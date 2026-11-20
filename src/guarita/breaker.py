"""Orçamento de custo por agente e disjuntor (circuit breaker) contra falhas em cascata."""

import time
from collections.abc import Callable, Mapping
from enum import StrEnum

from guarita.domain import Call, Decision


class BudgetGate:
    """Impõe um teto de custo acumulado por agente para barrar laços caros."""

    def __init__(
        self,
        max_cost: float,
        tool_costs: Mapping[str, float] | None = None,
        default_cost: float = 1.0,
    ) -> None:
        self._max_cost = max_cost
        self._costs = dict(tool_costs or {})
        self._default_cost = default_cost
        self._spent: dict[str, float] = {}

    async def decide(self, call: Call) -> Decision:
        cost = self._costs.get(call.tool, self._default_cost)
        spent = self._spent.get(call.agent, 0.0)
        if spent + cost > self._max_cost:
            return Decision.deny(f"orçamento esgotado para {call.agent}")
        self._spent[call.agent] = spent + cost
        return Decision.allow()


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Corta chamadas rapidamente quando o servidor a montante acumula falhas seguidas."""

    def __init__(
        self,
        failure_threshold: int = 3,
        reset_timeout: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._threshold = failure_threshold
        self._reset_timeout = reset_timeout
        self._clock = clock
        self._state = BreakerState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    def current_state(self) -> BreakerState:
        return self._state

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._state = BreakerState.OPEN
            self._opened_at = self._clock()

    def record_success(self) -> None:
        self._failures = 0
        self._state = BreakerState.CLOSED

    async def decide(self, call: Call) -> Decision:
        if self._state is BreakerState.OPEN:
            if self._clock() - self._opened_at >= self._reset_timeout:
                self._state = BreakerState.HALF_OPEN
                return Decision.allow()
            return Decision.deny(f"disjuntor aberto para {call.tool}")
        return Decision.allow()
