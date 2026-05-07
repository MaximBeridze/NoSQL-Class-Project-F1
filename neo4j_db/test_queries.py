"""
test_queries.py
───────────────
Quick sanity-check queries against the Neo4j graph.

NOTE: get_top_drivers() and find_connection() were imported here but were never
defined in neo4j_repository.py — this file crashed with ImportError.
Replaced with functions that actually exist in the repository.
"""

from neo4j_db.neo4j_repository import (
    get_driver_circuit_stats,
    get_driver_circuit_wins,
    get_driver_avg_finish,
    get_team_strength,
    run,
)


def get_top_drivers(limit: int = 5) -> list:
    """Return top drivers by wins stored on Driver nodes."""
    return run("""
        MATCH (d:Driver)
        WHERE d.wins IS NOT NULL
        RETURN d.id AS driver_id, d.name AS name, d.wins AS wins
        ORDER BY d.wins DESC
        LIMIT $limit
    """, {"limit": limit})


def find_connection(driver1_id: str, driver2_id: str) -> list:
    """
    Find the shortest path between two drivers in the graph.
    Useful for discovering shared teammates, races, or circuits.
    """
    return run("""
        MATCH path = shortestPath(
            (a:Driver {id: $d1})-[*]-(b:Driver {id: $d2})
        )
        RETURN [n IN nodes(path) | coalesce(n.name, n.id, toString(n))] AS path_nodes,
               length(path) AS hops
    """, {"d1": driver1_id, "d2": driver2_id})


if __name__ == "__main__":
    print("Top Drivers by wins:")
    for d in get_top_drivers():
        print(f"  {d['name']} — {d['wins']} wins")

    print("\nConnection: russell → colapinto")
    result = find_connection("russell", "colapinto")
    if result:
        print(f"  Path ({result[0]['hops']} hops): {' → '.join(result[0]['path_nodes'])}")
    else:
        print("  No path found")

    print("\nCircuit stats: norris at monaco")
    races = get_driver_circuit_stats("norris", "monaco")
    wins  = get_driver_circuit_wins("norris", "monaco")
    print(f"  Races: {races}, Wins: {wins}")

    print("\nAvg finish: norris")
    print(f"  {get_driver_avg_finish('norris'):.2f}")

    print("\nTeam strength: mclaren")
    print(f"  {get_team_strength('mclaren'):.2f}")
