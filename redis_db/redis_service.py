"""
redis_service.py
────────────────
All Redis interactions for the F1 Race Database project.

Key schema
──────────
standings:drivers                  ZSET  score=points
standings:constructors             ZSET  score=points
driver:{id}                        HASH  name, team_id, number, code, titles
constructor:{id}                   HASH  name, points, wins, podiums
track:perf:{circuit_id}            ZSET  score=performance_rating, member=driverId
race:live:{race_id}:driver:{id}    HASH  position, lap, gap_to_leader, tyre, pit_stops
race:live:{race_id}:order          ZSET  score=position (ascending, lower=better)
race:live:{race_id}:meta           HASH  race_name, total_laps, status, current_lap
prediction:{circuit_id}            HASH  top3, analysis, generated_at   (TTL=1hr)
"""

import json
import os
from datetime import datetime
from typing import Optional

import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

_pool = redis.ConnectionPool(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)


# ─────────────────────────────────────────────
# SEEDING
# ─────────────────────────────────────────────

def seed_all(data_dir: str = "data") -> dict:
    r = get_redis()
    results = {}
    results["driver_standings"]      = seed_driver_standings(r, data_dir)
    results["constructor_standings"] = seed_constructor_standings(r, data_dir)
    results["driver_profiles"]       = seed_driver_profiles(r, data_dir)
    results["track_performance"]     = seed_track_performance(r, data_dir)
    return results


def seed_driver_standings(r: redis.Redis, data_dir: str) -> str:
    path = os.path.join(data_dir, "driver_standings.json")
    with open(path) as f:
        standings = json.load(f)

    pipe = r.pipeline()
    pipe.delete("standings:drivers")

    seeded = 0
    for entry in standings:
        # All entries now use "driverId" — fixed in data/driver_standings.json
        driver_id = entry.get("driverId")
        if not driver_id:
            print(f"Warning: skipping malformed entry (no driverId): {entry}")
            continue

        pipe.zadd("standings:drivers", {driver_id: float(entry["points"])})
        pipe.hset(f"standing:driver:{driver_id}", mapping={
            "position": entry["position"],
            "wins":     entry["wins"],
            "podiums":  entry["podiums"],
            "status":   entry["status"],
        })
        seeded += 1

    pipe.execute()
    return f"Seeded {seeded} driver standings"


def seed_constructor_standings(r: redis.Redis, data_dir: str) -> str:
    """
    Derive real constructor points by summing driver standings per team.
    Reads driver_standings.json + drivers.json — no mock data.
    """
    standings_path = os.path.join(data_dir, "driver_standings.json")
    drivers_path   = os.path.join(data_dir, "drivers.json")
    teams_path     = os.path.join(data_dir, "teams.json")

    with open(standings_path) as f:
        standings = json.load(f)
    with open(drivers_path) as f:
        drivers = {d["_id"]: d for d in json.load(f)}
    with open(teams_path) as f:
        teams = {t["_id"]: t for t in json.load(f)}

    # Aggregate points/wins/podiums per constructor
    constructor_totals: dict[str, dict] = {}
    for entry in standings:
        driver_id = entry.get("driverId")
        if not driver_id:
            continue
        driver  = drivers.get(driver_id, {})
        team_id = driver.get("team_id")
        if not team_id:
            continue

        if team_id not in constructor_totals:
            constructor_totals[team_id] = {"points": 0, "wins": 0, "podiums": 0}

        constructor_totals[team_id]["points"]  += entry.get("points", 0)
        constructor_totals[team_id]["wins"]    += entry.get("wins", 0)
        constructor_totals[team_id]["podiums"] += entry.get("podiums", 0)

    pipe = r.pipeline()
    pipe.delete("standings:constructors")

    for team_id, totals in constructor_totals.items():
        team_name = teams.get(team_id, {}).get("name", team_id)
        pipe.zadd("standings:constructors", {team_id: float(totals["points"])})
        pipe.hset(f"constructor:{team_id}", mapping={
            "name":    team_name,
            "points":  totals["points"],
            "wins":    totals["wins"],
            "podiums": totals["podiums"],
        })

    pipe.execute()
    return f"Seeded real constructor standings for {len(constructor_totals)} teams"


