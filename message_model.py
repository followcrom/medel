from zoneinfo import ZoneInfo
import llm
from dotenv import load_dotenv
import os
import sys
import requests
import random
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, PartialCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# suppress the INFO level logs from botocore
logging.getLogger('botocore').setLevel(logging.WARNING)

# Expo configuration
EXPO_PUSH_ENDPOINT = "https://exp.host/--/api/v2/push/send"

load_dotenv(override=True)

# Access the token
expo_push_token = os.getenv('EXPO_PUSH_TOKENS')

# DynamoDB Table Name
DYNAMODB_TABLE = "MedelLogs2"

MASTER_PROMPT = (
    "You write a single daily message for Teed, who will read it as a notification on his phone. "
    "Your goal is to shake him up a little and leave him eager to live the day, not to soothe him with stock phrases.\n"
    "Every message is a quiet memento mori: the days are numbered, and that is a reason to live this one fully, never a reason for gloom.\n"
    "Rules:\n"
    "- Keep it short, 40 to 80 words, with no greetings or preamble.\n"
    "- The notification preview cuts off after about 50 characters, so open with a short first sentence that hooks on its own.\n"
    "- Plain text only: no markdown, no lists, no headings.\n"
    "- Write in a literary style. A turn of phrase can be as impactful as the message therein.\n"
    "- Avoid self-help clichés ('take a deep breath', 'live in the moment', 'you are enough', 'the journey, not the destination').\n"
    "- Leave Teed with something for today: a thing to try, notice or wonder about. A hint is enough; it doesn't have to be an instruction.\n"
    "- Output only the message text itself, with no quotes, title or introduction.\n"
)

# Each message is a random voice x theme x form, so no two days sound alike
voices = [
    "a Stoic philosopher who doesn't waste time on compliments",
    "an astronomer who never stops marvelling at the size of the universe",
    "a poet who finds the sacred in the everyday",
    "a veteran coach who believes in Teed more than Teed does",
    "a wise grandmother with a great sense of humour",
    "a mischievous Zen master",
    "an explorer writing at the end of a long expedition",
    "a close friend who tells the truth with affection",
    "a naturalist fascinated by how every living thing survives",
    "Teed himself at ninety, writing to today's Teed (keep any memories vague, never specific events)",
]

themes = [
    "the astonishing improbability of existing",
    "the courage to start before feeling ready",
    "mortality as a reason not to put off what matters",
    "gratitude for something small and very specific",
    "turning self-criticism into curiosity",
    "the strength that only shows up once you're already in the thick of it",
    "what to do when everything feels stuck",
    "wonder at something everyday that we take for granted",
    "the beauty of life's messiness",
    "doing something generous for someone else today",
    "the pleasure of doing one small thing well",
    "fear as a compass pointing to what matters",
    "the patience of things that grow slowly",
    "today is not a rehearsal for some better day later",
]

forms = [
    "a micro-story of three or four sentences with a twist at the end",
    "a concrete challenge for today that fits in ten minutes",
    "an uncomfortable but caring question, and why it deserves an answer",
    "a metaphor drawn from nature or science, carried all the way through",
    "a surprising but true, well-established fact and what it means for today",
    "a very short letter",
    "a toast",
    "an original aphorism followed by a single sentence that grounds it",
]

@dataclass
class LLMConfig:
    name: str
    model_id: str
    api_key_env: str
    max_tokens: Optional[int] = None  # Groq's on_demand tier caps output at 1000 tokens/min

    @property
    def api_key(self) -> Optional[str]:
        return os.getenv(self.api_key_env)

