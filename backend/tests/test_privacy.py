import pytest

from app.core.privacy import redact_secrets


def test_redacts_common_secret() -> None:
    text, count = redact_secrets("api_key=super-secret-value-123")
    assert "super-secret" not in text
    assert count == 1


def test_preserves_normal_text() -> None:
    text, count = redact_secrets("Retrieval augmented generation uses evidence.")
    assert count == 0
    assert text.startswith("Retrieval")


@pytest.mark.parametrize("secret", ["AKIAABCDEFGHIJKLMNOP", "AIzaSyExampleSecretKeyValue1234567890", "eyJabcdefghijk.abcdefghijklmnop.qrstuvwxyz123456", "mongodb+srv://admin:private-password@cluster.example/db"])
def test_redacts_cloud_tokens_jwts_and_credential_urls(secret: str) -> None:
    text, count = redact_secrets(f"credential={secret}")
    assert secret not in text
    assert count >= 1
