from pydantic import BaseSettings
from functools import lru_cache

__all__ = ("Settings",)

class _BaseSettings(BaseSettings):
    PROJECT_ID: str
    PROJECT_KEY_NAME: str
    PROJECT_KEY: str
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings():
    return _BaseSettings()


Settings = get_settings()
