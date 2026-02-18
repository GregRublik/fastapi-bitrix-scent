from loguru import logger
from fastapi.templating import Jinja2Templates

from aiohttp import ClientSession
from pydantic_settings import BaseSettings, SettingsConfigDict


class SessionManager:
    _session: ClientSession | None = None

    @classmethod
    async def get_session(cls) -> ClientSession:
        """Возвращает сессию aiohttp, создавая её при первом вызове."""
        if cls._session is None or cls._session.closed:
            cls._session = ClientSession()
        return cls._session

    @classmethod
    async def close_session(cls):
        """Закрывает сессию, если она существует."""
        if cls._session is not None:
            await cls._session.close()
            cls._session = None


class DbSettings(BaseSettings):
    host: str
    user: str
    password: str
    name: str
    port: int

    model_config = SettingsConfigDict(env_prefix="DB_", env_file=".env", extra="ignore")

    @property
    def dsn_asyncmy(self):
        return f"mysql+asyncmy://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def dsn_asyncpg(self):
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"



class BitrixSettings(BaseSettings):
    portal_url: str
    client_secret: str
    client_id: str
    key_405: str

    access_token: str = ''
    refresh_token: str = ''

    model_config = SettingsConfigDict(env_prefix="BITRIX_", env_file=".env", extra="ignore")


class Settings(BaseSettings):
    hosting_url: str

    host: str
    port: int

    bitrix: BitrixSettings
    db: DbSettings

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")


logger.add(
    "logs/debug.log",
    format="{time} - {level} - {message}",
    level="INFO",
    rotation="5 MB",
    compression="zip"
)

templates = Jinja2Templates(directory="src/templates")
settings = Settings(
    db=DbSettings(),
    bitrix=BitrixSettings(),
)
