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

# suppress the INFO level logs from botocore
logging.getLogger('botocore').setLevel(logging.WARNING)

# Expo configuration
EXPO_PUSH_ENDPOINT = "https://exp.host/--/api/v2/push/send"

load_dotenv()

# Access the token
expo_push_token = os.getenv('EXPO_PUSH_TOKENS')

# DynamoDB Table Name
DYNAMODB_TABLE = "MedelLogs"

prompts = [
    "Hey, I'm Teed. Hit me with a bite-sized mindfulness reminder to keep me present today.",
    "Hey, I'm Teed. Give me a punchy memento mori reminder — life's short, I wanna make it count. Keep it tight and practical.",
    "Hi, I'm Teed. Are we all psychologically fragile? Keep your answer crisp and direct.",
    "Hi, I'm Teed. Life's messy, but beautiful. How do I instantly tap into gratitude when I forget?",
    "Isn't it wild that we exist at all?",
    "Hey, I'm Teed. Drop a micro-dose of perspective — something to keep me centered today.",
    "Hi, I'm Teed. My mind is prone to reminding me of my flaws. Can you give me a quick, practical way to shift that narrative?",
    "Hey, I'm Teed. Remind me why even small joys are worth savoring.",
    "Life's a weird, wonderful ride - what's a quick mantra to enjoy the trip?",
    "Hey, I'm Teed. How do I stop overthinking and just be here now?",
    "Life is so rich, isn't it?",
    "Hey, I'm Teed. Need a quick reality check to snap out of negative self-talk.",
    "Hey, I'm Teed. Drop a zen-like whisper to help me detach from today's chaos.",
    "Hi, I'm Teed. What's a lightning-fast way to remember my own resilience?",
    "Hey, I'm Teed. Give me a pocket-sized perspective shifter right now.",
    "Hi, I'm Teed. How do I interrupt my brain's default spiral of worry?",
    "Hey, I'm Teed. Serve me a shot of instant self-compassion.",
    "Hey, I'm Teed. How do I cultivate stillness in the middle of my storm?",
    "Hola, soy Teed. Dame un micro-mantra para interrumpir mi autojuicio.",
    "Hola, soy Teed. ¿Cómo puedo recordar que la vida es un viaje, no un destino?",
    "Hola, soy Teed. ¿Cómo recuerdo que este momento es suficiente?", 
    "Oye, soy Teed. Susurra un recordatorio de mi propia fuerza silenciosa.",
    "Hola, soy Teed. ¿Qué rayo de perspectiva puedo tener cuando todo parece estancado?"
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
        'gpt': LLMConfig('GPT-4.5', 'gpt-4.5', 'OPENAI_API_KEY'),
        'claude': LLMConfig('Claude', 'claude-3.7-sonnet-latest', 'ANTHROPIC_API_KEY'),
        'gemini': LLMConfig('Gemini', 'gemini-2.5-pro-preview-03-25', 'GOOGLE_API_KEY'),
        'llama': LLMConfig('Llama-4', 'llama-4', 'GROQ'),
        'qwen': LLMConfig('Qwen', 'qwen', 'GROQ'),
        'grok': LLMConfig('Grok', 'grok-3-latest', 'XAI_API_KEY'),
        'bedrock': LLMConfig('Bedrock', 'nova-pro', 'AWS_API_KEY'),
        'deepseek': LLMConfig('Deepseek', 'deepseek-reasoner', 'DEEPSEEK_API_KEY'),
        'mistral': LLMConfig('Mistral', 'mistral-large', 'MISTRAL_API_KEY'),
    }

    def __init__(self, model_name: str = 'mistral'):
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
            master_prompt = "What follows is a request for practical mindfulness. Respond in a way that is brief, actionable, and easy to understand. Avoid fluff. Stay positive and supportive."
            prompt = f"{master_prompt}\n{random.choice(prompts)}"
            response = model.prompt(prompt)
            message = str(response) if response else "No message generated."
            # logger.info(f"Message generated: {message}")
            return message
        except Exception as e:
            logger.error(f"Failed to generate message: {e}")
            sys.exit(1)

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
            logger.info(f"Logged to DynamoDB: date={date}, model={model}")
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to log to DynamoDB: {e}")
            sys.exit(1)

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
                # logger.info(f"Notification sent successfully: {response.json()}")
                logger.info(f"Notification sent successfully")
            else:
                logger.error(f"Failed to send notification: {response.text}")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error in send_push_notification: {e}")
            sys.exit(1)

if __name__ == "__main__":
    import argparse

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--model', type=str, default='qwen') # Model you want to use
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
