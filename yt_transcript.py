#!/usr/bin/env python
import sys
import os
import json
import re
try:
    import yt_dlp
except ImportError:
    print("❌ Critical Error: Please run 'pip install yt-dlp'")
    sys.exit(1)

# --- CONFIGURATION ---
STORAGE_DIR = os.path.expanduser("~/storage/downloads/yt_transcripts/")
TEMP_DIR = os.path.expanduser("~/tmp/profitgraph_temp")

def clean_vtt_text(text):
    """
    Strips WebVTT formatting (timestamps, tags) to leave pure speech.
    """
    lines = text.split('\n')
    cleaned = []
    seen = set()
    
    for line in lines:
        # Skip headers, timestamps, and empty lines
        if line.startswith('WEBVTT') or '-->' in line or not line.strip():
            continue
        if line.startswith('Kind:') or line.startswith('Language:'):
            continue
            
        # Remove HTML-like tags (e.g. <c.colorE5E5E5>)
        clean_line = re.sub(r'<[^>]+>', '', line).strip()
        
        # Simple deduplication (captions often repeat lines)
        if clean_line and clean_line not in seen:
            cleaned.append(clean_line)
            seen.add(clean_line)
            
    return " ".join(cleaned)

def save_json(video_id, text):
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)
        
    filename = f"{video_id}_transcript.json"
    filepath = os.path.join(STORAGE_DIR, filename)
    
    payload = {
        "video_id": video_id,
        "transcript_text": text,
        "source_engine": "yt-dlp (Text Only)"
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Transcript saved: {filepath}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 yt_transcript.py <youtube_url>")
        sys.exit(1)

    url = sys.argv[1]
    
    # Configure yt-dlp for TEXT ONLY (No Video)
    ydl_opts = {
        'skip_download': True,      # <--- CRITICAL: Downloads NO video
        'writeautomaticsub': True,  # Fetch auto-generated subs
        'subtitleslangs': ['en'],   # English only
        'outtmpl': f'{TEMP_DIR}/%(id)s',
        'quiet': True,
        'no_warnings': True
    }

    print(f"📥 Connecting to YouTube (Metadata Only)...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            
            # Locate the .vtt file (yt-dlp names it video_id.en.vtt)
            expected_path = os.path.join(TEMP_DIR, f"{video_id}.en.vtt")
            
            if not os.path.exists(expected_path):
                print("❌ Error: No English subtitles found for this video.")
                sys.exit(1)
            
            # Parse and Clean
            with open(expected_path, 'r', encoding='utf-8') as f:
                raw_vtt = f.read()
            
            clean_text = clean_vtt_text(raw_vtt)
            save_json(video_id, clean_text)
            
            # Cleanup temp file
            os.remove(expected_path)

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()

