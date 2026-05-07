# Formula 1 Neo4j Prediction System

This project builds a graph-based Formula 1 data model using Neo4j, MongoDB, and Redis. It also includes a prediction engine that estimates race outcomes using historical performance, circuit statistics, and team strength.

## Disclaimer:
The race_results.json dataset is an artificially generated dataset used to better simulate the project and is not reflective of real-world data.

---

## Features

- Graph database modeling with Neo4j
- Race, driver, team, circuit, and season relationships
- Performance-based prediction engine
- MongoDB as primary data source
- Redis caching for predictions
- Circuit-specific driver analysis
- Dynamic scoring system combining multiple factors

---

## Project Structure

```
redis_db/
    __init__.py
    redis_service.py
    redisRoutes.py
    redisModels.py
    redis_cache/
neo4j_db/
    neo4j_repository.py
    build_graph.py
prediction/
    prediction_engine.py
mongo/
    mongo_connection.py
app.py
index.py
```

---

## Requirements

- Python 3.10+
- Neo4j Database
- MongoDB
- Redis
- Docker Desktop

---

## Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment Setup (.env)

You are provided with a `.env.example` file, create your `.env` from it with:

```bash
python app.py
```

If `.env` already exists, this command will not overwrite it.

Then edit `.env` with your actual connection values if needed:

```bash
NEO4J_URI=your_uri
NEO4J_USER=your_user
NEO4J_PASSWORD=your_password

MONGO_URI=your_uri
MONGO_DB=f1

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

---

## Load Data

To load data into MongoDB:

```bash
python index.py load
```

---

## Build Graph

To build the Neo4j graph from MongoDB:

```bash
python index.py build
```

This will:

- Clear Neo4j database
- Load teams, drivers, circuits, seasons, races
- Create relationships
- Load race results
- Generate teammate relationships

---

## Cache

To initiate Redis cache, make sure Redis is running locally.

Using Docker:

```bash
docker run -d --name redis -p 6379:6379 redis
```

Or install Redis locally and start the service.

---

## Run API

Start the FastAPI server:

```bash
python app.py
```

Or for development:

```bash
uvicorn app:app --reload
```

The API is available at:

```text
http://localhost:8000/redis
```

### Main API endpoints

- `GET /redis/standings/drivers`
- `GET /redis/standings/drivers/{driver_id}`
- `PATCH /redis/standings/drivers/{driver_id}/points`
- `GET /redis/standings/constructors`
- `GET /redis/track/{circuit_id}/performance`
- `GET /redis/track/{circuit_id}/driver/{driver_id}`
- `POST /redis/race/{race_id}/init`
- `GET /redis/race/{race_id}/live`
- `PATCH /redis/race/{race_id}/driver/{driver_id}/lap`
- `GET /redis/predict/{circuit_id}`

---

## Seed Redis Data

Load Redis data from `data/` with:

```bash
python index.py seed-redis
```

---

## Run Predictions

To run race predictions:

```bash
python index.py predict
```

You will be prompted:

```text
Enter circuit id (e.g. imola): hungaroring
```

The system will output predicted finishing probabilities for each driver.

---

## Data Preview

To preview data (driver, positions, points, etc):

Using Postman, or any API testing software, send a GET request to:

```bash
http://localhost:8000/redis/standings/drivers
```

## Prediction Model

The prediction engine combines:

- Historical wins and podiums (MongoDB)
- Circuit-specific performance (Neo4j)
- Average finishing position
- Team strength
- Championship momentum

Final score is normalized into percentage probabilities.

---



## Common Issues

### Missing driverId / inconsistent fields

Ensure MongoDB `driver_standings` uses consistent field names:
- driverId or driver_id
- points
- wins
- podiums

---

### Neo4j parameter errors

If you see:

```
Expected parameter(s): id
```

Check that:
- MongoDB documents include `_id`
- Repository functions correctly map `_id` → `id`

---

### Empty or identical predictions

This usually means:
- Neo4j graph not built correctly
- Missing race_results relationships
- Circuit IDs do not match between MongoDB and Neo4j

---

## Debug Tips

To verify data in Neo4j:

```cypher
MATCH (d:Driver) RETURN d
MATCH (r:Race) RETURN r
MATCH (d)-[rel:RESULT_IN]->(r:Race) RETURN d, rel, r
```

---

## License

This project is for educational use.