def seed_driver_profiles(r: redis.Redis, data_dir: str) -> str:
    path = os.path.join(data_dir, "drivers.json")
    with open(path) as f:
        drivers = json.load(f)

    pipe = r.pipeline()
    for d in drivers:
        pipe.hset(f"driver:{d['_id']}", mapping={
            "name":    d["name"],
            "team_id": d["team_id"],
            "number":  d["number"],
            "code":    d["code"],
            "titles":  d["titles"],
        })
    pipe.execute()
    return f"Seeded {len(drivers)} driver profiles"


def seed_track_performance(r: redis.Redis, data_dir: str) -> str:
    """
    Seed per-circuit driver performance scores from race_results.json.
    Score = sum of (11 - position) for each finish (points-like, max 10 per race).
    Falls back to track_performance.json if present.
    """
    # Try race_results.json first (real data)
    race_results_path = os.path.join(data_dir, "race_results.json")
    circuits_path     = os.path.join(data_dir, "circuits.json")

    with open(circuits_path) as f:
        circuits = {c["_id"]: c for c in json.load(f)}

    if os.path.exists(race_results_path):
        with open(race_results_path) as f:
            results = json.load(f)

        # Aggregate scores per circuit per driver
        circuit_scores: dict[str, dict[str, float]] = {}
        for r_entry in results:
            circuit_id = r_entry["race_id"]
            driver_id  = r_entry["driver_id"]
            position   = r_entry["position"]
            # Score: 10 for 1st, 9 for 2nd … 1 for 10th, 0 beyond
            score = max(0, 11 - position)

            if circuit_id not in circuit_scores:
                circuit_scores[circuit_id] = {}
            circuit_scores[circuit_id][driver_id] = (
                circuit_scores[circuit_id].get(driver_id, 0) + score
            )

        pipe = r.pipeline()
        for circuit_id, driver_scores in circuit_scores.items():
            key = f"track:perf:{circuit_id}"
            pipe.delete(key)
            for driver_id, score in driver_scores.items():
                pipe.zadd(key, {driver_id: score})

            circuit_info = circuits.get(circuit_id, {})
            pipe.hset(f"circuit:{circuit_id}", mapping={
                "name": circuit_info.get("name", circuit_id),
                "type": circuit_info.get("type", "Unknown"),
            })

        pipe.execute()
        return f"Seeded track performance for {len(circuit_scores)} circuits from race_results.json"

    # Fallback: track_performance.json
    fallback_path = os.path.join(data_dir, "track_performance.json")
    if not os.path.exists(fallback_path):
        return "No track performance data found (race_results.json or track_performance.json required)"

    with open(fallback_path) as f:
        tracks = json.load(f)

    pipe = r.pipeline()
    for track in tracks:
        key = f"track:perf:{track['circuit_id']}"
        pipe.delete(key)
        for entry in track["driver_scores"]:
            pipe.zadd(key, {entry["driverId"]: float(entry["score"])})
        pipe.hset(f"circuit:{track['circuit_id']}", mapping={
            "name": track["circuit_name"],
            "type": track["type"],
        })
    pipe.execute()
    return f"Seeded performance data for {len(tracks)} circuits from track_performance.json"


# ─────────────────────────────────────────────
# DRIVER STANDINGS
# ─────────────────────────────────────────────

def get_driver_standings(r: redis.Redis, top_n: int = 20) -> list[dict]:
    entries = r.zrevrangebyscore(
        "standings:drivers", "+inf", "-inf", withscores=True, start=0, num=top_n
    )
    results = []
    for rank, (driver_id, points) in enumerate(entries, start=1):
        meta    = r.hgetall(f"standing:driver:{driver_id}")
        profile = r.hgetall(f"driver:{driver_id}")
        results.append({
            "rank":      rank,
            "driver_id": driver_id,
            "name":      profile.get("name", driver_id),
            "team":      profile.get("team_id", ""),
            "points":    int(points),
            "wins":      int(meta.get("wins", 0)),
            "podiums":   int(meta.get("podiums", 0)),
            "status":    meta.get("status", "Active"),
        })
    return results


