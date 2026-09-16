from io import BytesIO
import inspect

import pytest
from fastapi import HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import Headers

from app.core.config import Settings
from app.core.rate_limit import limiter
from app.core.security import current_user
from app.services.file_security_service import validate_upload


@pytest.mark.asyncio
async def test_missing_auth_token_is_rejected() -> None:
    with pytest.raises(HTTPException) as raised:
        await current_user(None, Settings())
    assert raised.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_auth_token_is_rejected_and_safely_audited(monkeypatch) -> None:
    events: list[tuple[str, str, dict]] = []

    def invalid_token(*_args, **_kwargs):
        raise ValueError("sensitive verifier detail")

    async def record(event: str, severity: str, metadata: dict) -> None:
        events.append((event, severity, metadata))

    monkeypatch.setattr("app.core.security.auth.verify_id_token", invalid_token)
    monkeypatch.setattr("app.services.audit_service.security_event", record)
    settings = Settings(
        firebase_project_id="project",
        firebase_client_email="admin@example.com",
        firebase_private_key="private",
    )
    with pytest.raises(HTTPException) as raised:
        await current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid"),
            settings,
        )
    assert raised.value.status_code == 401
    assert raised.value.detail == "Invalid authentication token"
    assert events == [("failed_auth", "warning", {"reason": "invalid_token"})]


@pytest.mark.asyncio
async def test_empty_and_oversized_uploads_are_rejected_before_processing() -> None:
    empty = UploadFile(
        file=BytesIO(b""),
        filename="empty.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    with pytest.raises(HTTPException) as empty_error:
        await validate_upload(empty, 8)
    assert empty_error.value.status_code == 400

    large = UploadFile(
        file=BytesIO(b"safe text"),
        filename="large.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    with pytest.raises(HTTPException) as large_error:
        await validate_upload(large, 4)
    assert large_error.value.status_code == 413


def test_abuse_sensitive_routes_have_bounded_rate_limits() -> None:
    # Importing registers SlowAPI decorators; the assertions prevent a future
    # refactor from silently removing quota protection from expensive routes.
    from app.api import account, chat, documents, exports, intelligence, jobs, research, websites  # noqa: F401

    expected = {
        "app.api.chat.stream_chat",
        "app.api.documents.upload_documents",
        "app.api.documents.reindex_document",
        "app.api.websites.add_website",
        "app.api.websites.reindex_website",
        "app.api.research.start_research",
        "app.api.intelligence.generate_intelligence",
        "app.api.exports.create_export",
        "app.api.account.synchronize_session",
        "app.api.account.delete_account",
        "app.api.jobs.cancel_job",
        "app.api.jobs.retry_job",
    }
    configured = set(limiter._route_limits)
    assert expected <= configured
    assert all(limiter._route_limits[name] for name in expected)


def test_rate_limited_routes_accept_injected_response() -> None:
    """SlowAPI header injection requires a parameter literally named response."""
    from app.api import account, chat, documents, exports, intelligence, jobs, research, websites

    endpoints = [
        account.synchronize_session,
        account.delete_account,
        chat.stream_chat,
        documents.upload_documents,
        documents.reindex_document,
        websites.add_website,
        websites.reindex_website,
        research.start_research,
        intelligence.generate_intelligence,
        exports.create_export,
        jobs.cancel_job,
        jobs.retry_job,
    ]
    assert all("response" in inspect.signature(endpoint).parameters for endpoint in endpoints)
