# 💌 Message from a Model 📨

🖥️ Run in `swilly` 🕹️

---

`message_model.py` generates a message from an LLM and sends it as a push notification to the **RanDOM WisDOM** app. It then logs the message to DynamoDB. `mess_model.sh` picks a random model and runs it - locally or on **dobox**, it resolves its own paths automatically.

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

If `pip` starts backtracking through old versions (slow, high CPU), pin the exact version instead of a bare `-U`, e.g. `llm install -U "llm-anthropic==0.28"`.

Installing a plugin:

```bash
llm uninstall llm-gemini # for example

llm uninstall llm-gemini -y # -y flag skips asking for confirmation

llm install llm-gemini
```

### ⚠️ Model registries go stale

A plugin's model list is a snapshot from whenever it was built - it can drift from what the provider's live API actually serves (models get renamed, deprecated, or added). If a model that should work throws `Unknown model: ...`, or a request 404s even though `llm models` lists it, refresh the plugin's registry against the live API:

```bash
llm groq refresh
llm mistral refresh
```

Not every plugin supports a live refresh - check `llm <plugin-command> --help`.

Some plugins (e.g. `llm-deepseek`) only register a model if a key is already stored via `llm keys set <provider>` - setting `model.key` at runtime in the app's own code isn't enough for the model to show up at all. And on the box, `medel.service` runs as **root**, which has its own `llm` config under `/root/.config/io.datasette.llm/` - separate from any other user's, including `claudeops`. Any `llm keys set` or `llm ... refresh` needs to be run as root to actually take effect in production.

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

## 🌿 Environment Variables 🌿

The `.env` on **dobox** is a combination of the `.env` files in _medel_ and _domdom_notifications_. If you make a change to either, you'll need to update the one on **dobox**. It's a bit messy, but it works for now. 😅


##  🏌️ Failed Push Notification Attempts ❌

If a notification fails, `mess_model.sh` logs the error details and, on dobox, emails an alert to the admin (skipped locally if no `mail` command is available).

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

### 📲 Expo

The message is then sent as a push notification to the **RanDOM WisDOM** app.

### 📝 DynamoDB 📦

The _date, model_ and _message_ are logged to the `MedelLogs2` DynamoDB table.

👉 [MedelLogs2](https://eu-west-2.console.aws.amazon.com/dynamodbv2/home?region=eu-west-2#table?name=MedelLogs2)

---

## Running the job ᯓ🏃🏻‍♀️‍➡️

`mess_model.sh` does the following:

- resolves the right venv for the environment it's running in
- selects a model at random
- runs `message_model.py` with the selected model
- logs the message to DynamoDB

### ⏱️ Systemd Timer

A timer unit randomizes execution time within a given window - no cron/sleep hackery needed.

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
OnCalendar=*-*-* 15:00:00
# OnCalendar=*-*-* 00:00:00
RandomizedDelaySec=25200
# RandomizedDelaySec=86400
Persistent=true

[Install]
WantedBy=timers.target
```

Explanation:

- `OnCalendar=*-*-* 15:00:00`: Schedules the job to run daily starting from 3pm. 7 hours = 25200 seconds, covering a 15:00 → 22:00 window.

- `OnCalendar=*-*-* 00:00:00`: Schedules the job to run daily starting from midnight.

- `RandomizedDelaySec=86400`: Adds a randomized delay of up to 86400 seconds (24 hours).

- `Persistent=true`: Ensures that if the system is down during the scheduled time (e.g., midnight), the job will run as soon as the system comes back up. If that's not what you want for this job, drop Persistent=true.


#### 3, Enable and Start the Timer

```bash
systemctl enable medel.timer
systemctl start medel.timer
```

#### 4, Verification

Check when the job is next scheduled to run using the following command:

```bash
systemctl list-timers medel.timer
# or
systemctl list-timers | grep medel
# All timers
systemctl list-timers --all
```

Output:
```bash
| NEXT                        | LEFT          | LAST                        | PASSED         | UNIT          | ACTIVATES |
| Tue 2025-01-28 16:47:51 GMT | 19h left      | Mon 2025-01-27 08:30:07 GMT | 12h ago        | medel.timer   | medel.service |
```

#### 5, Pause the Timer

```bash
systemctl stop medel.service
```

`disable` only prevents the timer from starting at boot; it doesn't stop a timer that's already running. You need to stop it too:

```bash
systemctl stop medel.timer
systemctl disable medel.timer
```

After that, verify it's truly inactive:

```bash
systemctl status medel.timer
# You should see Active: inactive (dead) rather than active (waiting).
```

When you want to bring it back:

```bash
systemctl enable medel.timer
systemctl start medel.timer
```


#### 6, Debugging Steps

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

## 🪵 Logging to DynamoDB 📊

The application logs messages to a DynamoDB table named `MedelLogs2`. Each log entry includes a unique ID, the date, the model used, and the generated message.

#### Counter Item ⚠️

The Counter Item is a Live Record. Think of the counter item as the live scoreboard for your messages.

Your `get_next_id` function actively interacts with this specific item every single time it's called:

- It finds the item where `id` is 0.
- It reads the value of the `current_id` attribute from that item.
- It adds 1 to that value.
- It saves the new value back to the `current_id` attribute on that same `id`: 0 item.

---

<br>

## 🤔 Issues 🛠️

`message_model.py` sets the API key at runtime via `model.key = self.model_config.api_key` (sourced from `.env`). Some plugins (e.g. `llm-deepseek`) still need a key registered via `llm keys set <provider>` before they'll even list a model - see **⚠️ Model registries go stale** above for that, plus the root-vs-other-user config gotcha on **dobox**.

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