from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_ROLE = "OGSF"
MAX_HISTORY_LEGNTH = 20
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot_settings = {
    "provider": "ollama",
    "system_prompt": "You should address yourself as ogAI, a helpful assistant",
    "model": "mistral:latest",
}

url_ollama = os.getenv("url_OLLAMA")
url_openrouter = os.getenv("url_OPENROUTER")


headers = {"Content-Type": "application/json"}
headers_dps = headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}

user_greetings = {
    "blurry1507": "Hello Gayman, Why are you Gay? @{name}",
    "bry4n1416": "Hello @{name}, my Creator!",
    "drballz_": "Hello @{name}, Fellow Goth Girls lover!",
    "blank409": "Hello @{name}, How's the infamous gheeman doing!",
    "interlex.": "Hello @{name}, When are you going to join voice? I can see online always! :3",
    "maeai": "Hello @{name}, How's a going brother?",
    "khohrii": "Hello @{name}, What's on your mind ?. Time for a debate. Hmmmmmm",
    "nfer47": "@{name}, Ah Goi, lah wan u Boss ka Valoverse!",
    "_deemee": "Hello @{name}, You're currently not natural as Greg Doucette would say it",
    "vodkaismyh2o.": "Hello @{name}, my fellow Doctor! Can you write me a Prescription for Roids? Just Kidding or am I? Hmmmm",
    ".illest": "Hello @{name}, Want me to generate some lyrics?",
}