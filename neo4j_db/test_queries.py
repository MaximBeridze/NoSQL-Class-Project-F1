from neo4j_db.neo4j_repository import (
    get_top_drivers,
    find_connection
)

print("Top Drivers:")
print(get_top_drivers())

print("\nConnection:")
print(find_connection("russell", "colapinto"))