#!/bin/bash

# start timer
START_TIME=$(date +%s)

# parse OUT_FOLDER from config.py
OUT_FOLDER=$(python3 -c "import config; print(config.OUT_FOLDER)")

# get today's date and create output directory
DATE=$(date "+%Y-%m-%d")
OUTPUT_DIR="$OUT_FOLDER/$DATE/logs"
mkdir -p "$OUTPUT_DIR"

# run AMT Longterm Questions
echo "Running longtermquestions.py..."
python3 -u longtermquestions.py > "$OUTPUT_DIR/longtermquestions_$DATE.log" 2>&1

# run AMT News Questions
echo "Running newsquestions.py..."
python3 -u newsquestions.py > "$OUTPUT_DIR/newsquestions_$DATE.log" 2>&1

# run AMT Fact Check Questions
echo "Running factcheckquestions.py..."
python3 -u factcheckquestions.py > "$OUTPUT_DIR/factcheckquestions_$DATE.log" 2>&1

# end timer and calculate elapsed time
END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))

echo "Done! Logs saved to output folders."
echo "Completed in $(printf '%02dh %02dm %02ds\n' $((ELAPSED_TIME/3600)) $(( (ELAPSED_TIME%3600)/60 )) $((ELAPSED_TIME%60)))"