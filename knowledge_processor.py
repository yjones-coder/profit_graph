#!/usr/bin/env python
import os
import json
import sys
import datetime
import requests
from google import genai
from google.genai import types
from neo4j import GraphDatabase
import time

# --- TELEMETRY ---
class Telemetry:
    LOG_FILE = os.path.join(os.path.expanduser("~/storage/downloads/yt_transcripts/"), "telemetry.jsonl")
    
    @staticmethod
    def log(run_id, agent, prompt_version, input_snippet, output_preview, duration):
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "run_id": run_id,
            "agent": agent,
            "prompt_version": prompt_version,
            "input_preview": str(input_snippet)[:50],
            "output_preview": str(output_preview)[:50],
            "duration_sec": round(duration, 2)
        }
        try:
            with open(Telemetry.LOG_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"⚠️ Telemetry Error: {e}")

# --- CONFIGURATION ---
STORAGE_DIR = os.path.expanduser("~/storage/downloads/yt_transcripts/")
LOG_DIR = os.path.join(STORAGE_DIR, "logs") 
HISTORY_FILE = os.path.join(STORAGE_DIR, "processed_history.log")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PERPLEXITY_API_KEY = os.environ.get("SONAR_API_KEY")

# Neo4j Config
NEO4J_URI = os.environ.get("NEO4J_URI")
NEO4J_USER = os.environ.get("NEO4J_USERNAME")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD")

if not GEMINI_API_KEY or not PERPLEXITY_API_KEY:
    print("❌ Error: Missing API Keys.")
    sys.exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

# --- LOGGING SYSTEM ---
def save_debug_log(video_id, step_name, content):
    """Saves raw agent outputs to a timestamped log file for debugging."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{video_id}_debug_log.txt"
    filepath = os.path.join(LOG_DIR, filename)
    
    with open(filepath, 'a') as f:
        f.write(f"\n[{timestamp}] === {step_name} ===\n")
        if isinstance(content, (dict, list)):
            f.write(json.dumps(content, indent=2))
        else:
            f.write(str(content))
        f.write("\n" + "="*40 + "\n")

# --- HISTORY TRACKING ---
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def mark_as_complete(video_id):
    with open(HISTORY_FILE, 'a') as f:
        f.write(f"{video_id}\n")

# --- UTILS ---
def clean_json_text(text):
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

def load_transcript(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data.get('transcript_text', '')
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return None

def get_available_transcripts():
    history = load_history()
    available = []
    
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)

    files = [f for f in os.listdir(STORAGE_DIR) if f.endswith("_transcript.json")]
    
    for f in files:
        video_id = f.split("_")[0]
        if video_id not in history:
            full_path = os.path.join(STORAGE_DIR, f)
            available.append((video_id, full_path))
    
    return available

# --- AGENT 1: THE STRATEGIST (With Typo Correction) ---
def identify_gaps(transcript_text, video_id):
    print("🧠 (Strategist) Analyzing transcript for critical risks...")
    
    prompt = f"""
    You are a cynical, high-level CTO. Review this transcript for a technical business.
    
    Your Goal: Identify 3-5 "Critical Failure Points" or "Implementation Blockers."
    
    CRITICAL INSTRUCTION - AUDIO CLEANUP:
    The transcript is from YouTube auto-captions and may have phonetic errors.
    - If you see "JLM", it likely means "GLM" (General Language Model).
    - If you see "Lama", it likely means "Llama".
    - If you see "OpenAI Opus", CORRECT IT to "Claude 3 Opus" or "GPT-4o" based on context.
    - USE THE CORRECT TECHNICAL TERMS in your search queries.

    Focus on:
    1. UNDOCUMENTED COSTS (API pricing, tokens).
    2. PLATFORM RISK (Reliance on specific providers).
    3. TECHNICAL LIMITS (Context window, latency).
    
    Return JSON:
    {{
        "research_questions": [
            "Query 1",
            "Query 2"
        ]
    }}

    Transcript:
    {transcript_text[:15000]}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        data = json.loads(clean_json_text(response.text))
        save_debug_log(video_id, "STRATEGIST_OUTPUT", data)
        return data
    except Exception as e:
        print(f"⚠️ Strategist Error: {e}")
        return {"research_questions": []}

# --- AGENT 2: THE SCOUT ---
def execute_research_plan(plan, video_id):
    if isinstance(plan, list): queries = plan
    elif isinstance(plan, dict):
        queries = plan.get("research_questions", [])
        if not queries and "questions" in plan: queries = plan["questions"]
    else: return ""
        
    if not queries: return ""

    print(f"🕵️ (Scout) Executing research plan ({len(queries)} queries)...")
    
    research_summary = []
    url = "https://api.perplexity.ai/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }

    for q in queries:
        query_text = q if isinstance(q, str) else str(q)
        print(f"   🔎 Searching: {query_text[:40]}...")
        
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "You are a concise technical researcher."},
                {"role": "user", "content": query_text}
            ]
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                answer = response.json()['choices'][0]['message']['content']
                research_summary.append(f"Q: {query_text}\nA: {answer}\n")
            else:
                print(f"   ⚠️ API Error {response.status_code}")
                answer = "API Error"
        except Exception as e:
            print(f"   ⚠️ Network Error: {e}")
            answer = str(e)

    full_research = "\n---\n".join(research_summary)
    save_debug_log(video_id, "SCOUT_FINDINGS", full_research)
    return full_research