def get_driver_rank(r: redis.Redis, driver_id: str) -> Optional[dict]:
    points = r.zscore("standings:drivers", driver_id)
    if points is None:
        return None
    rank    = r.zrevrank("standings:drivers", driver_id)
    meta    = r.hgetall(f"standing:driver:{driver_id}")
    profile = r.hgetall(f"driver:{driver_id}")
    return {
        "rank":      rank + 1,
        "driver_id": driver_id,
        "name":      profile.get("name", driver_id),
        "team":      profile.get("team_id", ""),
        "points":    int(points),
        "wins":      int(meta.get("wins", 0)),
        "podiums":   int(meta.get("podiums", 0)),
        "status":    meta.get("status", "Active"),
    }


def update_driver_points(r: redis.Redis, driver_id: str, delta: float) -> dict:
    new_score = r.zincrby("standings:drivers", delta, driver_id)
    rank      = r.zrevrank("standings:drivers", driver_id)
    return {"driver_id": driver_id, "new_points": int(new_score), "new_rank": rank + 1}


# ─────────────────────────────────────────────
# CONSTRUCTOR STANDINGS
# ─────────────────────────────────────────────

def get_constructor_standings(r: redis.Redis) -> list[dict]:
    entries = r.zrevrangebyscore("standings:constructors", "+inf", "-inf", withscores=True)
    results = []
    for rank, (cid, points) in enumerate(entries, start=1):
        meta = r.hgetall(f"constructor:{cid}")
        results.append({
            "rank":           rank,
            "constructor_id": cid,
            "name":           meta.get("name", cid),
            "points":         int(points),
            "wins":           int(meta.get("wins", 0)),
            "podiums":        int(meta.get("podiums", 0)),
        })
    return results


def get_constructor_rank(r: redis.Redis, constructor_id: str) -> Optional[dict]:
    points = r.zscore("standings:constructors", constructor_id)
    if points is None:
        return None
    rank = r.zrevrank("standings:constructors", constructor_id)
    meta = r.hgetall(f"constructor:{constructor_id}")
    return {
        "rank":           rank + 1,
        "constructor_id": constructor_id,
        "name":           meta.get("name", constructor_id),
        "points":         int(points),
        "wins":           int(meta.get("wins", 0)),
        "podiums":        int(meta.get("podiums", 0)),
    }


# ─────────────────────────────────────────────
# TRACK PERFORMANCE
# ─────────────────────────────────────────────

def get_track_performance(r: redis.Redis, circuit_id: str, top_n: int = 10) -> Optional[dict]:
    key = f"track:perf:{circuit_id}"
    if not r.exists(key):
        return None

    entries      = r.zrevrangebyscore(key, "+inf", "-inf", withscores=True, start=0, num=top_n)
    circuit_meta = r.hgetall(f"circuit:{circuit_id}")

    rankings = []
    for rank, (driver_id, score) in enumerate(entries, start=1):
        profile = r.hgetall(f"driver:{driver_id}")
        rankings.append({
            "rank":      rank,
            "driver_id": driver_id,
            "name":      profile.get("name", driver_id),
            "team":      profile.get("team_id", ""),
            "score":     round(score, 1),
        })

    return {
        "circuit_id":   circuit_id,
        "circuit_name": circuit_meta.get("name", circuit_id),
        "circuit_type": circuit_meta.get("type", ""),
        "rankings":     rankings,
    }


def get_driver_circuit_score(r: redis.Redis, driver_id: str, circuit_id: str) -> Optional[dict]:
    score = r.zscore(f"track:perf:{circuit_id}", driver_id)
    if score is None:
        return None
    rank = r.zrevrank(f"track:perf:{circuit_id}", driver_id)
    return {
        "driver_id":  driver_id,
        "circuit_id": circuit_id,
        "score":      round(score, 1),
        "rank":       rank + 1,
    }


