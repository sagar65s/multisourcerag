from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from threading import Lock

from app.providers.llm.base import ProviderHealth


@dataclass
class RuntimeProviderState:
    health: ProviderHealth = ProviderHealth.HEALTHY
    cooldown_until: datetime | None = None
    last_failure: datetime | None = None
    last_success: datetime | None = None
    failure_count: int = 0
    daily_date: date = field(default_factory=lambda: datetime.now(UTC).date())
    daily_requests: int = 0
    recent_requests: deque[datetime] = field(default_factory=deque)


class ProviderStateStore:
    def __init__(self) -> None:
        self._states: dict[tuple[str, str], RuntimeProviderState] = defaultdict(RuntimeProviderState)
        self._lock = Lock()

    def can_attempt(self, category: str, name: str, rpm: int = 0, daily_quota: int = 0) -> tuple[bool, ProviderHealth]:
        now = datetime.now(UTC)
        with self._lock:
            state = self._states[(category, name)]
            if state.daily_date != now.date():
                state.daily_date = now.date(); state.daily_requests = 0
            while state.recent_requests and state.recent_requests[0] < now - timedelta(minutes=1): state.recent_requests.popleft()
            if state.cooldown_until and state.cooldown_until > now: return False, ProviderHealth.COOLDOWN
            if daily_quota > 0 and state.daily_requests >= daily_quota:
                state.health = ProviderHealth.QUOTA_EXHAUSTED; return False, state.health
            if rpm > 0 and len(state.recent_requests) >= rpm:
                state.health = ProviderHealth.RATE_LIMITED; state.cooldown_until = now + timedelta(seconds=60); return False, state.health
            state.daily_requests += 1; state.recent_requests.append(now)
            return True, state.health

    def success(self, category: str, name: str) -> None:
        with self._lock:
            state = self._states[(category, name)]; state.health = ProviderHealth.HEALTHY; state.cooldown_until = None; state.failure_count = 0; state.last_success = datetime.now(UTC)

    def failure(self, category: str, name: str, health: ProviderHealth, cooldown_seconds: int) -> None:
        with self._lock:
            state = self._states[(category, name)]; state.health = health; state.failure_count += 1; state.last_failure = datetime.now(UTC); state.cooldown_until = datetime.now(UTC) + timedelta(seconds=cooldown_seconds)

    def snapshot(self, category: str, name: str) -> dict:
        with self._lock:
            state = self._states[(category, name)]
            return {"health": state.health.value, "cooldown_until": state.cooldown_until, "last_failure": state.last_failure, "last_success": state.last_success, "daily_requests": state.daily_requests, "failures": state.failure_count}


provider_state = ProviderStateStore()
