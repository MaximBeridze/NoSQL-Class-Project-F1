# Formula 1 Neo4j Prediction System

This project builds a graph-based Formula 1 data model using Neo4j, MongoDB, and Redis. It also includes a prediction engine that estimates race outcomes using historical performance, circuit statistics, and team strength.

## Disclaimer:
The race_results.jason dataset is a artifictially generated dataset to better simulate the project and is not refective of real world data

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
neo4j_db/
    neo4j_repository.py
    build_graph.py
prediction/
    prediction_engine.py
mongo/
    mongo_connection.py
redis_cache/
    cache_predictions.py
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

Create a `.env` file in the root of the project:

```bash
NEO4J_URI=your_uri
NEO4J_USER=your_user
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=your_database

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

To initiate redis cache:
Make sure you have docket destop running

```bash
docker run -d --name redis -p 6379:6379 redis
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
