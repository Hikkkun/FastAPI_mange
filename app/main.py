from fastapi import FastAPI, Depends
from app.redis.redis_client import get_redis_client
from redis import Redis

app = FastAPI(title="FastAPI Redis App", version="1.0.0")


@app.get("/ping", summary="Test endpoint", tags=["Health Check"])
async def ping():
    return {"message": "Pong!"}


@app.get("/cache/{key}", summary="Get value from Redis", tags=["Redis"])
async def get_cache_value(key: str, redis_client: Redis = Depends(get_redis_client)):
    value = redis_client.get(key)
    if value:
        return {"key": key, "value": value}
    return {"key": key, "message": "Key not found"}


@app.post("/cache/{key}/{value}", summary="Set value in Redis", tags=["Redis"])
async def set_cache_value(key: str, value: str, redis_client: Redis = Depends(get_redis_client)):
    redis_client.set(key, value)
    return {"key": key, "value": value, "message": "Value set successfully"}
