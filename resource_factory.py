import os
import sys
import argparse
from pathlib import Path
from google import genai
from neo4j import GraphDatabase

# --- SIMPLE ENV LOADER ---
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.strip().split('=', 1)
                os.environ[k] = v

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if __name__ == "__main__":
    if not all([NEO4J_URI, NEO4J_PASSWORD, GEMINI_API_KEY]):
        print("❌ ERROR: Missing Keys in .env")
        sys.exit(1)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    client = genai.Client(api_key=GEMINI_API_KEY)

def get_graph_context(topic):
    query = """
    MATCH (n {name: $topic})-[r]-(connected)
    RETURN n, r, connected LIMIT 20
    """
    context = []
    try:
        with driver.session() as session:
            result = session.run(query, topic=topic)
            for record in result:
                n = record['n']
                r = record['r']
                c = record['connected']
                status = n.get('fact_check', 'Unverified')
                context.append(f"{n['name']} ({status}) --[{r.type}]--> {c['name']} (Desc: {c.get('verified_desc', c.get('video_desc'))})")
    except Exception as e:
        return f"Error: {e}"
    
    if not context: return "No data found in Graph."
    return "\n".join(context)

def generate_plan(topic, context):
    print(f"🚀 Generating Plan for: {topic}")
    prompt = f"""
    Create a Profit Implementation Plan for {topic}.
    
    GRAPH CONTEXT:
    {context}
    
    INSTRUCTIONS:
    1. Verify tool claims based on the 'fact_check' status in context.
    2. Highlight any discrepancies (e.g., if video said free but context says paid).
    3. Outline the stack, the problem solved, and the service to sell.
    """
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt) # UPDATED MODEL
    return response.text

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("task", choices=["plan", "flashcards"])
    parser.add_argument("topic")
    args = parser.parse_args()

    context = get_graph_context(args.topic)
    print(f"📊 Graph Context Loaded.")
    
    if args.task == "plan":
        output = generate_plan(args.topic, context)
        filename = f"{args.topic}_plan.md"
        with open(filename, "w") as f:
            f.write(output)
        print(f"✅ Saved to {filename}")

if __name__ == "__main__":
    main()



