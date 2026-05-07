"""
cache_predictions.py
────────────────────
Used by prediction_engine.py (the CLI flow: python index.py predict).

IMPORTANT: Uses the same Redis key format as redis_service.py so predictions
cached via CLI are readable by the API (GET /redis/predict/{circuit_id})
and vice versa.

Format: HASH at key  prediction:{circuit_id}
  top3         → JSON string of list[dict]
  analysis     → plain string description
  generated_at → ISO timestamp
TTL: 1 hour
"""

import json
from datetime import datetime
from typing import Optional

from redis_db.redis_cache.redis_connection import get_redis_client

PREDICTION_TTL = 3600  # seconds


def _client():
    """Lazy — only connects when called, never at import time."""
    return get_redis_client()


def cache_prediction(circuit_id: str, predictions: list) -> None:
    """
    Cache the full prediction list for a circuit.
    Stores as a HASH (same format as redis_service.store_prediction)
    so the FastAPI GET /redis/predict/{circuit_id} endpoint can also read it.
    """
    key  = f"prediction:{circuit_id}"
    r    = _client()
    top3 = predictions[:3]

    names    = [p.get("driverId", "?") for p in top3]
    analysis = (
        f"CLI prediction for '{circuit_id}'. "
        f"Top drivers: {', '.join(names)}. "
        f"Score = wins×10 + podiums×6 + points/10, weighted by circuit & team factors."
    )

    pipe = r.pipeline()
    pipe.hset(key, mapping={
        "top3":         json.dumps(top3),
        "analysis":     analysis,
        "generated_at": datetime.utcnow().isoformat(),
    })
    pipe.expire(key, PREDICTION_TTL)
    pipe.execute()


def get_cached_prediction(circuit_id: str) -> Optional[list]:
    """
    Return the cached prediction list, or None if not cached.
    Reads from HASH format (same as redis_service).
    """
    key  = f"prediction:{circuit_id}"
    data = _client().hgetall(key)

    if not data or "top3" not in data:
        return None

    return json.loads(data["top3"])