#!/bin/bash

# Absolute paths
VENV_PATH="/var/www/domdom/domdom_venv"
SCRIPT_PATH="/var/www/domdom/message_model.py"
LOG_FILE="/var/www/domdom/medel_analysis.log"

# Define array of available analyzers
MODELS=("llama3" "claude" "gemini" "o1" "gpt4" "grok" "bedrock" "deepseek" "mistral")

# Randomly select an analyzer
SELECTED_MODEL=${MODELS[$RANDOM % ${#MODELS[@]}]}

# Logs
echo "$(date)" >> "$LOG_FILE"
echo "Generating a message from $SELECTED_MODEL model" >> "$LOG_FILE"
echo "Running Python script..." >> "$LOG_FILE"
echo "Python script output:" >> "$LOG_FILE"

# Change to the appropriate directory
cd /var/www/domdom

# Check if the virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "$(date) - Virtual environment not found at $VENV_PATH" >> "$LOG_FILE"
    exit 1
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run Python script and capture output
python_script_output=$("$VENV_PATH/bin/python" "$SCRIPT_PATH" --model "$SELECTED_MODEL" 2>&1)
python_exit_code=$?

# Log the Python script's output
echo "$python_script_output" >> "$LOG_FILE"

# Deactivate virtual environment
deactivate

# Check if the Python script executed successfully
if [ $python_exit_code -eq 0 ]; then
    echo "Cron job complete!" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
else
    echo "" >> "$LOG_FILE"
    echo "Python script failed with exit code $python_exit_code" >> "$LOG_FILE"
    echo "Output: $python_script_output" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    # Compose the email body with date and script output
    email_body="$(date) - Error: Python script failed to run.
Exit Code: $python_exit_code

Output:
$python_script_output"

    # Send the email
    echo "$email_body" | mail -s "Medel Error" followcrom@gmail.com

    # Log that the email was sent
    echo "$(date) - Notification email sent regarding Python script failure." >> "$LOG_FILE"

    exit $python_exit_code
fi
