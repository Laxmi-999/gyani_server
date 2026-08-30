from arq.connections import RedisSettings, create_pool
from arq.connections import ArqRedis

redis_pool: ArqRedis | None = None

async def get_redis_pool() -> ArqRedis:
    global redis_pool
    if redis_pool is None:
        redis_pool = await create_pool(RedisSettings(host="localhost", port=6379))
    return redis_pool