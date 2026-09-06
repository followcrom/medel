#!/bin/bash

# I'm using a Systemd Timer to run this script at a random time each day
# See Option 1 in the README to run this script from cron

# Resolve the directory this script lives in, so it works unchanged on dobox
# (/var/www/domdom) and locally (wherever the medel repo is checked out).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SCRIPT_PATH="$SCRIPT_DIR/message_model.py"

# dobox keeps its venv alongside the script; locally it lives in the sibling
# swill project instead.
if [ -d "$SCRIPT_DIR/domdom_venv" ]; then
    VENV_PATH="$SCRIPT_DIR/domdom_venv"
    LOG_FILE="$SCRIPT_DIR/medel_analysis.log"
else
    VENV_PATH="$HOME/projects/swill/swill_venv"
    LOG_FILE="$SCRIPT_DIR/logs/medel_analysis.log"
    mkdir -p "$SCRIPT_DIR/logs"
fi

# Define array of available analyzers
MODELS=("gemini" "qwen" "gpt" "grok" "bedrock" "deepseek")
# MODELS=("llama" "claude" "gemini" "qwen" "gpt" "grok" "bedrock" "deepseek" "mistral")

# Randomly select a model
SELECTED_MODEL=${MODELS[$RANDOM % ${#MODELS[@]}]}

# Change to the appropriate directory
cd "$SCRIPT_DIR" || {
    echo "$(date) - Failed to cd into $SCRIPT_DIR" >> "$LOG_FILE"
    exit 1
}

# Check if the virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "$(date) - Virtual environment not found at $VENV_PATH" >> "$LOG_FILE"
    exit 1
fi

# Log start
{
    echo "$(date)"
    echo "Generating a message from $SELECTED_MODEL."
    echo "Running Python script..."
    echo "Python script output:"
} >> "$LOG_FILE"

# Run Python script and capture output
python_script_output=$("$VENV_PATH/bin/python" "$SCRIPT_PATH" --model "$SELECTED_MODEL" 2>&1)
python_exit_code=$?

# Log the output
echo "$python_script_output" >> "$LOG_FILE"

# Handle success/failure
if [ $python_exit_code -eq 0 ]; then
    echo "Job complete!" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
else
    {
        echo "Python script failed with exit code $python_exit_code"
        echo "Output: $python_script_output"
    } >> "$LOG_FILE"

    # Send failure email, if this environment has a mail command (dobox does; local dev usually doesn't)
    if command -v mail >/dev/null 2>&1; then
        echo "Email sent regarding Python script failure." >> "$LOG_FILE"
        cat << EOF | mail -s "Medel Error" noreply@followcrom.com
$(date) - Medel Error Notification

Today's Message from a Model failed to complete. The model selected was $SELECTED_MODEL.

Exit Code: $python_exit_code

Output:
$python_script_output
EOF
    else
        echo "No mail command available - skipping failure email." >> "$LOG_FILE"
    fi

    exit $python_exit_code
fi