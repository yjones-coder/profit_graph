import os
import sys
from neo4j import GraphDatabase

# --- CONFIGURATION (From Env Vars) ---
URI = os.environ.get("NEO4J_URI")
USER = os.environ.get("NEO4J_USERNAME", "neo4j")
PASSWORD = os.environ.get("NEO4J_PASSWORD")

def apply_constraints():
    if not URI or not PASSWORD:
        print("❌ Error: Environment variables missing.")
        print("Run: export NEO4J_URI='...' and export NEO4J_PASSWORD='...'")
        sys.exit(1)

    print(f"Connecting to Cloud DB: {URI}...")
    
    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        with driver.session() as session:
            print("Applying 'Defensive Engineering' Constraints...")
            
            # 1. Unique Constraint (Deduplication)
            # This prevents duplicate "OpenAI" nodes when processing multiple videos
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (n:Entity) REQUIRE n.name IS UNIQUE")
            
            # 2. Performance Indexes
            session.run("CREATE INDEX IF NOT EXISTS FOR (t:Tool) ON (t.name)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (r:Risk) ON (r.name)")
            
            print("✅ Constraints Active. Graph is ready for batch ingestion.")
        driver.close()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    apply_constraints()

