from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    @property
    def database_url_asyncmy(self):
        return f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}/{self.DB_NAME}"

    model_config = SettingsConfigDict(env_file="db.env")


settings = Settings()
