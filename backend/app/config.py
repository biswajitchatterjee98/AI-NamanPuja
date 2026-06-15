import re
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WEAK_KEY_PATTERNS = (
    r"^dev-api-key$",
    r"^replace-me$",
    r"^changeme$",
    r"^replace-with",
    r"^your[-_]",
    r"^xxx+$",
    r"^test[-_]key",
)

LlmProvider = Literal["mock", "openai", "groq"]


class Settings(BaseSettings):
    app_name: str = "namanpuja-content-pipeline"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "namanpuja"

    llm_provider: LlmProvider = "mock"
    use_mock_llm: bool = False  # legacy; if true, forces mock

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    gemini_api_key: str = ""
    gemini_content_model: str = "gemini-2.0-flash"
    gemini_image_model: str = "gemini-2.0-flash-preview-image-generation"

    redis_url: str = "redis://localhost:6379/0"
    worker_queue: str = "batch_generation"
    job_max_retries: int = 3

    cms_base_url: str = ""
    cms_api_key: str = ""
    cms_upload_enabled: bool = False

    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    s3_public_base_url: str = ""
    use_s3_storage: bool = False
    local_image_dir: str = "../frontend/public/images"

    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    api_keys: str = "dev-api-key"
    enforce_auth: bool = False
    trusted_hosts: str = ""
    trusted_proxy_ips: str = ""

    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120
    rate_limit_fail_closed: bool = True

    batch_stuck_minutes: int = 30
    pipeline_max_workers: int = 4

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def effective_llm_provider(self) -> LlmProvider:
        if self.use_mock_llm:
            return "mock"
        return self.llm_provider

    @property
    def active_llm_model(self) -> str:
        if self.effective_llm_provider == "groq":
            return self.groq_model
        if self.effective_llm_provider == "openai":
            return self.openai_model
        return "mock"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def parsed_api_keys(self) -> set[str]:
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}

    @property
    def parsed_trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    @property
    def parsed_trusted_proxy_ips(self) -> set[str]:
        return {ip.strip() for ip in self.trusted_proxy_ips.split(",") if ip.strip()}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @staticmethod
    def _is_weak_secret(value: str) -> bool:
        normalized = value.strip().lower()
        if len(normalized) < 16:
            return True
        return any(re.match(pattern, normalized) for pattern in WEAK_KEY_PATTERNS)

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if not self.is_production:
            return self

        if self.enforce_auth:
            for key in self.parsed_api_keys:
                if self._is_weak_secret(key):
                    raise ValueError("Production requires strong API keys; remove placeholder values")

        provider = self.effective_llm_provider
        if provider == "openai":
            if not self.openai_api_key or self._is_weak_secret(self.openai_api_key):
                raise ValueError("Production requires a valid OPENAI_API_KEY when LLM_PROVIDER=openai")
        elif provider == "groq":
            has_groq = self.groq_api_key and not self._is_weak_secret(self.groq_api_key)
            has_gemini = self.gemini_api_key and not self._is_weak_secret(self.gemini_api_key)
            if not has_groq and not has_gemini:
                raise ValueError(
                    "Production requires a valid GROQ_API_KEY or GEMINI_API_KEY when LLM_PROVIDER=groq"
                )

        if self.cms_upload_enabled:
            if not self.cms_base_url:
                raise ValueError("CMS_BASE_URL is required when CMS_UPLOAD_ENABLED=true")
            if not self.cms_api_key or self._is_weak_secret(self.cms_api_key):
                raise ValueError("CMS_API_KEY is required when CMS_UPLOAD_ENABLED=true")

        if self.use_s3_storage:
            if not self.s3_bucket or not self.s3_public_base_url:
                raise ValueError("S3_BUCKET and S3_PUBLIC_BASE_URL are required when USE_S3_STORAGE=true")

        if self.rate_limit_enabled:
            self.rate_limit_fail_closed = True

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
