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

load_dotenv()

# Access the token
expo_push_token = os.getenv('EXPO_PUSH_TOKENS')

# DynamoDB Table Name
DYNAMODB_TABLE = "MedelLogs2"

prompts = [
    "Hola, soy Teed. Dame un pequeño recordatorio de atención plena para que me mantenga presente hoy.",
    "Hola, soy Teed. ¿Somos todos psicológicamente frágiles? Responde conciso y directo.",
    "Hola, soy Teed. La vida es desordenada, pero hermosa. ¿Cómo puedo acceder instantáneamente a la gratitud cuando lo olvido?",
    "¿No es una locura que existamos?",
    "Hola, soy Teed. Dame un pequeño recordatorio de atención plena para que me mantenga presente hoy.",
    "Hola, soy Teed. Mi mente tiende a recordarme mis defectos. ¿Puedes darme una forma rápida y práctica de cambiar esa narrativa?",
    "Hola, soy Teed. Recuérdame por qué vale la pena disfrutar incluso de las pequeñas alegrías.",
    "La vida es un viaje extraño y maravilloso. ¿Cuál es un mantra rápido para disfrutar del viaje?",
    "La vida es tan rica, ¿no es así?",
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
        'gpt': LLMConfig('GPT-5-Nano', 'gpt-5', 'OPENAI_API_KEY'),
        'claude': LLMConfig('Claude', 'claude-3.7-sonnet-latest', 'ANTHROPIC_API_KEY'),
        'gemini': LLMConfig('Gemini', 'gemini-2.5-flash-lite-preview-09-2025', 'GOOGLE_API_KEY'),
        'llama': LLMConfig('Llama-4', 'llama-4', 'GROQ'),
        'qwen': LLMConfig('Qwen', 'qwen', 'GROQ'),
        'grok': LLMConfig('Grok', 'grok-4-fast', 'XAI_API_KEY'),
        'bedrock': LLMConfig('Bedrock', 'nova-pro', 'AWS_API_KEY'),
        'deepseek': LLMConfig('Deepseek', 'deepseek-reasoner', 'DEEPSEEK_API_KEY'),
        'mistral': LLMConfig('Mistral', 'mistral-large', 'MISTRAL_API_KEY'),
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
            master_prompt = "What follows is a request for practical mindfulness. Respond in a way that is brief, actionable, and easy to understand. Avoid fluff. Stay positive and supportive."
            prompt = f"{master_prompt}\n{random.choice(prompts)}"
            response = model.prompt(prompt)
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

    def log_to_dynamodb(self, date: str, model: str, message: str, id: int) -> None:
        try:
            self.dynamodb_client.put_item(
                TableName=DYNAMODB_TABLE,
                Item={
                    'id': {'N': str(id)},
                    'date': {'S': date},
                    'model': {'S': model},
                    'message': {'S': message}
                }
            )
            logger.info(f"Logged to DynamoDB: id={id}, date={date}, model={model}")
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
            
            # Log to DynamoDB with UK time
            date = datetime.now(ZoneInfo("Europe/London")).strftime('%Y-%m-%dT%H:%M:%S')
            next_id = self.get_next_id()  # Get the next incremented id
            self.log_to_dynamodb(date, self.model_config.name, message, next_id)

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
        except Exception as e:
            logger.error(f"Error in send_push_notification: {e}")
            sys.exit(1)

if __name__ == "__main__":
    import argparse

    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('--model', type=str, default='gpt') # Model you want to use
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
