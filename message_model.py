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
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, PartialCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Expo configuration
EXPO_PUSH_ENDPOINT = "https://exp.host/--/api/v2/push/send"

load_dotenv()

# Access the token
expo_push_token = os.getenv('EXPO_PUSH_TOKENS')

# DynamoDB Table Name
DYNAMODB_TABLE = "MedelLogs"

prompts = [
    "Hi, I'm Teed. Please could you provide a brief, practical reminder about mindfulness that I can use today?",
    "Hi, I'm Teed. I sometimes struggle with catastrophic thinking. Could you share some short and easy coping strategies that have helped others in similar situations?",
    "Hi, I'm Teed. Could you share a brief, meaningful memento mori reflection to help me maintain perspective on life?",
    "Hello, I'm Teed. When I experience social anxiety, what are some immediate techniques I can use to ground myself? Please keep it short and practical.",
    "Hello, my name is Teed. When life seems like an unending series of complications, how can I remember to be grateful for all the wonderful things we have? Please keep it brief.",
    "Life is so rich, isn't it?",
]

@dataclass
class LLMConfig:
    name: str
    model_id: str
    api_key_env: str
    
    @property
    def api_key(self) -> Optional[str]:
        return os.getenv(self.api_key_env)

class MessModel:
    AVAILABLE_MODELS = {
        'openai': LLMConfig('GPT-4o', 'gpt-4o', 'OPENAI_API_KEY'),
        'claude': LLMConfig('Claude', 'claude-3.5-sonnet', 'ANTHROPIC_API_KEY'),
        'gemini': LLMConfig('Gemini', 'gemini-1.5-flash-latest', 'GOOGLE_API_KEY'),
        'llama3': LLMConfig('Llama3', 'llama3', 'GROQ'),
        'mixtral': LLMConfig('Mixtral', 'mixtral-7b', 'GROQ'),
        'grok': LLMConfig('Grok', 'grok-beta', 'XAI_API_KEY'),
    }

    def __init__(self, model_name: str = 'grok'):
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
            prompt = random.choice(prompts)
            response = model.prompt(prompt)
            message = str(response) if response else "No message generated."
            # logger.info(f"Message generated: {message}")
            return message
        except Exception as e:
            logger.error(f"Failed to generate message: {e}")
            return None

    def log_to_dynamodb(self, date: str, model: str, message: str) -> None:
        try:
            self.dynamodb_client.put_item(
                TableName=DYNAMODB_TABLE,
                Item={
                    'date': {'S': date},
                    'model': {'S': model},
                    'message': {'S': message}
                }
            )
            logger.info(f"Logged to DynamoDB: date={date}, model={model}, message={message}")
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to log to DynamoDB: {e}")

    def create_notification_payload(self, message: str) -> Dict[str, Any]:
        title = "Message from a Model"
        short_message = (message[:50] + "...") if len(message) > 50 else message
        selected_image = random.randint(1, 9)

        return {
            "to": expo_push_token,
            "sound": "default",
            "title": title,
            "body": short_message,
            "data": {
                "id": self.model_config.name,  # Use the name from LLMConfig
                "title": "Lean In, Breath Out",
                "body": message,
                "imageUrl": f"https://followcrom-online.s3.eu-west-2.amazonaws.com/notifications/images/medel_{selected_image}.jpg",
                "url": "https://followcrom.com",
            },
            "ttl": 60,
            "priority": "high",
        }

    def send_push_notification(self) -> None:
        try:
            message = self.generate_message()
            if not message:
                logger.error("No message generated.")
                return

            # Log to DynamoDB
            # date = datetime.now(timezone.utc).isoformat()
            # Result: '2025-01-25T13:06:09.634696+00:00'
            date = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
            # Result: '2025-01-25T13:06:09'
            self.log_to_dynamodb(date, self.model_config.name, message)

            # Send push notification
            payload = self.create_notification_payload(message)
            response = requests.post(EXPO_PUSH_ENDPOINT, json=payload, headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
            if response.status_code == 200:
                logger.info(f"Notification sent successfully: {response.json()}")
            else:
                logger.error(f"Failed to send notification: {response.text}")
        except Exception as e:
            logger.error(f"Error in send_push_notification: {e}")

if __name__ == "__main__":
    import argparse

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--model', type=str, default='grok')
        args = parser.parse_args()

        model_name = args.model
        logger.info(f"Using model: {model_name}")

        try:
            model = MessModel(model_name)
            model.send_push_notification()
        except Exception as e:
            logger.error(f"Failed to send push notification using model '{model_name}': {e}")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Application initialization failed: {e}")
        sys.exit(1)
