from app.core.provider_state import ProviderStateStore
from app.providers.llm.base import ProviderHealth


def test_daily_quota_blocks_only_after_allowed_request() -> None:
    store = ProviderStateStore()
    assert store.can_attempt("llm", "quota-provider", daily_quota=1)[0]
    allowed, health = store.can_attempt("llm", "quota-provider", daily_quota=1)
    assert not allowed
    assert health is ProviderHealth.QUOTA_EXHAUSTED
    assert store.snapshot("llm", "quota-provider")["daily_requests"] == 1


def test_rpm_gate_enters_rate_limited_cooldown() -> None:
    store = ProviderStateStore()
    assert store.can_attempt("search", "rpm-provider", rpm=1)[0]
    allowed, health = store.can_attempt("search", "rpm-provider", rpm=1)
    assert not allowed
    assert health is ProviderHealth.RATE_LIMITED
    assert store.snapshot("search", "rpm-provider")["cooldown_until"] is not None
