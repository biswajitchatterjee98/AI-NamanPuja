import pytest

from app.config import Settings


def test_weak_api_key_rejected_in_production():
    with pytest.raises(ValueError, match="strong API keys"):
        Settings(
            app_env="production",
            enforce_auth=True,
            use_mock_llm=False,
            llm_provider="openai",
            api_keys="dev-api-key",
            openai_api_key="sk-prod-key-with-32-characters-min",
        )


def test_placeholder_openai_key_rejected():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings(
            app_env="production",
            enforce_auth=True,
            use_mock_llm=False,
            llm_provider="openai",
            api_keys="super-secret-production-api-key",
            openai_api_key="replace-with-production-key",
        )


def test_placeholder_groq_key_rejected():
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        Settings(
            app_env="production",
            enforce_auth=True,
            use_mock_llm=False,
            llm_provider="groq",
            api_keys="super-secret-production-api-key",
            groq_api_key="replace-with-groq-key",
        )


def test_cms_requires_key_when_upload_enabled():
    with pytest.raises(ValueError, match="CMS_API_KEY"):
        Settings(
            app_env="production",
            enforce_auth=True,
            use_mock_llm=False,
            llm_provider="openai",
            api_keys="super-secret-production-api-key",
            openai_api_key="sk-prod-key-with-32-characters-min",
            cms_upload_enabled=True,
            cms_base_url="https://cms.example.com",
        )


def test_development_allows_dev_key():
    settings = Settings(app_env="development", api_keys="dev-api-key")
    assert settings.app_env == "development"
