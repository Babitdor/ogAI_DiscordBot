# 🧠 ogAI - Discord Bot

A Discord chatbot powered by local LLMs (like Mistral or Qwen), designed for the OGSF community. Supports commands, LLM queries, and role-based access.

## ✨ Features

- 🔍 Query local LLMs (Ollama-compatible)
- 🧹 Clear chat messages with `!clear`
- 🎛️ Change model and system prompts with commands
- 🔐 Role-based access (`OGSF` by default)
- 🆘 Dynamic `!commands` listing

## 🛠️ Setup

### 1. Clone the Repo

```bash
git clone https://github.com/your-username/ogsf-chatbot.git
cd ogsf-chatbot
```
### 2.Create and Activate a Virtual Environment
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```
### 3. Install Requirements
```
pip install -r requirements.txt
```
### 4. Configure .env
```
DISCORD_TOKEN=your_bot_token_here
url=your hosted API of your ollama
```

### 5.5. Run the Bot
```
python AI_Ollama.py
```



