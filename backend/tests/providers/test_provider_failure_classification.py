import httpx
from app.managers.llm_provider_manager import classify_failure
from app.providers.llm.base import ProviderHealth

def test_rate_limit_and_timeout_are_classified():
    response = httpx.Response(429, request=httpx.Request("POST", "https://provider.test"))
    assert classify_failure(httpx.HTTPStatusError("limited", request=response.request, response=response))[0] == ProviderHealth.RATE_LIMITED
    assert classify_failure(httpx.TimeoutException("slow"))[0] == ProviderHealth.DEGRADED


def test_missing_provider_model_is_not_retried_as_a_transient_failure():
    response = httpx.Response(404, request=httpx.Request("POST", "https://provider.test"))
    error = httpx.HTTPStatusError("missing", request=response.request, response=response)
    assert classify_failure(error)[0] == ProviderHealth.MISCONFIGURED
