import os
import redis
from dotenv import load_dotenv
 
load_dotenv()
 
 
def get_redis_client() -> redis.Redis:
    """
    Return a new Redis client.
    Called lazily — never instantiated at module level so the app
    doesn't crash at import time if Redis isn't running yet.
    """
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
    )
