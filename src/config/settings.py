from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    wb_base_url: str = "https://search.wb.ru/exactmatch/ru/common/v9/search"
    max_pages: int = 10000
    default_currency: str = "rub"
    default_destination: str = "12358062"
    http_timeout: float = 10.0
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 1200

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache
def get_settings() -> Settings:
    return Settings()