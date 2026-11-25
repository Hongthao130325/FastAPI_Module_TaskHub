import pytest
from pydantic import ValidationError

from app.core.config import Settings


def create_settings(**overrides) -> Settings:
    values = {
        "POSTGRES_USER": "taskhub_test",
        "POSTGRES_PASSWORD": "test-password",
        "POSTGRES_DB": "taskhub_test",
        "SECRET_KEY": "a" * 48,
    }
    values.update(overrides)

    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    "environment",
    ["development", "testing", "production"],
)
def test_settings_accepts_supported_environments(environment: str):
    settings = create_settings(APP_ENV=environment)

    assert settings.APP_ENV == environment


def test_settings_defaults_to_development():
    settings = create_settings()

    assert settings.APP_ENV == "development"
    assert settings.DEBUG is False
    assert settings.DB_ECHO is False
    assert settings.REDIS_SOCKET_TIMEOUT == 5.0
    assert settings.REDIS_SOCKET_CONNECT_TIMEOUT == 5.0


def test_settings_rejects_unsupported_environment():
    with pytest.raises(ValidationError):
        create_settings(APP_ENV="staging")


def test_production_rejects_debug_enabled():
    with pytest.raises(ValidationError):
        create_settings(APP_ENV="production", DEBUG=True)


def test_production_rejects_database_echo_enabled():
    with pytest.raises(ValidationError):
        create_settings(APP_ENV="production", DB_ECHO=True)


def test_production_accepts_secure_configuration():
    settings = create_settings(
        APP_ENV="production",
        DEBUG=False,
        DB_ECHO=False,
    )

    assert settings.APP_ENV == "production"
