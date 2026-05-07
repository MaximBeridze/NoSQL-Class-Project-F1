from mongo.mongo_connection import db
from neo4j_db.neo4j_repository import *
from neo4j_db.neo4j_connection import close_driver


def build_graph():

    print("\n--- Building F1 Neo4j Graph ---\n")

    clear_database()

    # -----------------------
    # TEAMS
    # -----------------------
    print("Creating teams...")
    for t in db.teams.find():
        create_team(t)
    print("Teams loaded\n")

    # -----------------------
    # CIRCUITS
    # -----------------------
    print("Creating circuits...")
    for c in db.circuits.find():
        create_circuit(c)
    print("Circuits loaded\n")

    # -----------------------
    # SEASONS
    # -----------------------
    print("Creating seasons...")
    for s in db.seasons.find():
        create_season(s)
    print("Seasons loaded\n")

    # -----------------------
    # RACES
    # -----------------------
    print("Creating races...")

    for r in db.races.find():

        race_id = r["track"]

        create_race({
            "_id": race_id,
            "gp": r["gp"],
            "round": r["round"],
            "city": r["city"],
            "laps": r["laps"]
        })

        link_race_circuit(race_id, r["track"])
        link_race_season(race_id, 2025)

    print("Races loaded\n")

    # -----------------------
    # DRIVERS
    # -----------------------
    print("Creating drivers...")

    for d in db.drivers.find():
        create_driver(d)
        link_driver_team(d["_id"], d["team_id"])
        link_driver_season(d["_id"], 2025)

    print("Drivers loaded\n")

    # -----------------------
    # RESULTS
    # -----------------------
    print("Loading results...")

    load_race_results(list(db.race_results.find()))

    print("Results loaded\n")

    create_teammates()

    print("--- Graph build complete ---")


if __name__ == "__main__":
    try:
        build_graph()
    finally:
        close_driver()