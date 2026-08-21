from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.core.cache import cache

LOGIN_LOCKOUT_SCHEDULE: tuple[tuple[int, int], ...] = (
    (5, 60),
    (10, 300),
    (20, 900),
)
IP_SPRAY_SCHEDULE: tuple[tuple[int, int], ...] = (
    (20, 60),
    (50, 300),
    (100, 900),
)
SIGNUP_RATE_SCHEDULE: tuple[tuple[int, int], ...] = (
    (25, 60),
    (100, 300),
    (250, 900),
)
COUNTER_TTL = 900


@dataclass(frozen=True)
class ThrottleState:
    count: int
    locked_until: datetime | None = None


def key(kind: str, value: str) -> str:
    return f"auth:login:{kind}:{value}"


def signup_key(value: str) -> str:
    return f"auth:signup:ip:{value}"


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


def _record(identifier: str, schedule: tuple[tuple[int, int], ...]) -> ThrottleState:
    state = get_state(identifier)
    count = state.count + 1
    duration = 0
    for threshold, seconds in schedule:
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


def record_failure(identifier: str) -> ThrottleState:
    return _record(identifier, LOGIN_LOCKOUT_SCHEDULE)


def record_ip_failure(identifier: str) -> ThrottleState:
    return _record(identifier, IP_SPRAY_SCHEDULE)


def record_signup(identifier: str) -> ThrottleState:
    return _record(identifier, SIGNUP_RATE_SCHEDULE)


def clear(identifier: str) -> None:
    cache.delete(identifier)
