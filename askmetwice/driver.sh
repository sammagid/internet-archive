#!/bin/bash

# parse OUT_FOLDER from config.py
OUT_FOLDER=$(python3 -c "import config; print(config.OUT_FOLDER)")

# get today's date and create output directory
DATE=$(date '+%Y-%m-%d')
OUTPUT_DIR="$OUT_FOLDER/$DATE/logs"
mkdir -p "$OUTPUT_DIR"

# run newsquestions.py
echo "Running newsquestions.py..."
python3 -u newsquestions.py >> "$OUTPUT_DIR/newsquestions_$DATE.log" 2>&1

# run longtermquestions.py
echo "Running longtermquestions.py..."
python3 -u longtermquestions.py >> "$OUTPUT_DIR/longtermquestions_$DATE.log" 2>&1

echo "Done! Logs saved to output folders."