from dataclasses import dataclass

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials

from app.core.config import Settings, get_settings

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    uid: str
    email: str | None
    is_admin: bool
    auth_time: int = 0
    display_name: str | None = None
    photo_url: str | None = None
    provider: str | None = None
    email_verified: bool = False


def initialize_firebase(settings: Settings) -> None:
    if firebase_admin._apps or not settings.firebase_ready:
        return
    private_key = settings.firebase_private_key.replace("\\n", "\n")
    certificate = credentials.Certificate(
        {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "client_email": settings.firebase_client_email,
            "private_key": private_key,
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )
    firebase_admin.initialize_app(certificate)


async def current_user(
    token: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> AuthenticatedUser:
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if not settings.firebase_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Authentication service is not configured")
    try:
        claims = auth.verify_id_token(token.credentials, check_revoked=True)
    except Exception as exc:
        from app.services.audit_service import security_event
        await security_event("failed_auth", severity="warning", metadata={"reason": "invalid_token"})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc
    uid = claims.get("uid") or claims.get("sub")
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
    firebase_claims = claims.get("firebase") if isinstance(claims.get("firebase"), dict) else {}
    return AuthenticatedUser(
        uid=uid,
        email=claims.get("email"),
        is_admin=claims.get("admin") is True,
        auth_time=int(claims.get("auth_time") or 0),
        display_name=claims.get("name"),
        photo_url=claims.get("picture"),
        provider=firebase_claims.get("sign_in_provider"),
        email_verified=claims.get("email_verified") is True,
    )


async def admin_user(user: AuthenticatedUser = Depends(current_user)) -> AuthenticatedUser:
    if not user.is_admin:
        from app.services.audit_service import security_event
        await security_event("admin_authorization_failure", user.uid, metadata={"reason": "missing_admin_claim", "resource_type": "admin"})
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator permission required")
    return user
