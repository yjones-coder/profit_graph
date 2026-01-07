#!/bin/bash

# Usage: ./run_pipeline.sh "[https://youtube.com/](https://youtube.com/)..."

URL=$1

if [ -z "$URL" ]; then
    echo "Usage: ./run_pipeline.sh <YOUTUBE_URL>"
    exit 1
fi

echo "🎬 PHASE 1: Downloading Transcript..."
# Run python script and capture the line starting with OUTPUT_FILE::
OUTPUT_LINE=$(python yt_transcript.py "$URL" | grep "OUTPUT_FILE::")

# Extract the actual path (remove the prefix)
TRANSCRIPT_FILE=${OUTPUT_LINE#OUTPUT_FILE::}

if [ -z "$TRANSCRIPT_FILE" ]; then
    echo "❌ Failed to get transcript file path."
    exit 1
fi

echo "📄 Transcript saved at: $TRANSCRIPT_FILE"

echo "🧠 PHASE 2: Building Knowledge Graph (Gemini 2.5 + Sonar + Neo4j)..."
python knowledge_processor.py "$TRANSCRIPT_FILE"

echo "✅ Pipeline Complete!"
echo "💡 To generate a plan, run: python resource_factory.py plan 'ToolName'"



