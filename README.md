# 💌 Message from a Model 💋 📨

🖥️ Run in `swilly` 🕹️

---

`model_message.py` generates a message from an llm and sends it as a push notification to the **RanDOM WisDOM** app. It logs the message to DynamoDB.

### 🤖 llm

👉 [swill's llm usgae](https://llm.datasette.io/en/stable/usage.html)

Generates a message from one of the following:

`MODELS=("llama3" "claude" "gemini" "mixtral" "openai")`

### 📲 Expo

The message is then sent as a push notification to the **RanDOM WisDOM** app.

### 📝 DynamoDB

The _date, model and message_ are logged to the `MedelLogs` DynamoDB table.

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
systemctl list-timers --all
```

Output:
```bash
| NEXT                        | LEFT          | LAST          | PASSED       | UNIT            | ACTIVATES |
| Mon 2025-01-27 08:29:59 GMT | 21h left      | n/a           | n/a          | medel.timer     | medel.service |
```

---

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

---

## 🤔 Issues 🛠️

`model_message.py` was generating an _API key not found_ error when calling the groq models on the **dobox** BUT NOT locally. I had to `llm keys set groq` in the **dobox** (in the domdom_venv) to get the groq models to work. (The groq key is set locally, but that was not the issue as I'm calling the API keys from the `.env` file.)

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

## 📅 Commit Activity 🕹️

![GitHub last commit](https://img.shields.io/github/last-commit/followcrom/medel)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/followcrom/medel)

## ✍ Authors 

🌍 followCrom: [followcrom.com](https://followcrom.com/index.html) 🌐

📫 followCrom: [get in touch](https://followcrom.com/contact/contact.php) 📧

[![Static Badge](https://img.shields.io/badge/followcrom-online-blue)](http://followcrom.com)