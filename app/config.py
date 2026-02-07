from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Traffic Director"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_prefix": "TD_"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
