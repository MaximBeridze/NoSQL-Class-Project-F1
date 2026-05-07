# NoSQL F1 Project Report

## 1. Project Idea

The main idea of this project is to build a Formula 1 race prediction and data analysis application using three NoSQL databases: MongoDB, Neo4j, and Redis.

The application stores and analyzes Formula 1 data such as drivers, teams, races, circuits, results, standings, and performance statistics.

The goal is to use each database for what it is best at:

- MongoDB is used for flexible document-based race and statistics data.
- Neo4j is used for graph relationships between drivers, teams, races, and circuits.
- Redis is used for caching and fast access to frequently requested data.

This allows the project to handle race data, relationship analysis, and fast repeated requests in one application.

---

## 2. MongoDB Use Case

### Why MongoDB was used

MongoDB was used because Formula 1 data can be stored naturally as documents.

For example, a race can contain information about the season, race name, circuit, and an array of results. Each result can contain the driver, team, position, and points.

MongoDB is useful in this project for storing:

- Driver profiles
- Team information
- Race results
- Circuit data
- Season standings
- Historical performance statistics
- Data used for race prediction

Example document:

```json
{
  "raceId": "monaco_2024",
  "season": 2024,
  "raceName": "Monaco Grand Prix",
  "circuit": {
    "name": "Circuit de Monaco",
    "country": "Monaco"
  },
  "results": [
    {
      "driverId": "VER",
      "driverName": "Max Verstappen",
      "team": "Red Bull Racing",
      "position": 1,
      "points": 25
    },
    {
      "driverId": "LEC",
      "driverName": "Charles Leclerc",
      "team": "Ferrari",
      "position": 2,
      "points": 18
    }
  ]
}
```

This document structure is useful because all data related to one race can be stored together.

---

### Aggregation Pipeline 1: Driver Total Points

This aggregation calculates the total number of points scored by each driver.

```javascript
db.races.aggregate([
  { $unwind: "$results" },
  {
    $group: {
      _id: "$results.driverName",
      totalPoints: { $sum: "$results.points" },
      racesEntered: { $sum: 1 }
    }
  },
  { $sort: { totalPoints: -1 } }
])
```

#### Purpose

The purpose of this pipeline is to create a driver ranking based on total points.

#### Explanation

The `$unwind` stage separates each result from the `results` array.  
The `$group` stage groups the data by driver name.  
The `$sum` operator calculates the total points for each driver.  
The `$sort` stage orders the drivers from highest to lowest points.

This is useful for generating driver standings and comparing driver performance across races.

---

### Aggregation Pipeline 2: Average Finishing Position by Team

This aggregation calculates the average finishing position of each team.

```javascript
db.races.aggregate([
  { $unwind: "$results" },
  {
    $group: {
      _id: "$results.team",
      averagePosition: { $avg: "$results.position" },
      totalResults: { $sum: 1 }
    }
  },
  { $sort: { averagePosition: 1 } }
])
```

#### Purpose

The purpose of this pipeline is to analyze which teams perform best on average.

#### Explanation

The `$unwind` stage separates each driver result inside the race document.  
The `$group` stage groups the results by team.  
The `$avg` operator calculates the average finishing position for each team.  
The `$sort` stage orders teams by their average position.

A lower average finishing position means better performance.

This is useful for comparing team performance during a season.

---

## 3. Neo4j Use Case

### Why Neo4j was used

Neo4j was used because Formula 1 data has many relationships.

A graph database is useful for showing connections between:

- Drivers
- Teams
- Races
- Circuits
- Seasons
- Teammates
- Race participation

For example:

- A driver drives for a team.
- A team participates in a race.
- A race is held at a circuit.
- Two drivers can be teammates.
- A driver can change teams between seasons.

This type of connected data is easier to explore in Neo4j than in a normal table-based structure.

Example graph structure:

```cypher
(:Driver {name: "Max Verstappen"})
  -[:DRIVES_FOR]->
(:Team {name: "Red Bull Racing"})
  -[:PARTICIPATED_IN]->
(:Race {name: "Monaco Grand Prix"})
  -[:HELD_AT]->
(:Circuit {name: "Circuit de Monaco"})
```

---

### Path Traversal Query

This query finds the path from a driver to the circuits they raced on through their team and race participation.

```cypher
MATCH path = (d:Driver {name: "Max Verstappen"})
  -[:DRIVES_FOR]->(t:Team)
  -[:PARTICIPATED_IN]->(r:Race)
  -[:HELD_AT]->(c:Circuit)
RETURN path
```

