# 💌 Message from a Model 📨

🖥️ Run in `swilly` 🕹️

---

`model_message.py` generates a message from an LLM and sends it as a push notification to the **RanDOM WisDOM** app. It then logs the message to DynamoDB.

## 🕓 Get the Latest Models 🧠

### 🤖 llm

👉 [swill's llm documentation](https://llm.datasette.io/en/stable/usage.html)

Listing installed plugins:

```bash
llm plugins

llm plugins --all
```

Updating installed plugins:

```bash
llm install -U llm-gemini

llm install -U llm-openai-plugin
```

Installing a plugin:

```bash
llm uninstall llm-gemini # for example

llm uninstall llm-gemini -y # -y flag skips asking for confirmation

llm install llm-gemini

llm mistral refresh

# OR:

llm install llm-grok -U
```

List all available models:

```bash
llm models

llm openai models
```

Set a default model:

```bash
llm models default

llm models default gpt-4o
```

Set model alias:

```bash
llm alias
llm aliases list --json

# llm aliases set <alias> <model-id>
llm aliases set mini gpt-4o-mini
```

Get the path to the keys directory:

```bash
dirname "$(llm keys path)"
```

## ֎ OpenAI Models 🧿
 
Specific model usage can be tied to API keys. Allowed models can be set on a project level. Go to `Project -> Limits` on the [OpenAI dashboard](https://platform.openai.com/settings/proj_WJ4UVWtOs47BaFcQUjpLuk82) and access the Model usage section.

Alternatively, you can use the OpenAI API to list available models for a given API key:

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer <API_KEY>"
```

## 🌥️ AWS Accounts ☁️

To see which IAM user is currently logged in, run the following command:

```bash
aws sts get-caller-identity
```

### 📲 Expo

The message is then sent as a push notification to the **RanDOM WisDOM** app.

### 📝 DynamoDB

The _date, model_ and _message_ are logged to the `MedelLogs` DynamoDB table.

👉 [MedelLogs](https://eu-west-2.console.aws.amazon.com/dynamodbv2/home?region=eu-west-2#table?name=MedelLogs)

---

## Running the job ᯓ🏃🏻‍♀️‍➡️

`mess_model.sh` does the following:

- activates the virtual environment
- selects a model
- runs `mess_model.py` with the selected model
- logs the message to DynamoDB

### 1️⃣ Option 1: Cron Job 🕓

I could use a Cron Job with a random delay.

```bash
# Mess Model
0 0 * * * sleep $((RANDOM % 86400)) && /bin/bash /var/www/domdom/mess_model.sh
```

Explanation:

- `0 0 * * *`: Runs the cron job daily at midnight.

- `sleep $((RANDOM % 86400))`: Pauses the job for a random duration between 0 to 86400 seconds (24 hours).

<br>

I could add the sleep delay to the `mess_model.sh` script.

```bash
#!/bin/bash

# Only sleep if running from cron (no terminal)
if [ ! -t 0 ]; then
    # Random delay (0-86400 seconds = 0-24 hours)
    sleep $((RANDOM % 86400))
fi
```

or

```bash
#!/bin/bash

# Skip delay if --no-delay parameter is passed
if [[ "$1" != "--no-delay" ]]; then
    sleep $((RANDOM % 86400))
fi
```

Then I could run the script with:

```bash
./mess_model.sh --no-delay
```

### Resource Usage

#### Sleep in cron:

- 2 processes running: bash -c wrapper + sleep command
- Memory: ~2-4MB for both processes combined
- CPU: Minimal, but 2 processes in process table

#### Sleep in script:

- 1 process running: Just the script itself calling sleep()
- Memory: ~1-2MB for single process
- CPU: Minimal, single process

<br>

### 2️⃣ Option 2: Systemd Timer ⏱️

However, instead I'll use a Systemd Timer. Systemd timers are modern and more robust. A timer unit can randomize execution time within a given window.

#### 1, Create a Service File

Save this as `/etc/systemd/system/medel.service`

```ini
[Unit]
Description=Run Medel Shell Script

[Service]
ExecStart=/bin/bash /var/www/domdom/mess_model.sh
```

#### 2, Create a Timer File

Save this as `/etc/systemd/system/medel.timer`

```ini
[Unit]
Description=Generate a Random Time to Run Medel

[Timer]
OnCalendar=*-*-* 00:00:00
RandomizedDelaySec=86400
Persistent=true

[Install]
WantedBy=timers.target
```

Explanation:

- `OnCalendar=*-*-* 00:00:00`: Schedules the job to run daily starting from midnight.

- `RandomizedDelaySec=86400`: Adds a randomized delay of up to 86400 seconds (24 hours).

- `Persistent=true`: Ensures that if the system is down during the scheduled time (e.g., midnight), the job will run as soon as the system comes back up, respecting the random delay.


#### 3, Enable and Start the Timer

```bash
systemctl enable medel.timer
systemctl start medel.timer
```

#### 4, Verification

Check when the job is next scheduled to run using the following command:

```bash
systemctl list-timers | grep medel

systemctl list-timers --all
```

Output:
```bash
| NEXT                        | LEFT          | LAST                        | PASSED         | UNIT          | ACTIVATES |
| Tue 2025-01-28 16:47:51 GMT | 19h left      | Mon 2025-01-27 08:30:07 GMT | 12h ago        | medel.timer   | medel.service |
```

#### 5, Debugging Steps

Check Journal logs:

```bash
journalctl -u medel.service

journalctl -u medel.timer
```

Check Journal logs for errors:

```bash
journalctl -u medel.service -p err
```

---

<br>

## Logging to DynamoDB 📊

The application logs messages to a DynamoDB table named `MedelLogs2`. Each log entry includes a unique ID, the date, the model used, and the generated message.

#### Counter Item

There is also a Counter Item. This is a Live Record. ⚠️

Think of the counter item {"id": {"N": "0"}, "current_id": {"N": "1000"}} as the live scoreboard for your messages.

Your `get_next_id` function actively interacts with this specific item every single time it's called:

- It finds the item where `id` is 0.
- It reads the value of the `current_id` attribute from that item.
- It adds 1 to that value.
- It saves the new value back to the `current_id` attribute on that same `id`: 0 item.

---

<br>

## 🤔 Issues 🛠️

1, An issue with the models on the **dobox** not being found until you set the API key, using `llm keys set`. 🤔

- On installing DeepSeek models on the **dobox** (in the domdom_venv) they were not found until I added the API key. This is not the case locally.

_However_, most of the keys (apart from grok) are set in the local `keys.json` file, so honestly not sure here.

2, `model_message.py` was generating an _API key not found_ error when calling the groq models on the **dobox** BUT NOT locally. I had to `llm keys set groq` in the **dobox** (in the domdom_venv) to get the groq models to work. (The groq key is set locally, but that was not the issue as I'm calling the API keys from the `.env` file.)

I knew that `notifications_team.py` was successfully calling the groq models from the **dobox**, and the code was almost identical. So I compared the two files and found the issue. 😎👌🔥

This line was different in the def that calls the llm...

In `model_message.py`:

```python
model.api_key = self.model_config.api_key
```

In `notifications_team.py`: 

```python
model.key = self.model_config.api_key
```

_However_, why did it initally work locally and not on the **dobox**, even with the different code? 🤔 Am assuming it's to do with the keys being hardcoded locally, but not on the **dobox**. 😅

```bash
llm keys path

# Output
/home/followcrom/.config/io.datasette.llm/keys.json
```

<br>

## 📅 Commit Activity 🕹️

![GitHub last commit](https://img.shields.io/github/last-commit/followcrom/medel)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/followcrom/medel)
![GitHub repo size](https://img.shields.io/github/repo-size/followcrom/medel)

## ✍ Authors 

🌍 followCrom: [followcrom.com](https://followcrom.com/index.html) 🌐

📫 followCrom: [get in touch](https://followcrom.com/contact/contact.php) 👋

[![Static Badge](https://img.shields.io/badge/followcrom-online-blue)](http://followcrom.com)