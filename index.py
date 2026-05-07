import sys
import os
import shutil


def init_env_file():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    example_path = os.path.join(os.path.dirname(__file__), ".env.example")

    if os.path.exists(env_path):
        print(".env already exists. No changes were made.")
        return

    if os.path.exists(example_path):
        shutil.copyfile(example_path, env_path)
        print(f"Created .env from .env.example at: {env_path}")
        return

    template = """NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

MONGO_URI=mongodb://localhost:27017
MONGO_DB=f1

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
"""
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(template)

    print(f"Created .env file at: {env_path}")
    print("Edit the file with your Neo4j, MongoDB, and Redis connection details before running the app.")


def run_load():
    print("\n--- Loading MongoDB data ---")
    from mongo.load_data import load_all as load_mongo
    load_mongo()
    print("Done.\n")


def run_build():
    print("\n--- Building Neo4j graph ---")
    from neo4j_db.build_graph import build_graph
    build_graph()
    print("Done.\n")


def run_predict():
    from prediction.prediction_engine import calculate_predictions

    circuit = input("Enter circuit id (e.g. imola): ").strip()

    print(f"\n--- Predicting results for {circuit} ---")

    predictions = calculate_predictions(circuit)

    print("\nTop predictions:\n")

    for i, p in enumerate(predictions[:10], start=1):
        print(f"{i}. {p['driverId']} → {p['chance']}%")


def run_seed_redis():
    print("\n--- Seeding Redis data ---")
    from redis_db.redis_service import seed_all as seed_redis
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
  python index.py init-env   → Create .env from .env.example
  python index.py predict    → Run prediction
  python index.py all        → Run everything

Examples:
  python index.py load
  python index.py build
  python index.py seed-redis
  python index.py init-env
  python index.py all
""")


if __name__ == "__main__":

    init_env_file()

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

    elif command == "init-env":
        init_env_file()

    elif command == "predict":
        run_predict()

    elif command == "all":
        run_all()

    else:
        print("Unknown command.\n")
        print_help()