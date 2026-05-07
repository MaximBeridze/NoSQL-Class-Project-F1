from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

if not URI or URI.strip() == "":
    raise RuntimeError(
        "NEO4J_URI is not configured. Set NEO4J_URI in .env or the environment, "
        "for example: bolt://localhost:7687"
    )

if not USER or USER.strip() == "":
    raise RuntimeError("NEO4J_USER is not configured.")

if PASSWORD is None or PASSWORD.strip() == "":
    raise RuntimeError("NEO4J_PASSWORD is not configured.")



driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def get_session():
    return driver.session(database=DATABASE)

def close_driver():
    driver.close()