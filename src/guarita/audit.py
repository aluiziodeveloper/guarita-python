"""Trilha de auditoria só por acréscimo (append-only), encadeada por SHA-256."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from guarita.dlp import scan_text
from guarita.domain import Call, Decision
from guarita.gate import Gate

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditEntry:
    seq: int
    timestamp: str
    agent: str
    tool: str
    args_sha256: str
    verdict: str
    reason: str
    prev_hash: str
    entry_hash: str


def _args_digest(call: Call) -> str:
    canonical = json.dumps(
        dict(call.arguments), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _safe_reason(reason: str) -> str:
    """Garante RNF02: se o motivo citar dado sensível ou CPF, grava apenas o aviso redigido."""
    if reason and scan_text(reason):
        return "[motivo redigido por conter dado sensível]"
    return reason


def compute_entry_hash(payload: dict[str, object]) -> str:
    body = {k: v for k, v in payload.items() if k != "entry_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditTrail:
    """Registra cada decisão numa linha JSONL encadeada pelo hash da linha anterior."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def entries(self) -> list[AuditEntry]:
        if not self._path.exists():
            return []
        result: list[AuditEntry] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                result.append(AuditEntry(**json.loads(line)))
        return result

    def record(self, call: Call, decision: Decision) -> AuditEntry:
        existing = self.entries()
        seq = len(existing) + 1
        prev_hash = existing[-1].entry_hash if existing else GENESIS_HASH
        base: dict[str, object] = {
            "seq": seq,
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "agent": call.agent,
            "tool": call.tool,
            "args_sha256": _args_digest(call),
            "verdict": str(decision.verdict),
            "reason": _safe_reason(decision.reason),
            "prev_hash": prev_hash,
        }
        entry = AuditEntry(
            seq=seq,
            timestamp=str(base["timestamp"]),
            agent=call.agent,
            tool=call.tool,
            args_sha256=str(base["args_sha256"]),
            verdict=str(base["verdict"]),
            reason=str(base["reason"]),
            prev_hash=prev_hash,
            entry_hash=compute_entry_hash(base),
        )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry


class AuditingGate:
    """Envolve qualquer portão gravando toda decisão na trilha encadeada."""

    def __init__(self, inner: Gate, trail: AuditTrail) -> None:
        self._inner = inner
        self._trail = trail

    async def decide(self, call: Call) -> Decision:
        decision = await self._inner.decide(call)
        self._trail.record(call, decision)
        return decision


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    entries: int
    error: str = ""


def verify_trail(path: str | Path) -> VerificationResult:
    """Confere sequência, encadeamento e SHA-256 de cada linha da trilha."""
    trail_path = Path(path)
    if not trail_path.exists():
        return VerificationResult(ok=False, entries=0, error="arquivo de auditoria não encontrado")
    lines = [line for line in trail_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected_prev = GENESIS_HASH
    for idx, line in enumerate(lines, start=1):
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            return VerificationResult(
                ok=False, entries=idx - 1, error=f"linha {idx}: JSON inválido ({error})"
            )
        if raw.get("seq") != idx:
            return VerificationResult(
                ok=False, entries=idx - 1, error=f"linha {idx}: sequência quebrada"
            )
        if raw.get("prev_hash") != expected_prev:
            return VerificationResult(
                ok=False, entries=idx - 1, error=f"linha {idx}: prev_hash divergente"
            )
        actual_hash = compute_entry_hash(raw)
        if raw.get("entry_hash") != actual_hash:
            return VerificationResult(
                ok=False, entries=idx - 1, error=f"linha {idx}: hash adulterado"
            )
        expected_prev = actual_hash
    return VerificationResult(ok=True, entries=len(lines))
