from src.services.redis_service import RedisService


def get_redis_service() -> RedisService:
    return RedisService()