#### What it returns

This query returns a graph path like this:

```text
Driver -> Team -> Race -> Circuit
```

Example result:

```text
Max Verstappen -> Red Bull Racing -> Monaco Grand Prix -> Circuit de Monaco
```

#### Why it is useful

This query is useful because it shows how a driver is connected to races and circuits through their team.

It can help answer questions like:

- Which circuits has a driver raced on?
- Which races did a team participate in?
- Which circuits are connected to a specific driver?
- How is a driver connected to a specific race?

This is useful in Formula 1 because driver performance is connected to the team, the race, the circuit, and historical context.

---

### Additional Neo4j Query: Finding Teammates

This query finds drivers who are connected to the same team.

```cypher
MATCH (d1:Driver {name: "Charles Leclerc"})-[:DRIVES_FOR]->(t:Team)<-[:DRIVES_FOR]-(d2:Driver)
WHERE d1 <> d2
RETURN d1.name AS driver, t.name AS team, d2.name AS teammate
```

#### Purpose

The purpose of this query is to find a driver's teammates.

This is useful for comparing teammates, analyzing team performance, and understanding driver relationships.

---

## 4. Redis Use Case

### Why Redis was used

Redis was used to improve the performance of the application.

Some data is requested many times, such as driver standings, race predictions, team statistics, and leaderboards. Instead of querying MongoDB or Neo4j every time, the application can store the result in Redis and return it quickly.

Redis was mainly used as a caching layer.

---

### Data Stored in Redis

#### 1. Strings

Redis strings were used to store simple cached values, such as race prediction results.

Example:

```text
prediction:race:monaco_2024 = "Max Verstappen"
```

This stores the predicted winner of a race.

---

#### 2. Hashes

Redis hashes were used to store structured data about drivers.

Example:

```text
driver:VER
  name = Max Verstappen
  team = Red Bull Racing
  points = 250
  wins = 8
```

Hashes are useful because they store multiple fields under one key.

---

#### 3. Lists

Redis lists were used to store ordered recent activity, such as recent prediction requests.

Example:

```text
recent:predictions = [
  "monaco_2024",
  "silverstone_2024",
  "spa_2024"
]
```

This is useful for showing recently requested predictions.

---

#### 4. Sets

Redis sets were used to store unique values, such as favorite drivers or unique races viewed by a user.

Example:

```text
favorite:drivers:user1 = {
  "Max Verstappen",
  "Charles Leclerc",
  "Lewis Hamilton"
}
```

Sets are useful because they avoid duplicates automatically.

---

#### 5. Sorted Sets

Redis sorted sets were used for leaderboard-style data, such as driver rankings by points.

Example:

```text
leaderboard:drivers
  Max Verstappen -> 250
  Charles Leclerc -> 190
  Lewis Hamilton -> 160
```

Sorted sets are useful because Redis can quickly return rankings from highest score to lowest score.

---

### Role of Redis in the Project

Redis played the role of a cache and performance optimization layer.

Example flow:

```text
User requests driver standings
        ↓
Application checks Redis cache
        ↓
If data exists, return cached data
        ↓
If data does not exist, query MongoDB
        ↓
Store result in Redis
        ↓
Return data to user
```

Redis is useful in this project for:

- Cached race predictions
- Cached driver standings
- Cached team statistics
- Recent user activity
- Leaderboards
- Frequently requested API responses

This improves speed because Redis stores data in memory and can return results very quickly.

---

## 5. How the Three Databases Work Together

Each database has a different role in the project.

| Database | Main Role | Reason |
|---|---|---|
| MongoDB | Stores race, driver, team, and result documents | Flexible document storage |
| Neo4j | Stores relationships between drivers, teams, races, and circuits | Graph traversal and relationship analysis |
| Redis | Stores cached data and fast-access values | Performance optimization |

Together, they create a complete NoSQL architecture.

MongoDB stores the main application data.  
Neo4j handles connected relationship data.  
Redis makes the application faster by caching repeated queries.

---

## 6. Conclusion

This project demonstrates how different NoSQL databases can be used together in one application.

MongoDB is useful for storing flexible Formula 1 documents such as races, drivers, teams, and results. Neo4j is useful for exploring relationships between drivers, teams, races, and circuits. Redis is useful for improving performance by caching frequently requested data.

Using all three databases makes the application more powerful than using only one database because each database solves a different problem.