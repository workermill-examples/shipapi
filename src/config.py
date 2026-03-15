from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str = "postgresql://shipapi:shipapi@localhost:5432/shipapi"
    JWT_SECRET_KEY: str = "change-me-to-a-long-random-secret-key"
    PORT: int = 8000


settings = Settings()
