from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    PORT: int = 8000


settings = Settings()  # type: ignore[call-arg]
