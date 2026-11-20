import pytest

from guarita.breaker import BreakerState, BudgetGate, CircuitBreaker
from guarita.domain import Call

pytestmark = pytest.mark.anyio


async def test_budget_gate_stops_agent_when_cost_exceeds_limit() -> None:
    gate = BudgetGate(max_cost=5.0, tool_costs={"web_search": 2.0, "read_file": 1.0})

    assert (await gate.decide(Call("web_search", {}, agent="a"))).allowed is True
    assert (await gate.decide(Call("web_search", {}, agent="a"))).allowed is True
    assert (await gate.decide(Call("read_file", {}, agent="a"))).allowed is True
    over = await gate.decide(Call("read_file", {}, agent="a"))

    assert over.allowed is False
    assert "orçamento" in over.reason


async def test_circuit_breaker_opens_after_threshold_and_recovers_after_timeout() -> None:
    now = 0.0
    breaker = CircuitBreaker(failure_threshold=2, reset_timeout=30.0, clock=lambda: now)
    call = Call("web_search", {})

    assert breaker.current_state() is BreakerState.CLOSED
    breaker.record_failure()
    assert (await breaker.decide(call)).allowed is True
    breaker.record_failure()
    assert breaker.current_state() is BreakerState.OPEN
    blocked = await breaker.decide(call)
    assert blocked.allowed is False
    assert "disjuntor aberto" in blocked.reason

    now = 31.0
    probe = await breaker.decide(call)
    assert probe.allowed is True
    assert breaker.current_state() is BreakerState.HALF_OPEN

    breaker.record_success()
    assert breaker.current_state() is BreakerState.CLOSED
