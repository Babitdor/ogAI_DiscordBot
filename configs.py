from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_ROLE = "OGSF"
MAX_HISTORY_LEGNTH = 20


bot_settings = {
    "system_prompt": "You are a helpful and smart assistant",
    "model": "mistral:latest",
}

url = os.getenv("url")
headers = {"Content-Type": "application/json"}
