from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from app.core.messages import SECRET_KEY_PLACEHOLDER_MESSAGE


class Settings(BaseSettings):
    POSTGRES_USER: str = Field(...)
    POSTGRES_PASSWORD: str = Field(...)
    POSTGRES_DB: str = Field(...)
    POSTGRES_TEST_DB: str = "taskhub_test"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5433
    DB_ECHO: bool = False

    SECRET_KEY: SecretStr = Field(min_length=32)
    ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0)

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value().lower()

        placeholders = (
            "change-me",
            "replace-with",
            "your-secret",
            "your-secret-key",
        )

        if any(placeholder in secret for placeholder in placeholders):
            raise ValueError(SECRET_KEY_PLACEHOLDER_MESSAGE)

        return value

    @property
    def DATABASE_URL(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
