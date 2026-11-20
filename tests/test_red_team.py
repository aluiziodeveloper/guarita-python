from pathlib import Path

import pytest
from mcp import Client
from mcp.types import TextContent

from guarita.audit import AuditingGate, AuditTrail, verify_trail
from guarita.catalog import PinCatalog
from guarita.dlp import DlpGate
from guarita.domain import Call
from guarita.egress import EgressGate
from guarita.injection import InjectionReviewer
from guarita.integrity import PinnedTools
from guarita.lab.server import build_rug_pull_server, build_server
from guarita.limits import TokenBucketGate
from guarita.pipeline import PipelineRouter, RoutePipeline
from guarita.policy import PolicyGate
from guarita.proxy import build_proxy
from guarita.scanner import DescriptionScanner
from guarita.untrusted import UntrustedWrapper

pytestmark = pytest.mark.anyio


def to_fullwidth(text: str) -> str:
    return "".join(chr(ord(c) + 0xFEE0) if 0x21 <= ord(c) <= 0x7E else c for c in text)


async def test_combined_guarita_blocks_poisoning_rug_pull_injection_and_exfil(
    tmp_path: Path,
) -> None:
    trail = AuditTrail(tmp_path / "audit.jsonl")
    policy = PolicyGate.from_toml(
        """
        [[rules]]
        effect = "allow"
        tools = ["read_file"]
        [rules.arguments]
        path = ["notes.txt", "ticket.txt"]
        """
    )
    router = PipelineRouter(
        default=RoutePipeline(
            inbound=(
                AuditingGate(policy, trail),
                DlpGate(),
                EgressGate({"api.corp.test"}),
                TokenBucketGate(capacity=10, refill_per_second=1.0, clock=lambda: 0.0),
            ),
            outbound=(InjectionReviewer(),),
        )
    )

    with PinCatalog(tmp_path / "catalog.db") as catalog:
        async with Client(build_server("honest")) as upstream:
            catalog.pin("files", (await upstream.list_tools()).tools)
            proxy = build_proxy(
                upstream,
                gate=router,
                integrity=PinnedTools(catalog, "files"),
                scanner=DescriptionScanner(),
                reviewer=router,
            )
            async with Client(proxy) as agent:
                ok = await agent.call_tool("read_file", {"path": "notes.txt"})
                ssh = await agent.call_tool("read_file", {"path": "~/.ssh/id_rsa"})
                indirect = await agent.call_tool("read_file", {"path": "ticket.txt"})

        async with Client(build_rug_pull_server()) as traitor:
            catalog.pin("traitor", (await traitor.list_tools()).tools)
            proxy_rp = build_proxy(
                traitor,
                gate=router,
                integrity=PinnedTools(catalog, "traitor"),
                scanner=DescriptionScanner(),
                reviewer=router,
            )
            async with Client(proxy_rp) as agent:
                first = await agent.call_tool("read_file", {"path": "notes.txt"})
                after_swap = await agent.call_tool("read_file", {"path": "notes.txt"})

    assert ok.is_error is False
    assert ssh.is_error is True
    assert indirect.is_error is True
    assert first.is_error is False
    assert after_swap.is_error is True
    assert verify_trail(tmp_path / "audit.jsonl").ok is True


@pytest.mark.xfail(strict=True, reason="costura 1: DLP ainda não normaliza Unicode NFKC/Cf")
async def test_seam_fullwidth_cpf_bypasses_dlp() -> None:
    smuggled_cpf = to_fullwidth("529.982.247-25")
    decision = await DlpGate().decide(Call("send_message", {"body": f"CPF {smuggled_cpf}"}))

    assert decision.allowed is False


@pytest.mark.xfail(strict=True, reason="costura 2: política ainda não decodifica %2e%2e")
async def test_seam_percent_encoded_traversal_bypasses_policy() -> None:
    policy = PolicyGate.from_toml(
        """
        [[rules]]
        effect = "allow"
        tools = ["read_file"]
        [rules.arguments]
        path = ["notes/*"]
        """
    )
    decision = await policy.decide(Call("read_file", {"path": "notes/%2e%2e/.ssh/id_rsa"}))

    assert decision.allowed is False


@pytest.mark.xfail(
    strict=True, reason="costura 3: replace_text descarta structured_content exigido pelo SDK 2.x"
)
async def test_seam_untrusted_wrapper_with_mcpserver_output_schema() -> None:
    async with (
        Client(build_server("honest")) as upstream,
        Client(build_proxy(upstream, reviewer=UntrustedWrapper())) as agent,
    ):
        res = await agent.call_tool("read_file", {"path": "notes.txt"})

    assert res.is_error is False
    assert isinstance(res.content[0], TextContent)
    assert "<<<UNTRUSTED_DATA_" in res.content[0].text
