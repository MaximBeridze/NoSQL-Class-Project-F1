from mongo.mongo_connection import db


def top_drivers_by_points():
    pipeline = [
        {
            "$sort": {
                "points": -1
            }
        },
        {
            "$limit": 10
        }
    ]

    return list(db.driver_standings.aggregate(pipeline))



def top_winning_teams():
    pipeline = [
        {
            "$lookup": {
                "from": "drivers",
                "localField": "driverId",
                "foreignField": "_id",
                "as": "driver"
            }
        },
        {
            "$unwind": "$driver"
        },
        {
            "$group": {
                "_id": "$driver.team_id",
                "total_points": {
                    "$sum": "$points"
                },
                "total_wins": {
                    "$sum": "$wins"
                }
            }
        },
        {
            "$sort": {
                "total_points": -1
            }
        }
    ]

    return list(db.driver_standings.aggregate(pipeline))