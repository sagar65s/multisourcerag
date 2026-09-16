import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import Settings
from app.core.security import current_user


@pytest.mark.asyncio
async def test_identity_profile_is_derived_only_from_verified_firebase_claims(monkeypatch) -> None:
    monkeypatch.setattr("app.core.security.auth.verify_id_token", lambda *_args, **_kwargs: {
        "uid": "verified-user",
        "email": "verified@example.com",
        "name": "Verified Name",
        "picture": "https://example.com/photo.png",
        "email_verified": True,
        "auth_time": 456,
        "admin": True,
        "firebase": {"sign_in_provider": "google.com"},
    })
    settings = Settings(firebase_project_id="project", firebase_client_email="admin@example.com", firebase_private_key="private")
    user = await current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="verified-token"), settings)
    assert user.uid == "verified-user"
    assert user.email == "verified@example.com"
    assert user.display_name == "Verified Name"
    assert user.photo_url == "https://example.com/photo.png"
    assert user.provider == "google.com"
    assert user.email_verified and user.is_admin and user.auth_time == 456
