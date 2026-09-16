from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore", str_strip_whitespace=True)

    app_name: str = "MultiSource AI"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    cors_origins: str = "http://localhost:3000"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "secure_rag"
    mongodb_retry_seconds: int = Field(default=30, ge=5, le=300)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "knowledge_chunks"
    firebase_project_id: str | None = None
    firebase_client_email: str | None = None
    firebase_private_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    mistral_api_key: str | None = None
    mistral_model: str = "mistral-small-latest"
    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-oss-20b:free"
    tavily_api_key: str | None = None
    github_token: str | None = None
    llm_provider_order: str = "gemini,groq,mistral,openrouter"
    search_provider_order: str = "tavily,ddgs"
    requests_per_minute: int = 60
    max_upload_bytes: int = 25 * 1024 * 1024
    private_storage_root: str = "./private_storage"
    ocr_languages: str = "eng+tam+hin"
    ocr_min_text_chars_per_page: int = 40
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    retrieval_candidates: int = 18
    reranked_evidence_limit: int = 6
    website_max_response_bytes: int = 5 * 1024 * 1024
    website_request_timeout_seconds: int = 15
    website_redirect_limit: int = 5
    website_default_max_pages: int = 20
    website_hard_max_pages: int = 50
    enable_playwright_fallback: bool = False
    search_results_limit: int = 8
    live_content_fetch_limit: int = 5
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    provider_log_retention_days: int = Field(default=30, ge=1, le=365)
    audit_log_retention_days: int = Field(default=365, ge=30, le=2555)
    security_log_retention_days: int = Field(default=365, ge=30, le=2555)
    processing_job_retention_days: int = Field(default=30, ge=1, le=365)
    provider_retry_count: int = Field(default=1, ge=0, le=3)
    custom_llm_providers_json: str = "[]"
    custom_search_providers_json: str = "[]"

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment == "production":
            if "*" in self.cors_origin_list:
                raise ValueError("Wildcard CORS origins are forbidden in production")
            if "*" in self.trusted_host_list:
                raise ValueError("Wildcard trusted hosts are forbidden in production")
            if not self.frontend_url.startswith("https://"):
                raise ValueError("Production FRONTEND_URL must use HTTPS")
            if any(not origin.startswith("https://") for origin in self.cors_origin_list):
                raise ValueError("Production CORS origins must use HTTPS")
            if not self.firebase_ready:
                raise ValueError("Firebase Admin credentials are required in production")
            if not self.qdrant_api_key:
                raise ValueError("Qdrant authentication is required in production")
        return self

    @property
    def firebase_ready(self) -> bool:
        return all((self.firebase_project_id, self.firebase_client_email, self.firebase_private_key))

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def llm_provider_names(self) -> list[str]:
        return [item.strip() for item in self.llm_provider_order.split(",") if item.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