def update_track_score(r: redis.Redis, circuit_id: str, driver_id: str, score: float) -> dict:
    r.zadd(f"track:perf:{circuit_id}", {driver_id: score})
    rank = r.zrevrank(f"track:perf:{circuit_id}", driver_id)
    return {"driver_id": driver_id, "circuit_id": circuit_id, "score": score, "rank": rank + 1}


# ─────────────────────────────────────────────
# LIVE RACE STATE
# ─────────────────────────────────────────────

def init_live_race(
    r: redis.Redis, race_id: str, race_name: str, total_laps: int, drivers: list[dict]
) -> dict:
    pipe = r.pipeline()

    pipe.hset(f"race:live:{race_id}:meta", mapping={
        "race_name":   race_name,
        "total_laps":  total_laps,
        "current_lap": 0,
        "status":      "starting",
        "started_at":  datetime.utcnow().isoformat(),
    })

    order_key = f"race:live:{race_id}:order"
    pipe.delete(order_key)

    for d in drivers:
        driver_id = d["driver_id"]
        pos       = d["start_position"]
        pipe.zadd(order_key, {driver_id: pos})
        pipe.hset(f"race:live:{race_id}:driver:{driver_id}", mapping={
            "position":      pos,
            "lap":           0,
            "gap_to_leader": "0.000",
            "tyre":          d.get("tyre", "Medium"),
            "pit_stops":     0,
            "status":        "Racing",
        })

    pipe.execute()
    return {"race_id": race_id, "status": "initialised", "drivers": len(drivers)}


def get_live_race_order(r: redis.Redis, race_id: str) -> Optional[dict]:
    meta_key = f"race:live:{race_id}:meta"
    if not r.exists(meta_key):
        return None

    meta    = r.hgetall(meta_key)
    entries = r.zrangebyscore(f"race:live:{race_id}:order", "-inf", "+inf", withscores=True)

    order = []
    for driver_id, pos in entries:
        state   = r.hgetall(f"race:live:{race_id}:driver:{driver_id}")
        profile = r.hgetall(f"driver:{driver_id}")
        order.append({
            "position":      int(pos),
            "driver_id":     driver_id,
            "name":          profile.get("name", driver_id),
            "team":          profile.get("team_id", ""),
            "lap":           int(state.get("lap", 0)),
            "gap_to_leader": state.get("gap_to_leader", "0.000"),
            "tyre":          state.get("tyre", "Medium"),
            "pit_stops":     int(state.get("pit_stops", 0)),
            "status":        state.get("status", "Racing"),
        })

    return {
        "race_id":     race_id,
        "race_name":   meta.get("race_name"),
        "total_laps":  int(meta.get("total_laps", 0)),
        "current_lap": int(meta.get("current_lap", 0)),
        "status":      meta.get("status"),
        "order":       order,
    }


def update_driver_lap_state(
    r: redis.Redis,
    race_id: str,
    driver_id: str,
    position: int,
    lap: int,
    gap_to_leader: str,
    tyre: Optional[str] = None,
    pit: bool = False,
    driver_status: str = "Racing",
) -> dict:
    pipe = r.pipeline()

    update = {
        "position":      position,
        "lap":           lap,
        "gap_to_leader": gap_to_leader,
        "status":        driver_status,
    }
    if tyre:
        update["tyre"] = tyre
    if pit:
        pipe.hincrby(f"race:live:{race_id}:driver:{driver_id}", "pit_stops", 1)

    pipe.hset(f"race:live:{race_id}:driver:{driver_id}", mapping=update)
    pipe.zadd(f"race:live:{race_id}:order", {driver_id: position})
    pipe.hset(f"race:live:{race_id}:meta", "current_lap", lap)
    pipe.execute()

    return {"race_id": race_id, "driver_id": driver_id, "position": position, "lap": lap}


def finish_race(r: redis.Redis, race_id: str) -> dict:
    r.hset(f"race:live:{race_id}:meta", mapping={
        "status":      "finished",
        "finished_at": datetime.utcnow().isoformat(),
    })
    return {"race_id": race_id, "status": "finished"}


