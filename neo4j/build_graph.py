import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mongo.mongo_connection import db
from neo4j_repository import (
    create_driver,
    create_team,
    create_circuit,
    link_driver_team,
    update_driver_stats,
    link_driver_circuit,
    link_driver_season,
    create_teammates
)
from neo4j_connection import close_driver


# 
# BUILD GRAPH
# 
def build_graph():
    print("Building Neo4j graph from MongoDB Atlas...")

    # 
    # TEAMS
    # 
    print("Creating teams...")
    for t in db.teams.find():
        create_team(t["_id"], t["name"])

    # 
    # CIRCUITS
    # 
    print("Creating circuits...")
    for c in db.circuits.find():
        create_circuit(c["_id"], c["name"])

    # 
    # DRIVERS
    # 
    print("Creating drivers + relationships...")

    for d in db.drivers.find():
        driver_id = d["_id"]
        team_id = d["team_id"]

        create_driver(driver_id, d["name"])
        link_driver_team(driver_id, team_id)

        # optional: season link (based on standings or default year)
        link_driver_season(driver_id, 2025)

    # 
    # DRIVER STANDINGS (STATS)
    # 
    print("Updating driver stats...")

    for s in db.driver_standings.find():
        driver_id = s.get("driverId")

        if not driver_id:
            print("Skipping invalid record:", s)
            continue

        update_driver_stats(
            driver_id,
            s.get("points", 0),
            s.get("wins", 0),
            s.get("podiums", 0)
        )

    # 
    # CIRCUIT LINKS (basic assumption)
    # 
    print("Linking drivers to circuits...")

    for r in db.races.find():
        circuit_id = r["track"]

        # all drivers "participate" in race (simplified model)
        for d in db.drivers.find():
            link_driver_circuit(d["_id"], circuit_id)

    # 
    # CREATE TEAMS CONNECTIONS
    # 
    print("Creating teammate relationships...")
    create_teammates()

    print("Graph build complete!")


# 
# RUN
# 
if __name__ == "__main__":
    try:
        build_graph()
    finally:
        close_driver()