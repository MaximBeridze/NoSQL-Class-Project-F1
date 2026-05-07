from fastapi import FastAPI
from redis_db.redisRoutes import redis_router
import uvicorn

app = FastAPI(title="F1 Redis API", version="1.0.0")
app.include_router(redis_router, prefix="/redis")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)