def list_active_races(r: redis.Redis) -> list[str]:
    keys   = r.keys("race:live:*:meta")
    active = []
    for key in keys:
        status  = r.hget(key, "status")
        race_id = key.split(":")[2]
        if status != "finished":
            active.append(race_id)
    return active


# ─────────────────────────────────────────────
# PREDICTION CACHE
# ─────────────────────────────────────────────

PREDICTION_TTL = 3600


def get_cached_prediction(r: redis.Redis, circuit_id: str) -> Optional[dict]:
    key  = f"prediction:{circuit_id}"
    data = r.hgetall(key)
    if not data or "top3" not in data:
        return None
    return {
        "circuit_id":   circuit_id,
        "top3":         json.loads(data["top3"]),
        "analysis":     data.get("analysis", ""),
        "generated_at": data.get("generated_at", ""),
        "cached":       True,
    }


def store_prediction(r: redis.Redis, circuit_id: str, top3: list[dict], analysis: str) -> dict:
    key = f"prediction:{circuit_id}"
    now = datetime.utcnow().isoformat()
    pipe = r.pipeline()
    pipe.hset(key, mapping={
        "top3":         json.dumps(top3),
        "analysis":     analysis,
        "generated_at": now,
    })
    pipe.expire(key, PREDICTION_TTL)
    pipe.execute()
    return {"circuit_id": circuit_id, "generated_at": now, "ttl_seconds": PREDICTION_TTL}


def generate_prediction(r: redis.Redis, circuit_id: str) -> dict:
    """
    Generate a top-3 prediction for a circuit without ML.

    Algorithm:
      composite = 60% × track_performance_score + 40% × normalised_championship_points
    """
    track_key    = f"track:perf:{circuit_id}"
    circuit_meta = r.hgetall(f"circuit:{circuit_id}")

    if not r.exists(track_key):
        return {"error": f"No track performance data for circuit '{circuit_id}'"}

    track_entries = r.zrangebyscore(track_key, "-inf", "+inf", withscores=True)
    if not track_entries:
        return {"error": "No driver data for this circuit"}

    top_driver_id  = r.zrevrangebyscore("standings:drivers", "+inf", "-inf", start=0, num=1)
    max_points     = r.zscore("standings:drivers", top_driver_id[0]) if top_driver_id else 1
    max_points     = max(max_points or 1, 1)

    # Normalise track scores to 0-100 range
    track_scores   = [score for _, score in track_entries]
    max_track      = max(track_scores) if track_scores else 1

    composite = {}
    for driver_id, track_score in track_entries:
        norm_track  = (track_score / max_track) * 100
        champ_pts   = r.zscore("standings:drivers", driver_id) or 0
        norm_champ  = (champ_pts / max_points) * 100
        composite[driver_id] = round(0.60 * norm_track + 0.40 * norm_champ, 2)

    ranked = sorted(composite.items(), key=lambda x: x[1], reverse=True)

    top3 = []
    for pos, (driver_id, score) in enumerate(ranked[:3], start=1):
        profile = r.hgetall(f"driver:{driver_id}")
        top3.append({
            "position":        pos,
            "driver_id":       driver_id,
            "name":            profile.get("name", driver_id),
            "team":            profile.get("team_id", ""),
            "composite_score": score,
        })

    analysis = (
        f"Prediction for {circuit_meta.get('name', circuit_id)} "
        f"({circuit_meta.get('type', 'Unknown')} circuit). "
        f"Composite score = 60% normalised track performance + 40% normalised championship standing."
    )

    store_prediction(r, circuit_id, top3, analysis)
    return {"circuit_id": circuit_id, "top3": top3, "analysis": analysis, "cached": False}


def invalidate_prediction(r: redis.Redis, circuit_id: str) -> dict:
    deleted = r.delete(f"prediction:{circuit_id}")
    return {"circuit_id": circuit_id, "invalidated": bool(deleted)}
