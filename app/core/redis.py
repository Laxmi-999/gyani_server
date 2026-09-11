from arq.connections import ArqRedis, RedisSettings, create_pool

from app.config import settings

redis_pool: ArqRedis | None = None


def get_redis_settings() -> RedisSettings:
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
    )


async def get_redis_pool() -> ArqRedis:
    global redis_pool
    if redis_pool is None:
        redis_pool = await create_pool(get_redis_settings())
    return redis_pool