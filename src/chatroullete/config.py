from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from chatroullete.enums import Language


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "chatroullete"
    postgres_password: SecretStr
    postgres_db: str = "chatroullete"

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


class Settings(DatabaseSettings):
    bot_token: SecretStr

    webhook_base_url: str
    webhook_path: str = "/webhook"
    webhook_secret: SecretStr
    webapp_host: str = "127.0.0.1"
    webapp_port: int = 8085

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    room_idle_timeout_seconds: int = 600
    room_idle_check_interval_seconds: int = 30

    default_language: Language = Language.RU
    min_age: int = 18
    max_age: int = 99

    @property
    def webhook_url(self) -> str:
        return self.webhook_base_url.rstrip("/") + self.webhook_path
