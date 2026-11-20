"""Cotas por agente: da janela fixa ingênua ao token bucket determinístico."""

import time
from collections.abc import Callable
from dataclasses import dataclass

from guarita.domain import Call, Decision


class FixedWindowQuota:
    """Defesa ingênua: contador por janela fixa, vulnerável a rajada dupla na virada."""

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._counts: dict[tuple[str, int], int] = {}

    async def decide(self, call: Call) -> Decision:
        bucket = int(self._clock() // self._window)
        key = (call.agent, bucket)
        used = self._counts.get(key, 0)
        if used >= self._limit:
            return Decision.deny(f"cota da janela esgotada para {call.agent}")
        self._counts[key] = used + 1
        return Decision.allow()


@dataclass
class _Bucket:
    tokens: float
    updated_at: float


class TokenBucketGate:
    """Balde de fichas por agente: recarga contínua e sem rajada dupla na virada."""

    def __init__(
        self,
        capacity: int,
        refill_per_second: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._capacity = float(capacity)
        self._rate = refill_per_second
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}

    async def decide(self, call: Call) -> Decision:
        now = self._clock()
        bucket = self._buckets.get(call.agent)
        if bucket is None:
            bucket = _Bucket(tokens=self._capacity, updated_at=now)
            self._buckets[call.agent] = bucket
        elapsed = max(0.0, now - bucket.updated_at)
        bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._rate)
        bucket.updated_at = now
        if bucket.tokens < 1.0:
            return Decision.deny(f"cota esgotada para {call.agent}")
        bucket.tokens -= 1.0
        return Decision.allow()
