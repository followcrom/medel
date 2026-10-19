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
MODELS=("llama" "gemini" "qwen" "gpt" "grok" "bedrock" "deepseek" "mistral")
# MODELS=("llama" "claude" "gemini" "qwen" "gpt" "grok" "bedrock" "deepseek" "mistral")

# Randomly select a model
# SELECTED_MODEL=${MODELS[$RANDOM % ${#MODELS[@]}]}

# Select a specific model every time
SELECTED_MODEL="mistral"

# Every run is wrapped in a START banner and a single RESULT line, so runs
# are easy to tell apart and `grep RESULT medel_analysis.log` gives a history.
RULE="================================================================"
START_TS=$(date +%s)

log_start() {
    {
        echo "$RULE"
        echo "START  $(date '+%Y-%m-%d %H:%M:%S %Z')  model=$SELECTED_MODEL"
        echo "$RULE"
    } >> "$LOG_FILE"
}

# log_end <exit code> [reason]
log_end() {
    local secs=$(( $(date +%s) - START_TS ))
    {
        echo "----------------------------------------------------------------"
        if [ "$1" -eq 0 ]; then
            echo "RESULT: SUCCESS  $(date '+%Y-%m-%d %H:%M:%S %Z')  model=$SELECTED_MODEL  (${secs}s)"
        else
            echo "RESULT: FAILED (exit $1)  $(date '+%Y-%m-%d %H:%M:%S %Z')  model=$SELECTED_MODEL  (${secs}s)${2:+  - $2}"
        fi
        echo ""
        echo ""
    } >> "$LOG_FILE"
}

log_start

# Change to the appropriate directory
cd "$SCRIPT_DIR" || {
    log_end 1 "failed to cd into $SCRIPT_DIR"
    exit 1
}

# Check if the virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    log_end 1 "virtual environment not found at $VENV_PATH"
    exit 1
fi

# Run Python script and capture output
python_script_output=$("$VENV_PATH/bin/python" "$SCRIPT_PATH" --model "$SELECTED_MODEL" 2>&1)
python_exit_code=$?

# Log the output
echo "$python_script_output" >> "$LOG_FILE"

# Handle success/failure
if [ $python_exit_code -eq 0 ]; then
    log_end 0
else
    # Send failure email, if this environment has a mail command (dobox does; local dev usually doesn't)
    if command -v mail >/dev/null 2>&1; then
        email_note="failure email sent"
        cat << EOF | mail -s "Medel Error" noreply@followcrom.com
$(date) - Medel Error Notification

Today's Message from a Model failed to complete. The model selected was $SELECTED_MODEL.

Exit Code: $python_exit_code

Output:
$python_script_output
EOF
    else
        email_note="no mail command, failure email skipped"
    fi

    log_end $python_exit_code "$email_note"
    exit $python_exit_code
fi
