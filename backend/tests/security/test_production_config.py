import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_rejects_wildcard_cors_and_hosts():
    with pytest.raises(ValidationError):
        Settings(environment="production", cors_origins="*", trusted_hosts="example.com")
    with pytest.raises(ValidationError):
        Settings(environment="production", cors_origins="https://example.com", trusted_hosts="*")


def test_production_accepts_explicit_origins_and_hosts():
    settings = Settings(environment="production", frontend_url="https://app.example.com", cors_origins="https://app.example.com", trusted_hosts="api.example.com", firebase_project_id="project", firebase_client_email="admin@example.com", firebase_private_key="private", qdrant_api_key="qdrant-secret")
    assert settings.cors_origin_list == ["https://app.example.com"]


def test_production_rejects_insecure_frontend_origin():
    with pytest.raises(ValidationError):
        Settings(environment="production", frontend_url="http://app.example.com", cors_origins="https://app.example.com", trusted_hosts="api.example.com")


def test_production_requires_private_infrastructure_authentication():
    with pytest.raises(ValidationError):
        Settings(environment="production", frontend_url="https://app.example.com", cors_origins="https://app.example.com", trusted_hosts="api.example.com")
