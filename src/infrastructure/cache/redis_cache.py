import redis.asyncio as redis
from typing import Optional, TypeVar, Generic
import json
import logging
from ...config.settings import get_settings
from ...domain.entities.product import Product

T = TypeVar("T")
logger = logging.getLogger(__name__)

class CacheService(Generic[T]):
    def __init__(self):
        self.settings = get_settings()
        self.client = redis.from_url(self.settings.redis_url)

    async def get(self, key: str) -> Optional[list[Product]]:
        try:
            cached_data = await self.client.get(key)
            if cached_data:
                data = json.loads(cached_data)
                return [Product(**item) for item in data]
            return None
        except redis.RedisError as e:
            logger.error(f"Redis unavailable for key {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: list[Product], ttl: int) -> None:
        try:
            serialized_value = [product.dict() for product in value]
            await self.client.setex(key, ttl, json.dumps(serialized_value, default=str))
        except redis.RedisError as e:
            logger.error(f"Redis unavailable for key {key}: {e}")
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            raise

    async def close(self) -> None:
        await self.client.aclose()