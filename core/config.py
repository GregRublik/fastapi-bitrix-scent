from loguru import logger
from fastapi.templating import Jinja2Templates
from pydantic import Field

from session_manager import SessionManager
from pydantic_settings import BaseSettings, SettingsConfigDict


class DbSettings(BaseSettings):
    db_host: str = Field(json_schema_extra={'env': 'DB_HOST'})
    db_user: str = Field(json_schema_extra={'env': 'DB_USER'})
    db_pass: str = Field(json_schema_extra={'env': 'DB_PASS'})
    db_name: str = Field(json_schema_extra={'env': 'DB_NAME'})
    db_port: int = Field(json_schema_extra={'env': 'DB_PORT'})

    model_config = SettingsConfigDict(env_file="db/db.env")

    @property
    def database_url_asyncmy(self):
        return f"mysql+asyncmy://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def database_url_asyncpg(self):
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


# class RedisSettings(BaseSettings):
#     redis_pass: str = Field(json_schema_extra={'env': 'REDIS_PASS'})
#     redis_user: str = Field(json_schema_extra={'env': 'REDIS_USER'})
#     redis_user_pass: str = Field(json_schema_extra={'env': 'REDIS_USER_PASS'})
#     redis_port: str = Field(json_schema_extra={'env': 'REDIS_PORT'})
#
#     model_config = SettingsConfigDict(env_file="redis.env")


class Settings(BaseSettings):
    hosting_url: str = Field(json_schema_extra={'env': 'HOSTING_URL'})
    portal_url: str = Field(json_schema_extra={'env': 'PORTAL_URL'})
    client_secret: str = Field(json_schema_extra={'env': 'CLIENT_SECRET'})
    client_id: str = Field(json_schema_extra={'env': 'CLIENT_ID'})
    key_405: str = Field(json_schema_extra={'env': 'KEY_405'})
    sentry_url: str = Field(json_schema_extra={'env': 'SENTRY_URL'})

    db: DbSettings = DbSettings()
    # redis: RedisSettings = RedisSettings()

    model_config = SettingsConfigDict(env_file=".env")


logger.add(
    "logs/debug.log",
    format="{time} - {level} - {message}",
    level="INFO",
    rotation="5 MB",
    compression="zip"
)

templates = Jinja2Templates(directory="templates")
session_manager = SessionManager.get_instance()
settings = Settings()


def check_token(client_secret):
    assert client_secret == settings.client_secret, "Invalid Token"
