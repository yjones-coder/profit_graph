import os
from neo4j import GraphDatabase

URI = os.environ.get("NEO4J_URI")
AUTH = (os.environ.get("NEO4J_USERNAME"), os.environ.get("NEO4J_PASSWORD"))

query = """
MATCH (v:Video)-->(s:Strategy)
RETURN v.id, substring(s.content, 0, 50) as preview
LIMIT 5
"""

try:
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        result = driver.execute_query(query)
        records = result.records
        if not records:
            print("❌ Database is EMPTY. The upload failed.")
        else:
            print(f"✅ Found {len(records)} entries:")
            for r in records:
                print(f"   - Video: {r['v.id']} | Strat: {r['preview']}...")
except Exception as e:
    print(f"❌ Connection Error: {e}")

