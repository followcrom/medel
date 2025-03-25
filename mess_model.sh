#!/bin/bash

# Exit on error
set -e
trap 'log "Message NOT sent due to an error." ERR' ERR

# Absolute paths
VENV_PATH="/var/www/domdom/domdom_venv"
SCRIPT_PATH="/var/www/domdom/message_model.py"
LOG_FILE="/var/www/domdom/medel_analysis.log"

# Define array of available analyzers
MODELS=("llama3" "claude" "gemini" "o1" "openai" "grok" "bedrock" "deepseek" "mistral")

# Randomly select an analyzer
SELECTED_MODEL=${MODELS[$RANDOM % ${#MODELS[@]}]}

# Logging function
log() {
    echo "$(date): $1" >> "$LOG_FILE"
    echo >> "$LOG_FILE"
}

# Log start time and selected analyzer
log "Generating a message from $SELECTED_MODEL"

# Change to the appropriate directory
cd /var/www/domdom

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run Python script and capture output
python_script_output=$("$VENV_PATH/bin/python" "$SCRIPT_PATH" --model "$SELECTED_MODEL" 2>&1)
python_exit_code=$?

# Log the Python script's output
echo "$python_script_output" >> "$LOG_FILE"

# Check if the Python script executed successfully
if [ $python_exit_code -eq 0 ]; then
    log "Check your notifications for a message from $SELECTED_MODEL"
else
    log "Error occurred in Python script. See output above."
    exit $python_exit_code
fi
