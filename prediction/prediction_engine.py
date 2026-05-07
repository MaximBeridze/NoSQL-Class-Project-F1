import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mongo.mongo_connection import db
from redis_db.redis_cache.cache_predictions import get_cached_prediction, cache_prediction

from neo4j_db.neo4j_repository import (
    get_driver_circuit_stats,
    get_driver_circuit_wins,
    get_team_strength,
    get_driver_avg_finish
)


def calculate_predictions(circuit_id):

    cached = get_cached_prediction(circuit_id)
    if cached:
        return cached

    standings = list(db.driver_standings.find())
    drivers = {d["_id"]: d for d in db.drivers.find()}

    predictions = []
    total = 0

    for s in standings:

        driver_id = s.get("driver_id") or s.get("driverId")
        if not driver_id:
            continue

        driver_info = drivers.get(driver_id, {})
        team_id = driver_info.get("team_id")

        # ---------------- MONGO ----------------
        mongo_score = (
            s.get("wins", 0) * 10 +
            s.get("podiums", 0) * 6 +
            s.get("points", 0) / 10
        )

        # ---------------- CIRCUIT ----------------
        races = get_driver_circuit_stats(driver_id, circuit_id)
        wins = get_driver_circuit_wins(driver_id, circuit_id)

        win_rate = wins / races if races else 0
        circuit_factor = 1 + win_rate * 0.7

        # ---------------- AVG FINISH ----------------
        avg_finish = get_driver_avg_finish(driver_id)
        finish_factor = max(0.6, 2.0 - avg_finish / 10)

        # ---------------- TEAM ----------------
        team_factor = 1.0
        if team_id:
            team_strength = get_team_strength(team_id)
            team_factor = 1 + min(team_strength / 25, 0.3)

        # ---------------- MOMENTUM (FIXED) ----------------
        momentum = max(0.8, 1.3 - s.get("points", 0) / 400)

        # ---------------- FINAL SCORE ----------------
        score = (
            mongo_score *
            circuit_factor *
            finish_factor *
            team_factor *
            momentum
        )

        predictions.append({
            "driverId": driver_id,
            "score": score
        })

        total += score

    for p in predictions:
        p["chance"] = round((p["score"] / total) * 100, 2) if total else 0

    predictions.sort(key=lambda x: x["chance"], reverse=True)

    cache_prediction(circuit_id, predictions)

    return predictions