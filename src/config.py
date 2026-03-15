from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env")

    DATABASE_URL: str
    JWT_SECRET_KEY: str
    PORT: int = 8000


settings = Settings()