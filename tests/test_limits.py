import pytest

from guarita.domain import Call
from guarita.limits import FixedWindowQuota, TokenBucketGate

pytestmark = pytest.mark.anyio


async def test_fixed_window_allows_double_burst_across_window_boundary() -> None:
    now = 59.9
    naive = FixedWindowQuota(limit=2, window_seconds=60.0, clock=lambda: now)
    call = Call("read_file", {}, agent="loop-bot")

    assert (await naive.decide(call)).allowed is True
    assert (await naive.decide(call)).allowed is True
    now = 60.1  # 0.2s depois, a janela virou e dobrou a rajada
    assert (await naive.decide(call)).allowed is True
    assert (await naive.decide(call)).allowed is True


async def test_token_bucket_blocks_burst_and_refills_smoothly() -> None:
    now = 0.0
    gate = TokenBucketGate(capacity=2, refill_per_second=0.5, clock=lambda: now)
    call = Call("read_file", {}, agent="loop-bot")

    assert (await gate.decide(call)).allowed is True
    assert (await gate.decide(call)).allowed is True
    blocked = await gate.decide(call)
    assert blocked.allowed is False
    assert "cota" in blocked.reason

    now = 2.0  # 2s * 0.5 tokens/s = +1 token
    assert (await gate.decide(call)).allowed is True
    assert (await gate.decide(call)).allowed is False


async def test_token_bucket_isolates_agents() -> None:
    gate = TokenBucketGate(capacity=1, refill_per_second=0.1, clock=lambda: 0.0)

    assert (await gate.decide(Call("read_file", {}, agent="a"))).allowed is True
    assert (await gate.decide(Call("read_file", {}, agent="a"))).allowed is False
    assert (await gate.decide(Call("read_file", {}, agent="b"))).allowed is True
