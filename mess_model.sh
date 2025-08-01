#!/bin/bash

# Only sleep if running from cron (no terminal)
if [ ! -t 0 ]; then
    # Random delay (0-86400 seconds = 0-24 hours)
    sleep $((RANDOM % 86400))
fi

# Absolute paths
VENV_PATH="/var/www/domdom/domdom_venv"
SCRIPT_PATH="/var/www/domdom/message_model.py"
LOG_FILE="/var/www/domdom/medel_analysis.log"

# Define array of available analyzers
MODELS=("llama" "claude" "gemini" "qwen" "gpt" "grok" "bedrock" "deepseek" "mistral")

# Randomly select a model
SELECTED_MODEL=${MODELS[$RANDOM % ${#MODELS[@]}]}

# Change to the appropriate directory
cd /var/www/domdom || {
    echo "$(date) - Failed to cd into /var/www/domdom" >> "$LOG_FILE"
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
    echo "Generating a message from $SELECTED_MODEL model"
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
    echo "Cron job complete!" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
else
    {
        echo "Python script failed with exit code $python_exit_code"
        echo "Output: $python_script_output"
        echo "Email sent regarding Python script failure."
        echo ""
    } >> "$LOG_FILE"

    # Send failure email
    cat << EOF | mail -s "Medel Error" noreply@followcrom.com
$(date) - Medel Error Notification

Today's Message from a Model failed to complete. The model selected was $SELECTED_MODEL.

Exit Code: $python_exit_code

Output:
$python_script_output
EOF

    exit $python_exit_code
fi