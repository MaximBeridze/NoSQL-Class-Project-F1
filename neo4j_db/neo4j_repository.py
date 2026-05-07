from neo4j_db.neo4j_connection import get_session


from neo4j_db.neo4j_connection import get_session


# -------------------------
# CORE RUNNER
# -------------------------
def run(query, params=None):
    params = params or {}
    with get_session() as session:
        result = session.run(query, params)
        return [r.data() for r in result]


# -------------------------
# CLEAR DATABASE
# -------------------------
def clear_database():
    return run("MATCH (n) DETACH DELETE n")



# -------------------------
# NODES
# -------------------------
def create_driver(d):
    return run("""
        MERGE (x:Driver {id: $id})
        SET x.name = $name,
            x.number = $number,
            x.code = $code,
            x.titles = $titles,
            x.wins = coalesce(x.wins, 0)
    """, {
        "id": d.get("_id") or d.get("id"),
        "name": d.get("name"),
        "number": d.get("number"),
        "code": d.get("code"),
        "titles": d.get("titles", 0)
    })


def create_team(t):
    return run("""
        MERGE (x:Team {id: $id})
        SET x.name = $name,
            x.principal = $principal,
            x.chassis = $chassis,
            x.engine = $engine,
            x.all_time_wins = coalesce(x.all_time_wins, 0)
    """, {
        "id": t.get("_id") or t.get("id"),
        "name": t.get("name"),
        "principal": t.get("principal"),
        "chassis": t.get("chassis"),
        "engine": t.get("engine")
    })


def create_constructor(c):
    return run("""
        MERGE (x:Constructor {id: $id})
        SET x.name = $name,
            x.base = $base,
            x.principal = $principal
    """, {
        "id": c.get("_id") or c.get("id"),
        "name": c.get("name"),
        "base": c.get("base"),
        "principal": c.get("principal")
    })


def create_circuit(c):
    return run("""
        MERGE (x:Circuit {id: $id})
        SET x.name = $name,
            x.location = $location,
            x.length_km = $length_km,
            x.corners = $corners,
            x.type = $type
    """, {
        "id": c.get("_id") or c.get("id"),
        "name": c.get("name"),
        "location": c.get("location"),
        "length_km": c.get("length_km"),
        "corners": c.get("corners"),
        "type": c.get("type")
    })


def create_race(r):
    return run("""
        MERGE (x:Race {id: $id})
        SET x.name = $name,
            x.round = $round,
            x.city = $city,
            x.laps = $laps
    """, {
        "id": r.get("_id") or r.get("id"),
        "name": r.get("gp"),
        "round": r.get("round"),
        "city": r.get("city"),
        "laps": r.get("laps")
    })


def create_season(s):
    return run("""
        MERGE (x:Season {year: $year})
        SET x.status = $status,
            x.regulations = $regulations,
            x.wikipedia = $wikipedia
    """, {
        "year": s.get("year") or s.get("_id"),
        "status": s.get("status"),
        "regulations": s.get("regulations"),
        "wikipedia": s.get("wikipedia")
    })


# -------------------------
# RELATIONSHIPS
# -------------------------
def link_driver_team(driver_id, team_id):
    return run("""
        MATCH (d:Driver {id: $d})
        MATCH (t:Team {id: $t})
        MERGE (d)-[:DRIVES_FOR]->(t)
    """, {"d": driver_id, "t": team_id})


def link_race_circuit(race_id, circuit_id):
    return run("""
        MATCH (r:Race {id: $r})
        MATCH (c:Circuit {id: $c})
        MERGE (r)-[:HELD_AT]->(c)
    """, {"r": race_id, "c": circuit_id})


def link_driver_season(driver_id, year):
    return run("""
        MATCH (d:Driver {id: $d})
        MERGE (s:Season {year: $y})
        MERGE (d)-[:RACED_IN_SEASON]->(s)
    """, {
        "d": driver_id,
        "y": year
    })


def link_race_season(race_id, year):
    return run("""
        MATCH (r:Race {id: $r})
        MERGE (s:Season {year: $y})
        MERGE (r)-[:PART_OF]->(s)
    """, {
        "r": race_id,
        "y": year
    })


# -------------------------
# RESULTS (FIXED MODEL)
# -------------------------
def link_race_result(driver_id, race_id, position, points):
    return run("""
        MATCH (d:Driver {id: $d})
        MATCH (r:Race {id: $r})

        MERGE (d)-[rel:RESULT_IN]->(r)

        SET rel.position = $position,
            rel.points = $points
    """, {
        "d": driver_id,
        "r": race_id,
        "position": position,
        "points": points
    })


def link_win(driver_id, race_id):
    return run("""
        MATCH (d:Driver {id: $d})
        MATCH (r:Race {id: $r})

        MERGE (d)-[w:WON_AT]->(r)
        ON CREATE SET w.count = 1
        ON MATCH SET w.count = w.count + 1

        SET d.wins = coalesce(d.wins, 0) + 1
    """, {"d": driver_id, "r": race_id})


def load_race_results(results):
    print(f"Loading race results... ({len(results)})")

    for r in results:
        driver_id = r["driver_id"]
        race_id = r["race_id"]

        link_race_result(
            driver_id,
            race_id,
            r["position"],
            r.get("points", 0)
        )

        if r["position"] == 1:
            link_win(driver_id, race_id)


# -------------------------
# TEAMMATES
# -------------------------
def create_teammates():
    return run("""
        MATCH (d1:Driver)-[:DRIVES_FOR]->(t:Team)<-[:DRIVES_FOR]-(d2:Driver)
        WHERE d1.id < d2.id
        MERGE (d1)-[:TEAMMATE_OF]->(d2)
        MERGE (d2)-[:TEAMMATE_OF]->(d1)
    """)


# -------------------------
# FIXED PREDICTION QUERIES
# -------------------------
def get_driver_circuit_stats(driver_id, circuit_id):
    result = run("""
        MATCH (d:Driver {id: $driver})-[r:RESULT_IN]->(race:Race)-[:HELD_AT]->(c:Circuit {id: $circuit})
        RETURN count(r) AS races
    """, {"driver": driver_id, "circuit": circuit_id})

    return result[0]["races"] if result else 0


def get_driver_circuit_wins(driver_id, circuit_id):
    result = run("""
        MATCH (d:Driver {id: $driver})-[r:RESULT_IN]->(race:Race)-[:HELD_AT]->(c:Circuit {id: $circuit})
        WHERE r.position = 1
        RETURN count(r) AS wins
    """, {"driver": driver_id, "circuit": circuit_id})

    return result[0]["wins"] if result else 0


def get_driver_avg_finish(driver_id):
    result = run("""
        MATCH (d:Driver {id: $driver})-[r:RESULT_IN]->(:Race)
        RETURN avg(r.position) AS avg_finish
    """, {"driver": driver_id})

    if result and result[0]["avg_finish"] is not None:
        return float(result[0]["avg_finish"])

    return 20.0


def get_team_strength(team_id):
    result = run("""
        MATCH (d:Driver)-[:DRIVES_FOR]->(t:Team {id: $team})
        RETURN avg(d.wins) AS avg_wins
    """, {"team": team_id})

    if result and result[0]["avg_wins"] is not None:
        return float(result[0]["avg_wins"])

    return 0