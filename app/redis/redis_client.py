import aioredis
import logging
import os

logger = logging.getLogger(__name__)

# Глобальная переменная для Redis
_redis = None

# Функция для инициализации Redis
async def init_redis():
    global _redis
    if _redis is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")  # Получаем URL из переменной окружения
            _redis = await aioredis.from_url(redis_url)
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    return _redis

# Функция для закрытия Redis
async def close_redis():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
        logger.info("Redis connection closed")

# Функция для получения Redis
def get_redis():
    if _redis is None:
        raise RuntimeError("Redis is not initialized")
    return _redis