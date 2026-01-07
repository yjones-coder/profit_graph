import sys
import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
import profit_config as cfg  # Links to your central config

# Import Transcript API
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("❌ ERROR: youtube-transcript-api not installed!")
    print("👉 Run: pip install youtube-transcript-api")
    sys.exit(1)

class VideoIngestor:
    def __init__(self, gdrive_folder="AI_News_Brain/Raw_Transcripts"):
        # 1. TARGET: Use the Factory's defined transcript folder
        self.local_output_dir = Path(cfg.TRANSCRIPTS_DIR)
        self.local_output_dir.mkdir(parents=True, exist_ok=True)
        self.gdrive_folder = gdrive_folder

    def extract_video_id(self, url_or_id):
        # Robust regex to catch standard links, shortened links, and embeds
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'^([a-zA-Z0-9_-]{11})$'
        ]
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match: return match.group(1)
        return None

    def fetch_transcript(self, video_id, languages=['en']):
        print(f"📥 Fetching transcript for: {video_id}")
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Priority: Manual English -> Auto-Generated English
            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                except:
                    # Fallback: Just get whatever is available and translate? 
                    # For now, let's grab the first available if EN fails
                    transcript = transcript_list.find_transcript(languages)

            fetched = transcript.fetch()
            # Combine lines into one block of text
            return " ".join([item['text'] for item in fetched])
            
        except Exception as e:
            print(f"❌ Transcription Failed: {str(e)}")
            return None

    def save_for_factory(self, video_id, text, custom_name=None):
        # 2. FORMAT: Create the strict JSON structure the Factory demands
        data = {
            "video_id": video_id,
            "transcript_text": text,
            "ingested_at": datetime.now().isoformat()
        }

        # Filename strategy: Use custom name if provided, else Video ID
        base_name = custom_name if custom_name else video_id
        # sanitize filename just in case
        base_name = re.sub(r'[\\/*?:"<>|]', "", base_name)
        
        filename = f"{base_name}_transcript.json"
        filepath = self.local_output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        print(f"✅ JSON Saved for Factory: {filepath}")
        return filepath

    def backup_to_gdrive(self, local_filepath):
        # 3. BACKUP: Silent background backup using your Rclone config
        # We check if rclone is actually installed first
        if subprocess.call("type rclone", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            print("⚠️  Rclone not found. Skipping cloud backup.")
            return

        print(f"☁️  Backing up to GDrive ({self.gdrive_folder})...")
        cmd = [
            "rclone", "copy", str(local_filepath),
            f"manus_google_drive:{self.gdrive_folder}/",
            "--config", "/data/data/com.termux/files/home/.config/rclone/rclone.conf"
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"   (Backup Successful)")
        except Exception as e:
            print(f"   (Backup Failed: {e})")

    def process_video(self, url_or_id, custom_name=None):
        video_id = self.extract_video_id(url_or_id)
        if not video_id:
            print(f"❌ Invalid URL/ID: {url_or_id}")
            return False

        text = self.fetch_transcript(video_id)
        if not text: 
            return False

        # Save & Backup
        json_file = self.save_for_factory(video_id, text, custom_name)
        self.backup_to_gdrive(json_file)
        
        return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest_video.py <url_or_file> [custom_name]")
        sys.exit(1)

    target = sys.argv[1]
    # Check for optional custom name argument
    custom_name = sys.argv[2] if len(sys.argv) > 2 else None

    ingestor = VideoIngestor()

    # Handle Batch File (List of URLs)
    if os.path.isfile(target):
        print(f"📄 Reading batch queue: {target}")
        with open(target, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        print(f"Found {len(urls)} videos in queue.")
        for i, url in enumerate(urls, 1):
            print(f"\n--- Processing {i}/{len(urls)} ---")
            ingestor.process_video(url)
    else:
        # Handle Single URL
        ingestor.process_video(target, custom_name)

if __name__ == "__main__":
    main()
