from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from .redisModels import PointsUpdate, TrackScoreUpdate, InitRaceBody, LapUpdate

from .redis_service import (
    get_redis,
    # standings
    get_driver_standings,
    get_driver_rank,
    update_driver_points,
    get_constructor_standings,
    get_constructor_rank,
    # track performance
    get_track_performance,
    get_driver_circuit_score,
    update_track_score,
    # live race
    init_live_race,
    get_live_race_order,
    update_driver_lap_state,
    finish_race,
    list_active_races,
    # predictions
    get_cached_prediction,
    generate_prediction,
    invalidate_prediction,
)

redis_router = APIRouter(tags=["Redis"])


# ─────────────────────────────────────────────
# DRIVER STANDINGS
# ─────────────────────────────────────────────

@redis_router.get("/standings/drivers")
def driver_standings(top: int = Query(20, ge=1, le=50)):
    """Return the top-N drivers sorted by championship points."""
    r = get_redis()
    return {"standings": get_driver_standings(r, top_n=top)}


@redis_router.get("/standings/drivers/{driver_id}")
def driver_rank(driver_id: str):
    """Return a single driver's points and rank."""
    r    = get_redis()
    data = get_driver_rank(r, driver_id)
    if not data:
        raise HTTPException(404, detail=f"Driver '{driver_id}' not found in standings")
    return data


@redis_router.patch("/standings/drivers/{driver_id}/points")
def add_driver_points(driver_id: str, body: PointsUpdate):
    """Add (or subtract) points from a driver atomically."""
    r = get_redis()
    if not get_driver_rank(r, driver_id):
        raise HTTPException(404, detail=f"Driver '{driver_id}' not found")
    return update_driver_points(r, driver_id, body.delta)


# ─────────────────────────────────────────────
# CONSTRUCTOR STANDINGS
# ─────────────────────────────────────────────

@redis_router.get("/standings/constructors")
def constructor_standings():
    """Return all constructors sorted by points."""
    r = get_redis()
    return {"standings": get_constructor_standings(r)}


@redis_router.get("/standings/constructors/{constructor_id}")
def constructor_rank(constructor_id: str):
    r    = get_redis()
    data = get_constructor_rank(r, constructor_id)
    if not data:
        raise HTTPException(404, detail=f"Constructor '{constructor_id}' not found")
    return data


# ─────────────────────────────────────────────
# TRACK PERFORMANCE
# ─────────────────────────────────────────────

@redis_router.get("/track/{circuit_id}/performance")
def track_performance(circuit_id: str, top: int = Query(10, ge=1, le=30)):
    """Return driver performance rankings for a specific circuit."""
    r    = get_redis()
    data = get_track_performance(r, circuit_id, top_n=top)
    if not data:
        raise HTTPException(404, detail=f"No performance data for circuit '{circuit_id}'")
    return data


@redis_router.get("/track/{circuit_id}/driver/{driver_id}")
def driver_circuit_score(circuit_id: str, driver_id: str):
    """Return a driver's performance score and rank on a given circuit."""
    r    = get_redis()
    data = get_driver_circuit_score(r, driver_id, circuit_id)
    if not data:
        raise HTTPException(404, detail=f"No score for driver '{driver_id}' on circuit '{circuit_id}'")
    return data


@redis_router.put("/track/{circuit_id}/driver/{driver_id}/score")
def set_track_score(circuit_id: str, driver_id: str, body: TrackScoreUpdate):
    """Set or update a driver's performance score on a circuit."""
    r = get_redis()
    return update_track_score(r, circuit_id, driver_id, body.score)


# ─────────────────────────────────────────────
# LIVE RACE
# ─────────────────────────────────────────────

@redis_router.post("/race/{race_id}/init")
def init_race(race_id: str, body: InitRaceBody):
    """Initialise a live race session in Redis."""
    r = get_redis()
    return init_live_race(
        r,
        race_id,
        body.race_name,
        body.total_laps,
        [d.model_dump() for d in body.drivers],
    )


@redis_router.get("/race/active")
def active_races():
    """List all race IDs that are not yet finished."""
    r = get_redis()
    return {"active_races": list_active_races(r)}


@redis_router.get("/race/{race_id}/live")
def live_race(race_id: str):
    """Return the current running order and driver states for a live race."""
    r    = get_redis()
    data = get_live_race_order(r, race_id)
    if not data:
        raise HTTPException(404, detail=f"Race '{race_id}' not found")
    return data


@redis_router.patch("/race/{race_id}/driver/{driver_id}/lap")
def update_lap(race_id: str, driver_id: str, body: LapUpdate):
    """Push a lap-state update for a driver in a live race."""
    r = get_redis()
    if not get_live_race_order(r, race_id):
        raise HTTPException(404, detail=f"Race '{race_id}' not found")
    return update_driver_lap_state(
        r, race_id, driver_id,
        body.position, body.lap, body.gap_to_leader,
        body.tyre, body.pit, body.status,
    )


@redis_router.post("/race/{race_id}/finish")
def end_race(race_id: str):
    """Mark a race as finished."""
    r = get_redis()
    if not get_live_race_order(r, race_id):
        raise HTTPException(404, detail=f"Race '{race_id}' not found")
    return finish_race(r, race_id)


# ─────────────────────────────────────────────
# PREDICTIONS
# ─────────────────────────────────────────────

@redis_router.get("/predict/{circuit_id}")
def predict(circuit_id: str, refresh: bool = Query(False)):
    """
    Return a top-3 race prediction for a circuit.
    Results are cached in Redis for 1 hour.
    Use ?refresh=true to bypass the cache.
    """
    r = get_redis()

    if not refresh:
        cached = get_cached_prediction(r, circuit_id)
        if cached:
            return cached

    result = generate_prediction(r, circuit_id)
    if "error" in result:
        raise HTTPException(404, detail=result["error"])
    return result


@redis_router.delete("/predict/{circuit_id}/cache")
def bust_prediction_cache(circuit_id: str):
    """Manually invalidate the prediction cache for a circuit."""
    r = get_redis()
    return invalidate_prediction(r, circuit_id)
