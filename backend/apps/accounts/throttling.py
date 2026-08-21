from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.core.cache import cache

LOCKOUT_SCHEDULE: tuple[tuple[int, int], ...] = (
    (5, 60),
    (10, 300),
    (20, 900),
)
COUNTER_TTL = 900


@dataclass(frozen=True)
class ThrottleState:
    count: int
    locked_until: datetime | None = None


def key(kind: str, value: str) -> str:
    return f"auth:login:{kind}:{value}"


def get_state(identifier: str) -> ThrottleState:
    value = cache.get(identifier)
    if not isinstance(value, dict):
        return ThrottleState(0)
    locked_until = value.get("locked_until")
    if isinstance(locked_until, str):
        locked_until = datetime.fromisoformat(locked_until)
    if isinstance(locked_until, datetime) and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    return ThrottleState(int(value.get("count", 0)), locked_until)


def is_locked(identifier: str) -> bool:
    state = get_state(identifier)
    return state.locked_until is not None and state.locked_until > datetime.now(UTC)


def record_failure(identifier: str) -> ThrottleState:
    state = get_state(identifier)
    count = state.count + 1
    duration = 0
    for threshold, seconds in LOCKOUT_SCHEDULE:
        if count >= threshold:
            duration = seconds
    locked_until = datetime.now(UTC) + timedelta(seconds=duration) if duration else None
    cache.set(
        identifier,
        {
            "count": count,
            "locked_until": locked_until.isoformat() if locked_until else None,
        },
        COUNTER_TTL,
    )
    return ThrottleState(count, locked_until)


def clear(identifier: str) -> None:
    cache.delete(identifier)
