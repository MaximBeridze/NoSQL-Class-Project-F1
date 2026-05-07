import json
import os
from mongo.mongo_connection import db

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_FOLDER = os.path.abspath(DATA_FOLDER)

files = {
    "drivers.json": "drivers",
    "teams.json": "teams",
    "circuits.json": "circuits",
    "driver_standings.json": "driver_standings",
    "races.json": "races",
    "seasons.json": "seasons",
    "results.json": "results",
    "race_results.json": "race_results"
}

def clean_document(doc):
    if "_id" in doc and isinstance(doc["_id"], dict):
        # convert {"$oid": "..."} → "..."
        doc["_id"] = doc["_id"].get("$oid", doc["_id"])
    return doc

def load_all():
    for file, collection in files.items():
        path = os.path.join(DATA_FOLDER, file)

        if not os.path.exists(path):
            print(f"⚠️ Missing {file}")
            continue

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        db[collection].delete_many({})

        if isinstance(data, list):
            cleaned_data = [clean_document(d) for d in data]
            db[collection].insert_many(cleaned_data)
        else:
            db[collection].insert_one(data)

        print(f"Loaded {file} → {collection}")

if __name__ == "__main__":
    load_all()