from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "namanpuja-content-pipeline"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/api/v1"

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "namanpuja"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    use_mock_llm: bool = False

    redis_url: str = "redis://localhost:6379/0"
    worker_queue: str = "batch_generation"

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

    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 120

    batch_stuck_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

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
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if not self.is_production:
            return self

        weak_keys = {"dev-api-key", "replace-me", "changeme"}
        if self.enforce_auth and self.parsed_api_keys.intersection(weak_keys):
            raise ValueError("Production requires strong API keys; remove dev defaults")

        if not self.use_mock_llm and not self.openai_api_key:
            raise ValueError("Production requires OPENAI_API_KEY or explicit USE_MOCK_LLM=true")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
