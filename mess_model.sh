#!/bin/bash

# Exit on error
set -e
trap 'echo "Message NOT sent" >> "$LOG_FILE"' ERR

# Absolute paths
VENV_PATH="/var/www/domdom/domdom_venv"
SCRIPT_PATH="/var/www/domdom/message_model.py"
LOG_FILE="/var/www/domdom/medel_analysis.log"
# ENV_FILE="/var/www/domdom/.env"

# Define array of available analyzers
MODELS=("llama3" "claude" "gemini" "mixtral" "openai")

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

# Activate virtual environment and run script
source "$VENV_PATH/bin/activate"
"$VENV_PATH/bin/python" "$SCRIPT_PATH" --model "$SELECTED_MODEL" >> "$LOG_FILE" 2>&1

# Output of the python script
python_script_output=$(python $SCRIPT_PATH 2>&1)

# log "Python script output: $python_script_output"

# Check if the script executed successfully
if [ $? -eq 0 ]; then
    log "Check your notifications for a message from $SELECTED_MODEL"
else
    log "Error occurred: $python_script_output"
fi
