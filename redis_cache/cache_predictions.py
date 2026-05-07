import json
from typing import cast
from redis_cache.redis_connection import get_redis_client

redis_client = get_redis_client()


def cache_prediction(circuit_id, predictions):

    key = f"prediction:{circuit_id}"

    redis_client.setex(
        key,
        3600,
        json.dumps(predictions)
    )


def get_cached_prediction(circuit_id):

    key = f"prediction:{circuit_id}"

    data = cast(str | None, redis_client.get(key))

    if not data:
        return None

    return json.loads(data)