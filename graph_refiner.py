#!/usr/bin/env python
import os
import json
import sys
import profit_config as cfg
from google import genai
from google.genai import types
from neo4j import GraphDatabase

# --- CONFIGURATION ---
# Database: Uses the new Centralized Config
NEO4J_URI = cfg.NEO4J_URI
NEO4J_AUTH = cfg.NEO4J_AUTH

# AI Keys: Still read from Environment (Best Practice)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in environment.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

def get_unrefined_strategies(session):
    # Find Strategies that haven't been "Refined" yet
    query = """
    MATCH (s:Strategy)
    WHERE NOT (s)-[:REFINED_BY]->(:RefinerLog)
    RETURN s.id as id, s.content as text
    LIMIT 5
    """
    return session.run(query).data()

def identify_relationships(text):
    print("   🤔 AI Analyst is thinking...")
    prompt = f"""
    Analyze this tech strategy brief.
    Identify technical relationships between tools/concepts mentioned.

    Return a JSON list of relationships using these specific verbs:
    - "INTEGRATES_WITH" (e.g. IDE uses Model)
    - "RUNS_ON" (e.g. App runs on Cloud)
    - "COMPETES_WITH" (e.g. Claude vs GPT-4)
    - "MITIGATES" (e.g. Cache mitigates Latency)

    Output Format (Strict JSON):
    [
        {{"source": "Cursor", "target": "Claude 3.5", "rel": "INTEGRATES_WITH"}},
        {{"source": "Supabase", "target": "Firebase", "rel": "COMPETES_WITH"}}
    ]

    Text:
    {text[:5000]}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        text_resp = response.text.strip()
        # Clean potential markdown
        if text_resp.startswith("```json"): text_resp = text_resp[7:]
        if text_resp.startswith("```"): text_resp = text_resp[3:]
        if text_resp.endswith("```"): text_resp = text_resp[:-3]
        return json.loads(text_resp.strip())
    except Exception as e:
        print(f"   ⚠️ AI Error: {e}")
        return []

def apply_relationships(session, relationships, strategy_id):
    count = 0
    for r in relationships:
        try:
            # Cypher query to create the link
            q = f"""
            MERGE (a:Entity {{name: $source}})
            MERGE (b:Entity {{name: $target}})
            MERGE (a)-[:{r['rel']}]->(b)
            """
            session.run(q, source=r['source'], target=r['target'])
            count += 1
        except Exception as e:
            # Often caused by invalid characters in entity names
            continue

    # Mark as Refined
    session.run("""
        MATCH (s:Strategy {id: $sid})
        MERGE (l:RefinerLog {timestamp: datetime()})
        MERGE (s)-[:REFINED_BY]->(l)
    """, sid=strategy_id)

    print(f"   ✅ Injected {count} new connections.")

def main():
    print(f"🔌 Connecting to Cloud Graph...")
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
        with driver.session() as session:
            print("🔍 Scanning Graph for unrefined strategies...")
            strategies = get_unrefined_strategies(session)

            if not strategies:
                print("✅ All strategies are already refined!")
                return

            for strat in strategies:
                print(f"\n🧠 Refining Strategy: {strat['id']}...")
                rels = identify_relationships(strat['text'])
                if rels:
                    apply_relationships(session, rels, strat['id'])
                else:
                    print("   (No relationships found)")
        driver.close()
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    main()
