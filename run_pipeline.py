#!/usr/bin/env python
import subprocess
import sys
import os
import re
from urllib.parse import urlparse, parse_qs

# --- CONFIGURATION ---
STORAGE_DIR = os.path.expanduser("~/storage/downloads/yt_transcripts/")

# --- UTILS ---
def extract_video_id(url_or_id):
    """
    Same logic as ingestion script to predict the filename.
    """
    if len(url_or_id) == 11 and "youtube" not in url_or_id:
        return url_or_id
    
    parsed = urlparse(url_or_id)
    if parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch':
            p = parse_qs(parsed.query)
            return p.get('v', [None])[0]
        if parsed.path[:7] == '/embed/':
            return parsed.path.split('/')[2]
        if parsed.path[:3] == '/v/':
            return parsed.path.split('/')[2]
            
    # Fallback regex
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url_or_id)
    if match:
        return match.group(1)
    return None

def run_command(command_list):
    """
    Runs a shell command and streams output in real-time.
    Returns True if successful (exit code 0), False otherwise.
    """
    print(f"\n🚀 EXEC: {' '.join(command_list)}")
    print("-" * 40)
    
    try:
        # stream output to console
        process = subprocess.Popen(
            command_list, 
            stdout=sys.stdout, 
            stderr=sys.stderr,
            text=True
        )
        process.wait()
        
        if process.returncode == 0:
            return True
        else:
            print(f"❌ Process failed with exit code {process.returncode}")
            return False
    except Exception as e:
        print(f"❌ Execution Error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_pipeline.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    video_id = extract_video_id(url)
    
    if not video_id:
        print("❌ Error: Invalid YouTube URL.")
        sys.exit(1)

    # 1. DEFINE PATHS
    expected_file = os.path.join(STORAGE_DIR, f"{video_id}_transcript.json")

    # 2. RUN INGESTION (yt_transcript.py)
    print(f"\n🔹 PHASE 1: INGESTION ({video_id})")
    success = run_command(["python3", "yt_transcript.py", url])
    
    if not success:
        print("🛑 Pipeline stopped due to Ingestion failure.")
        sys.exit(1)

    # Verify file actually exists
    if not os.path.exists(expected_file):
        print(f"🛑 Error: Ingestion finished but file not found: {expected_file}")
        sys.exit(1)

    # 3. RUN INTELLIGENCE (knowledge_processor.py)
    print(f"\n🔹 PHASE 2: INTELLIGENCE")
    success = run_command(["python3", "knowledge_processor.py", expected_file])
    
    if success:
        print("\n✅ PIPELINE SUCCESS.")
        print(f"   Strategy Brief: {expected_file.replace('.json', '_STRATEGY.md')}")
    else:
        print("\n⚠️ Pipeline finished with errors in Phase 2.")

if __name__ == "__main__":
    main()

