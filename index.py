import sys

from mongo.load_data import load_all as load_mongo
from neo4j_db.build_graph import build_graph
from prediction.prediction_engine import calculate_predictions
from redis_db.redis_service import seed_all as seed_redis


def run_load():
    print("\n--- Loading MongoDB data ---")
    load_mongo()
    print("Done.\n")


def run_build():
    print("\n--- Building Neo4j graph ---")
    build_graph()
    print("Done.\n")


def run_predict():
    circuit = input("Enter circuit id (e.g. imola): ").strip()

    print(f"\n--- Predicting results for {circuit} ---")

    predictions = calculate_predictions(circuit)

    print("\nTop predictions:\n")

    for i, p in enumerate(predictions[:10], start=1):
        print(f"{i}. {p['driverId']} → {p['chance']}%")


def run_seed_redis():
    print("\n--- Seeding Redis data ---")
    results = seed_redis()
    print("Seeding results:", results)
    print("Done.\n")


def run_all():
    run_load()
    run_build()
    run_seed_redis()
    run_predict()


def print_help():
    print("""
Usage:
  python index.py load       → Load MongoDB data
  python index.py build      → Build Neo4j graph
  python index.py seed-redis → Seed Redis with data
  python index.py predict    → Run prediction
  python index.py all        → Run everything

Examples:
  python index.py load
  python index.py build
  python index.py seed-redis
  python index.py predict
  python index.py all
""")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print_help()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "load":
        run_load()

    elif command == "build":
        run_build()

    elif command == "seed-redis":
        run_seed_redis()

    elif command == "predict":
        run_predict()

    elif command == "all":
        run_all()

    else:
        print("Unknown command.\n")
        print_help()