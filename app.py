import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn

project_root = Path(__file__).resolve().parent
env_path = project_root / ".env"
env_example = project_root / ".env.example"

if not env_path.exists():
    if env_example.exists():
        shutil.copyfile(env_example, env_path)
    else:
        env_path.write_text(
            "NEO4J_URI=bolt://localhost:7687\n"
            "NEO4J_USER=neo4j\n"
            "NEO4J_PASSWORD=your_password\n\n"
            "MONGO_URI=mongodb://localhost:27017\n"
            "MONGO_DB=f1\n\n"
            "REDIS_HOST=localhost\n"
            "REDIS_PORT=6379\n"
            "REDIS_DB=0\n",
            encoding="utf-8",
        )

load_dotenv()

from redis_db.redisRoutes import redis_router

app = FastAPI(title="F1 Redis API", version="1.0.0")
app.include_router(redis_router, prefix="/redis")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)