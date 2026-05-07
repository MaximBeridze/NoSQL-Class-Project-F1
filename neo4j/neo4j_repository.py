from neo4j_connection import get_session

def run(query, params=None):
    params = params or {}

    with get_session() as session:
        result = session.run(query, params)
        return [r.data() for r in result]


# -------- NODES --------

def create_driver(driver_id, name):
    return run("""
        MERGE (d:Driver {id: $id})
        SET d.name = $name
    """, {"id": driver_id, "name": name})


def create_team(team_id, name):
    return run("""
        MERGE (t:Team {id: $id})
        SET t.name = $name
    """, {"id": team_id, "name": name})


def create_circuit(circuit_id, name):
    return run("""
        MERGE (c:Circuit {id: $id})
        SET c.name = $name
    """, {"id": circuit_id, "name": name})


# -------- RELATIONSHIPS --------

def link_driver_team(driver_id, team_id):
    return run("""
        MATCH (d:Driver {id: $d})
        MATCH (t:Team {id: $t})
        MERGE (d)-[:DRIVES_FOR]->(t)
    """, {"d": driver_id, "t": team_id})


def link_driver_circuit(driver_id, circuit_id):
    return run("""
        MATCH (d:Driver {id: $d})
        MATCH (c:Circuit {id: $c})
        MERGE (d)-[:RACED_AT]->(c)
    """, {"d": driver_id, "c": circuit_id})

def create_teammates():
    return run("""
        MATCH (d1:Driver)-[:DRIVES_FOR]->(t:Team)<-[:DRIVES_FOR]-(d2:Driver)
        WHERE d1.id < d2.id
        MERGE (d1)-[:TEAMMATE_OF]->(d2)
        MERGE (d2)-[:TEAMMATE_OF]->(d1)
    """)

def link_driver_season(driver_id, year):
    return run("""
        MERGE (s:Season {year: $year})
        WITH s
        MATCH (d:Driver {id: $id})
        MERGE (d)-[:RACED_IN]->(s)
    """, {"id": driver_id, "year": year})

def link_driver_win(driver_id, circuit_id):
    return run("""
        MATCH (d:Driver {id: $d})
        MATCH (c:Circuit {id: $c})
        MERGE (d)-[:WON_AT]->(c)
    """, {"d": driver_id, "c": circuit_id})

def update_driver_stats(driver_id, points, wins, podiums):
    return run("""
        MATCH (d:Driver {id: $id})
        SET d.points = coalesce($points, 0),
            d.wins = coalesce($wins, 0),
            d.podiums = coalesce($podiums, 0)
    """, {
        "id": driver_id,
        "points": points,
        "wins": wins,
        "podiums": podiums
    })


# -------- QUERIES --------

def get_top_drivers():
    return run("""
        MATCH (d:Driver)
        RETURN d.id AS id, d.name AS name, d.wins AS wins
        ORDER BY wins DESC
    """)


def find_connection(d1, d2):
    return run("""
        MATCH path = shortestPath(
            (a:Driver {id: $d1})-[*]-(b:Driver {id: $d2})
        )
        RETURN path
    """, {"d1": d1, "d2": d2})