# --- AGENT 3: THE ARCHITECT (Entity Extraction Mode) ---
def synthesize_strategy(transcript, research, video_id):
    start_time = time.time()
    print("🏗️ (Architect) Synthesizing Strategy & Extracting Entities...")
    
    prompt = f"""
    Context: ProfitGraph Business Strategy.
    Input 1: Transcript (User Content)
    {transcript[:5000]}...
    Input 2: Verified Research (External Validation)
    {research}
    
    Task:
    1. Create a "Profit Synergy Brief" (Markdown).
    2. Extract KEY ENTITIES as a structured list:
       - Models (LLMs like GPT-4, Claude, Llama)
       - Interfaces (IDEs, SaaS, wrappers like Cursor, Whisper Flow)
       - Frameworks (LangChain, OMI, Supabase)
       - Risks (Vendor lock-in, Costs)
       - Risks (Business, Tech, Vendor)
       - Actions (Implementation steps)
    3. Generate a SMART FILENAME (snake_case).
    
    Return JSON:
    {{
        "filename": "smart_name.md",
        "content": "# Markdown Report...",
        "marketing": {{
            "viral_tweet": "280 char hook...",
            "linkedin": "Bullet points..."
        }},
        "entities": [
            {{"type": "Tool", "name": "Supabase", "detail": "Database"}},
            {{"type": "Risk", "name": "API Cost", "detail": "High at scale"}}
        ]
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        text_response = clean_json_text(response.text)
        
        # Robust JSON Parsing
        try:
            _d = json.loads(text_response)
            data = _d[0] if isinstance(_d, list) else _d
            
            smart_name = data.get("filename", "strategy.md")
            content = data.get("content", "")
            marketing = data.get("marketing", {})
            if marketing:
                content += "\n\n## 🚀 Marketing Assets\n**🐦 Viral Tweet:** " + marketing.get("viral_tweet", "") + "\n\n**💼 LinkedIn:**\n" + marketing.get("linkedin", "")
            entities = data.get("entities", [])
            final_filename = f"{video_id}_{smart_name}"
        except:
            print("⚠️ JSON Parsing failed. Using fallback.")
            content = text_response
            entities = []
            final_filename = f"{video_id}_strategy_fallback.md"

        # Save File
        filepath = os.path.join(STORAGE_DIR, final_filename)
        with open(filepath, 'w') as f:
            f.write(content)
            
        print(f"✅ Strategy Brief Saved: {final_filename}")
        
        # Telemetry Log
        Telemetry.log(video_id, "Architect", "Entity_Extractor_v1", research[:50], content[:50], time.time() - start_time)
        save_debug_log(video_id, "ARCHITECT_OUTPUT", data if 'data' in locals() else content)
        
        return content, entities

    except Exception as e:
        print(f"❌ Architect Error: {e}")
        return None, []

# --- NEO4J SYNC (High Fidelity) ---
def sync_to_neo4j(video_id, strategy_text, research_text, entities=[]):
    if not NEO4J_URI or not NEO4J_PASSWORD:
        return

    print(f"🌐 Syncing to Neo4j ({len(entities)} Entities)...")
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        # 1. Base Strategy Node
        query_base = """
        MERGE (v:Video {id: $vid})
        SET v.last_processed = datetime()
        MERGE (s:Strategy {id: $vid + "_strat"})
        SET s.content = $strategy
        MERGE (r:Research {id: $vid + "_res"})
        SET r.content = $research
        MERGE (v)-[:YIELDS_STRATEGY]->(s)
        MERGE (s)-[:BASED_ON_RESEARCH]->(r)
        """
        
        # 2. Entity Nodes (Tools, Risks, etc.)
        query_entities = """
        MATCH (s:Strategy {id: $vid + "_strat"})
        UNWIND $batch as item
        MERGE (e:Entity {name: item.name})
        SET e.type = item.type
        MERGE (s)-[:MENTIONS {detail: item.detail}]->(e)
        """
        
        with driver.session() as session:
            session.run(query_base, vid=video_id, strategy=strategy_text, research=research_text)
            
            # Inject Entities
            valid_entities = [e for e in entities if 'name' in e and 'type' in e]
            if valid_entities:
                session.run(query_entities, vid=video_id, batch=valid_entities)
                
        print("✅ Graph Updated Successfully!")
    except Exception as e:
        print(f"❌ Neo4j Error: {e}")
    finally:
        if driver: driver.close()

# --- MAIN FLOW ---
def run_pipeline(filepath):
    filename = os.path.basename(filepath)
    video_id = filename.split('_')[0]
    
    print(f"\n▶️ PROCESSING: {video_id}")
    
    # 1. Load
    transcript_text = load_transcript(filepath)
    if not transcript_text: return
        
    # 2. Strategist
    research_plan = identify_gaps(transcript_text, video_id)
    
    # 3. Scout
    research_data = execute_research_plan(research_plan, video_id)
    
    # 4. Architect (Returns Tuple now)
    strategy_text, entities = synthesize_strategy(transcript_text, research_data, video_id)
    
    # 5. Graph Sync (Passes Entities now)
    if strategy_text:
        sync_to_neo4j(video_id, strategy_text, research_data, entities)
        mark_as_complete(video_id)

def main():
    if len(sys.argv) > 1:
        run_pipeline(sys.argv[1])
        return

    print("\n📂 ProfitGraph: Select a Transcript to Process")
    print("---------------------------------------------")
    
    available = get_available_transcripts()
    
    if not available:
        print("✅ No new transcripts found.")
        return

    for i, (vid, path) in enumerate(available):
        print(f"[{i+1}] {vid} ({os.path.basename(path)})")
    
    try:
        choice = input("\nEnter number to process (or 'q' to quit): ")
        if choice.lower() == 'q': return
            
        idx = int(choice) - 1
        if 0 <= idx < len(available):
            run_pipeline(available[idx][1])
            print("\n🎉 Done.")
        else:
            print("❌ Invalid selection.")
    except ValueError:
        print("❌ Invalid input.")

if __name__ == "__main__":
    main()

