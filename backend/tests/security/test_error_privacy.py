from fastapi.exceptions import RequestValidationError
import pytest

from app.main import validation_error


@pytest.mark.asyncio
async def test_validation_error_does_not_echo_invalid_private_input() -> None:
    secret = "USER_PRIVATE_PASSWORD"
    exception = RequestValidationError([{"type": "string_too_short", "loc": ("body", "password"), "msg": "String should have at least 12 characters", "input": secret, "ctx": {"min_length": 12}}])
    response = await validation_error(None, exception)
    assert secret.encode() not in response.body
    assert b'"input"' not in response.body
    assert b'"ctx"' not in response.body
