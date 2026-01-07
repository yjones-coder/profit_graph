#!/usr/bin/env python
import os
import sys
import json
from google import genai
from google.genai import types
from neo4j import GraphDatabase

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USERNAME")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

if not GEMINI_API_KEY or not NEO4J_URI:
    print("❌ Error: Missing API Keys. Ensure GEMINI_API_KEY and NEO4J_* are exported.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# --- UTILS ---
def clean_code_block(text):
    text = text.strip()
    if text.startswith("```cypher"): text = text[9:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

class ProfitOracle:
    def __init__(self):
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            self.schema = self.get_schema()
            print(f"🔮 Oracle initialized. Connected to: {NEO4J_URI}")
        except Exception as e:
            print(f"❌ Connection Error: {e}")
            sys.exit(1)

    def close(self):
        if self.driver:
            self.driver.close()

    def get_schema(self):
        """Fetches the current graph structure to inform the AI."""
        query = """
        CALL db.schema.visualization()
        """
        with self.driver.session() as session:
            result = session.run(query)
            record = result.single()
            nodes = [n.labels for n in record['nodes']]
            rels = [r.type for r in record['relationships']]
            
            schema_summary = f"Nodes: {nodes}\nRelationships: {rels}"
            # Also get a sample of Strategy properties
            sample_q = "MATCH (s:Strategy) RETURN keys(s) LIMIT 1"
            sample = session.run(sample_q).single()
            if sample:
                schema_summary += f"\nStrategy Properties: {sample[0]}"
                
            return schema_summary

    def generate_cypher(self, user_question):
        prompt = f"""
        You are a Neo4j Cypher Expert.
        Convert this question into a READ-ONLY Cypher query.
        
        Schema:
        {self.schema}
        
        CRITICAL: The :Video nodes ONLY have an 'id' (e.g., 'S2MP49...'). They do NOT have titles.
        To find a specific topic (like 'Rocket AI' or 'Pricing'), you must use CONTAINS on the Strategy content.
        
        Correct Pattern Example:
        MATCH (v:Video)-[:YIELDS_STRATEGY]->(s:Strategy)
        WHERE toLower(s.content) CONTAINS toLower('Rocket AI') 
        RETURN s.content LIMIT 1
        
        Question: "{user_question}"
        
        Output ONLY the Cypher code. No markdown.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        return clean_code_block(response.text)


    def run_query(self, cypher):
        """Executes the Cypher and returns results"""
        with self.driver.session() as session:
            try:
                result = session.run(cypher)
                # Convert to list of dicts
                data = [dict(record) for record in result]
                return data
            except Exception as e:
                return f"Cypher Error: {e}"

    def synthesize_answer(self, question, data):
        """Turns raw DB rows into a Human Answer"""
        prompt = f"""
        You are a Business Intelligence Analyst.
        
        User Question: "{question}"
        
        Database Data:
        {json.dumps(data, default=str)[:10000]}
        
        Task:
        Synthesize a direct, insight-rich answer based ONLY on the data above.
        If the data is empty, say "I couldn't find relevant data in the graph."
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt
        )
        return response.text

# --- MAIN LOOP ---
def main():
    oracle = ProfitOracle()
    
    print("\n💬 The Oracle is listening... (Type 'exit' to quit)\n")
    
    while True:
        try:
            question = input("You: ")
            if question.lower() in ['exit', 'quit']:
                break
                
            # 1. Generate Cypher
            print("   Thinking...", end="\r")
            cypher = oracle.generate_cypher(question)
            # print(f"   [Debug] Cypher: {cypher}") # Uncomment to see the raw query
            
            # 2. Execute
            data = oracle.run_query(cypher)
            
            # 3. Synthesize
            if isinstance(data, str) and "Error" in data:
                print(f"   ⚠️ {data}")
            else:
                answer = oracle.synthesize_answer(question, data)
                print(f"\n🔮 Oracle: {answer}\n")
                
        except KeyboardInterrupt:
            break
            
    oracle.close()
    print("\n👋 Oracle disconnected.")

if __name__ == "__main__":
    main()