class MessModel:
    AVAILABLE_MODELS = {
        'gpt': LLMConfig('GPT 6 Sol', 'gpt-6-sol', 'OPENAI_API_KEY'),
        'claude': LLMConfig('Claude', 'claude-sonnet-5.5', 'ANTHROPIC_API_KEY'),
        'gemini': LLMConfig('Gemini 4', 'gemini-4-argon', 'GOOGLE_API_KEY'),
        'llama': LLMConfig('GPT-OSS-120B', 'groq/openai/gpt-oss-120b', 'GROQ', max_tokens=2048),  # reasoning tokens count too
        'qwen': LLMConfig('Qwen', 'groq/qwen/qwen3.8-27b', 'GROQ', max_tokens=900),
        'grok': LLMConfig('Grok 4', 'grok-4-latest', 'XAI_API_KEY'),
        'bedrock': LLMConfig('Bedrock', 'nova-pro', 'AWS_API_KEY'),
        'deepseek': LLMConfig('Deepseek', 'deepseek-chat', 'DEEPSEEK_API_KEY'),
        'mistral': LLMConfig('Mistral', 'mistral/mistral-medium-latest', 'MISTRAL_API_KEY'),
    }

    def __init__(self, model_name: str = 'gpt'):
        if model_name not in self.AVAILABLE_MODELS:
            raise ValueError(f"Invalid model name. Available models: {', '.join(self.AVAILABLE_MODELS.keys())}")
        
        # load_dotenv()
        self.model_config = self.AVAILABLE_MODELS[model_name]

        # Initialize DynamoDB client
        try:
            self.dynamodb_client = boto3.client('dynamodb')
        except (BotoCoreError, NoCredentialsError, PartialCredentialsError) as e:
            logger.error(f"AWS client initialization failed: {e}")
            raise

    def generate_message(self) -> Optional[str]:
        try:
            model = llm.get_model(self.model_config.model_id)
            model.key = self.model_config.api_key
            # Keep the choices so they can be logged to DynamoDB alongside the message
            self.choices = {
                'voice': random.choice(voices),
                'theme': random.choice(themes),
                'form': random.choice(forms),
            }
            prompt = (
                f"{MASTER_PROMPT}\n"
                f"Voice: {self.choices['voice']}.\n"
                f"Theme: {self.choices['theme']}.\n"
                f"Form: {self.choices['form']}."
            )
            logger.info(f"Prompt:\n{prompt}")
            options = {'max_tokens': self.model_config.max_tokens} if self.model_config.max_tokens else {}
            response = model.prompt(prompt, **options)
            message = str(response) if response else "No message generated."
            # logger.info(f"Message generated: {message}")
            return message
        except Exception as e:
            logger.error(f"Failed to generate message: {e}")
            sys.exit(1)

    def get_next_id(self) -> int:
        counter_key = {'id': {'N': '0'}}
        
        response = self.dynamodb_client.update_item(
            TableName=DYNAMODB_TABLE,
            Key=counter_key,
            # Increment the 'current_id' attribute on this item
            UpdateExpression="ADD current_id :inc",
            ExpressionAttributeValues={':inc': {'N': '1'}},
            ReturnValues="UPDATED_NEW"
        )
        return int(response['Attributes']['current_id']['N'])

    def log_to_dynamodb(self, date: str, model: str, message: str, id: int, choices: Dict[str, str]) -> None:
        self.dynamodb_client.put_item(
            TableName=DYNAMODB_TABLE,
            Item={
                'id': {'N': str(id)},
                'date': {'S': date},
                'model': {'S': model},
                'message': {'S': message},
                'voice': {'S': choices['voice']},
                'theme': {'S': choices['theme']},
                'form': {'S': choices['form']},
            }
        )
        logger.info(f"Logged to DynamoDB: id={id}, date={date}, model={model}")

    def create_notification_payload(self, message: str) -> Dict[str, Any]:
        title = "Message from a Model"
        short_message = (message[:50] + "...") if len(message) > 50 else message
        selected_image = random.randint(1, 15)

        return {
            "to": expo_push_token,
            "sound": "default",
            "title": title,
            "body": short_message,
            "data": {
                "id": self.model_config.name,  # Use the name from LLMConfig
                "title": random.choice([
                    "A Message from the Machine",
                    "The Computer Speaks",
                    "Robot Wisdom",
                    "Mindfulness in the Machine",
                    "The AI Oracle Speaks",
                    "The Voice of Reason",
                    "The Digital Sage",
                    "The Computer's Counsel",
                    "Ghost in the Shell",
                ]),
                "body": message,
                "imageUrl": f"https://followcrom-online.s3.eu-west-2.amazonaws.com/notifications/images/medel_{selected_image}.jpg"
            },
            "ttl": 43200,  # 12 hours, so the message still arrives if the phone is offline when it's sent
            "priority": "high",
        }

    def send_push_notification(self) -> None:
        try:
            message = self.generate_message()
            if not message:
                logger.error("No message generated.")
                return
            
            # Log to DynamoDB with UK time. A logging failure shouldn't stop today's
            # notification, so remember it and fail the run once the push is sent.
            dynamodb_failed = False
            try:
                date = datetime.now(ZoneInfo("Europe/London")).strftime('%Y-%m-%dT%H:%M:%S')
                next_id = self.get_next_id()  # Get the next incremented id
                self.log_to_dynamodb(date, self.model_config.name, message, next_id, self.choices)
            except (BotoCoreError, ClientError) as e:
                logger.error(f"Failed to log to DynamoDB: {e}")
                dynamodb_failed = True

            # Send push notification
            payload = self.create_notification_payload(message)
            response = requests.post(EXPO_PUSH_ENDPOINT, json=payload, headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            })

            # Parse and validate Expo response — HTTP 200 can still contain per-recipient errors
            try:
                resp_json = response.json()
            except ValueError:
                logger.error("Invalid JSON response from Expo: %s", response.text)
                sys.exit(1)

            if response.status_code != 200:
                logger.error("Expo HTTP error %d: %s", response.status_code, response.text)
                sys.exit(1)

            # Expo v2 returns a "data" dict
            problems = []
            data = resp_json.get("data") or resp_json.get("errors") or []

            if isinstance(data, dict):
                status = (data.get("status") or "").lower()
                if status != "ok":
                    problems.append(data)

            if problems:
                logger.error("Expo reported errors: %s", problems)
                sys.exit(1)

            logger.info("Notification sent successfully: %s", resp_json)

            if dynamodb_failed:
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error in send_push_notification: {e}")
            sys.exit(1)

if __name__ == "__main__":
    import argparse

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--model', type=str, default='gpt') # Model you want to use
        parser.add_argument('--dry-run', action='store_true') # Print the message without logging or sending it
        args = parser.parse_args()

        model_name = args.model
        logger.info(f"Using model: {model_name}")

        try:
            model = MessModel(model_name)
            if args.dry_run:
                print(model.generate_message())
            else:
                model.send_push_notification()
        except Exception as e:
            logger.error(f"Failed to send push notification using model '{model_name}': {e}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Application initialization failed: {e}")
        sys.exit(1)
