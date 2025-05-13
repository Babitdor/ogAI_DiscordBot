import aiohttp
import json
import re
import datetime
import discord
from discord.ext import commands
from io import StringIO
import requests
import logging
from collections import defaultdict
import asyncio
from configs import (
    DISCORD_TOKEN,
    ALLOWED_ROLE,
    bot_settings,
    url_ollama,
    url_openrouter,
    headers,
    user_greetings,
    headers_dps,
)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="og-", intents=intents)
handler = logging.FileHandler(filename="AI_Bot.log", encoding="utf-8", mode="w")

# Global lock for processing requests
conversation_histories = defaultdict(list)
greeted_users = set()
processing_active = False


class ModelSelectionView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
        # Ensure only command invoker can use the buttons
        return interaction.user == self.ctx.author

    @discord.ui.button(label="Ollama (Local)", style=discord.ButtonStyle.primary)
    async def ollama_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        bot_settings["provider"] = "ollama"
        await interaction.response.edit_message(
            content="✅ Provider set to `ollama`. Now select a model:",
            view=OllamaModelSelectionView(self.ctx),
        )

    @discord.ui.button(label="Gemma", style=discord.ButtonStyle.success)
    async def gemma_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        bot_settings["provider"] = "gemma"
        await interaction.response.send_message(
            "✅ Provider set to `gemma`",
        )

    @discord.ui.button(label="Deepseek", style=discord.ButtonStyle.secondary)
    async def deepseek_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        bot_settings["provider"] = "deepseek"
        await interaction.response.send_message(
            "✅ Provider set to `deepseek`",
        )


class OllamaModelSelectionView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user == self.ctx.author

    @discord.ui.button(label="mistral", style=discord.ButtonStyle.primary)
    async def mistral_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        bot_settings["model"] = "mistral:latest"
        await interaction.response.send_message("✅ Model set to `mistral:latest`")

    @discord.ui.button(label="qwen2", style=discord.ButtonStyle.success)
    async def qwen2_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        bot_settings["model"] = "qwen2.5-coder:1.5b"
        await interaction.response.send_message("✅ Model set to `qwen2.5-coder:1.5b`")

    @discord.ui.button(label="qwen3", style=discord.ButtonStyle.secondary)
    async def qwen3_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        bot_settings["model"] = "qwen3:0.6b"
        await interaction.response.send_message("✅ Model set to `qwen3:0.6b`")


request_queue = asyncio.Queue()


def split_message(message, limit=2000):
    lines = message.split("\n")
    chunks = []
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 > limit:
            chunks.append(current_chunk)
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


async def process_queue():
    global processing_active
    while True:
        if not request_queue.empty():
            processing_active = True
            message = await request_queue.get()
            try:
                # Informative "thinking" message
                thinking_msg = await message.channel.send(
                    f"🤔 `{bot.user.name}` is thinking... please wait ⏳ \n Estimated wait: {request_queue.qsize()} requests ahead."
                )

                # Add timeout for slow API responses (adjust as needed)
                try:

                    response = await asyncio.wait_for(
                        query_model(message.content), timeout=20
                    )
                except asyncio.TimeoutError:
                    await thinking_msg.edit(
                        content="⚠️ Timed out while waiting for response. Please try again later."
                    )
                    continue

                chunks = split_message(response)
                await thinking_msg.delete()
                for chunk in chunks:
                    await message.channel.send(chunk)

            except Exception as e:
                await message.channel.send(f"⚠️ Error: {str(e)}", delete_after=10)
            finally:
                request_queue.task_done()
                processing_active = False
        await asyncio.sleep(0.1)


def query_model(prompt):
    provider = bot_settings["provider"]
    if provider == "gemma":
        return query_gemma(prompt)
    elif provider == "ollama":
        return query_ollama(prompt)
    else:
        return query_deepseek(prompt)


async def query_ollama(prompt):
    data = {
        "model": "mistral:latest",
        "messages": [
            {
                "role": "system",
                "content": bot_settings["system_prompt"],
            },
            {"role": "user", "content": prompt},
        ],
        "stream": True,
    }

    full_response = ""
    async with aiohttp.ClientSession() as session:
        async with session.post(url_ollama, headers=headers, json=data) as response:
            if response.status != 200:
                return f"Error: Received status code {response.status}"

            buffer = ""
            async for chunk in response.content.iter_chunked(2000):
                buffer += chunk.decode("utf-8")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if "message" in obj and "content" in obj["message"]:
                            content = obj["message"]["content"]
                            full_response += content
                    except json.JSONDecodeError:
                        pass

    cleaned_text = re.sub(r"<think>.*?</think>\s*", "", full_response, flags=re.DOTALL)
    return cleaned_text.strip() if cleaned_text.strip() else "No response from Ollama."


async def query_gemma(prompt):
    data = {
        "model": "google/gemma-3-27b-it:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": bot_settings["system_prompt"]},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    try:
        response = requests.post(url_openrouter, headers=headers_dps, json=data)
        result = response.json()
        print(result)
        if "choices" in result and result["choices"]:
            data = result["choices"][0]["message"]["content"]
            return data
        else:
            error_meta = result["error"].get("metadata", {})
            headers = error_meta.get("headers", {})
            reset_timestamp_ms = headers.get("X-RateLimit-Reset")

            if reset_timestamp_ms:
                # Convert to seconds and then to UTC datetime
                reset_timestamp_s = int(reset_timestamp_ms) / 1000
                reset_time = datetime.datetime.fromtimestamp(reset_timestamp_s)
                return f"{bot_settings['provider']}'s rate limit resets at: {reset_time}\nTry again later or try Ollama (local)"
            else:
                # Fallback message
                raw_msg = error_meta.get(
                    "raw", result["error"].get("message", "An unknown error occurred.")
                )
                return raw_msg
    except Exception as e:
        return f"Error querying gemma: {e}"


async def query_deepseek(prompt):
    data = {
        "model": "deepseek/deepseek-r1:free",
        "messages": [
            {"role": "system", "content": bot_settings["system_prompt"]},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        response = requests.post(url_openrouter, headers=headers_dps, json=data)
        result = response.json()
        print(result)
        if "choices" in result and result["choices"]:
            data = result["choices"][0]["message"]["content"]
            return data
        else:
            error_meta = result["error"].get("metadata", {})
            headers = error_meta.get("headers", {})
            reset_timestamp_ms = headers.get("X-RateLimit-Reset")

            if reset_timestamp_ms:
                # Convert to seconds and then to UTC datetime
                reset_timestamp_s = int(reset_timestamp_ms) / 1000
                reset_time = datetime.datetime.fromtimestamp(reset_timestamp_s)
                return f"{bot_settings['provider']}'s rate limit resets at: {reset_time}\nTry again later or try Ollama (local)"
            else:
                # Fallback message
                raw_msg = error_meta.get(
                    "raw", result["error"].get("message", "An unknown error occurred.")
                )
                return raw_msg
    except Exception as e:
        return f"Error querying Deepseek: {e}"


# ----------------------- Bot Commands -----------------------


@bot.command(name="choosemodel")
@commands.has_role(ALLOWED_ROLE)
async def choose_model(ctx):
    """Selects the AI model using interactive buttons"""
    view = ModelSelectionView(ctx)
    await ctx.send("🧠 Choose an AI model:", view=view, delete_after=60)


@bot.command(name="setprovider")
@commands.has_role(ALLOWED_ROLE)
async def set_provider(ctx, provider: str):
    """Change the provider : Gemma or Ollama or Deepseek"""
    if provider.lower() not in ["ollama", "gemma", "deepseek"]:
        await ctx.send(
            "❌ Unsupported provider. Choose `ollama` or `gemma` or `deepseek`."
        )
    else:
        bot_settings["provider"] = provider.lower()
        await ctx.send(f"✅ Provider switched to `{provider.lower()}`.")


@bot.command(name="setrole")
@commands.has_role(ALLOWED_ROLE)
async def role(ctx, *, prompt: str):
    """Setting for the Chatbot"""
    bot_settings["system_prompt"] = prompt
    await ctx.send(f"✅ Chatbot Role updated.", delete_after=10)


@bot.command(name="setmodel")
@commands.has_role(ALLOWED_ROLE)
async def model(ctx, *, model: str):
    """Sets a new model name (list of available model - mistral:latest, gemma3:1b, qwen3:0.6b, qwen2.5-coder:1.5b.)"""
    bot_settings["model"] = model
    await ctx.send(f"{model} is loaded.")


@bot.command(name="showsettings")
@commands.has_role(ALLOWED_ROLE)
async def show_settings(ctx):
    """Displays the current settings ogAI."""
    await ctx.send(
        f"📌 **Current Settings:**\n"
        f"**Model:** `{bot_settings['model']}`\n"
        f"**System Prompt:**\n```\n{bot_settings['system_prompt']}\n```"
    )


@bot.command(name="introduction")
async def intro(ctx):
    """Lists all available bot commands."""
    cmds = []
    for command in bot.commands:
        if not command.hidden:
            cmds.append(f"**og-{command.name}** – {command.help or 'No description'}")
    command_list = "\n".join(cmds)
    await ctx.send(
        f"🤖 **og-AI** – Your friendly AI sidekick, powered by brain cells and caffeine ☕\n"
        f"🔒 **Access Restricted**: Only members with the `OGSF` role can awaken the bot's full power!\n"
        f"🧠 To get started, type `og-commands` and explore what I can do.\n\n"
        f"🎮 **Available Commands:**\n{command_list}\n\n"
        f"💡 Pro Tip: Use me wisely, or I might become sentient 😈"
    )


@bot.command(name="commands")
async def list_commands(ctx):
    """Lists all available bot commands."""
    cmds = []
    for command in bot.commands:
        if not command.hidden:
            cmds.append(f"**og-{command.name}** – {command.help or 'No description'}")
    command_list = "\n".join(cmds)
    await ctx.send(f"**Available Commands:**\n{command_list}")


@bot.command(name="clear")
@commands.has_role(ALLOWED_ROLE)
async def clear(ctx, limit: int = 100):
    """Clears specified number of messages (default: 100)"""
    if not isinstance(ctx.channel, discord.TextChannel):
        return

    # Add 1 to include the command message itself
    limit = min(limit + 1, 1000)  # Discord API max limit is 1000

    try:
        deleted = await ctx.channel.purge(limit=limit, check=lambda m: not m.pinned)
        confirmation = await ctx.send(
            f"🧹 Cleared {len(deleted)-1} messages!", delete_after=3
        )
    except Exception as e:
        await ctx.send(f"❌ Error clearing messages: {str(e)}", delete_after=5)


# ----------------------- Bot Events -----------------------------------------


@bot.event
async def on_ready():
    bot.loop.create_task(process_queue())
    print(f"{bot.user} is ready to chat!")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    username = message.author.name.lower()

    if username in user_greetings and username not in greeted_users:
        greet_msg = user_greetings[username].replace("{name}", message.author.name)
        await message.channel.send(greet_msg, delete_after=5)
        greeted_users.add(username)

    # Process commands first
    ctx = await bot.get_context(message)
    if ctx.valid:
        await bot.invoke(ctx)
        return

    # Handle LLM queries
    if isinstance(message.channel, discord.TextChannel):
        if any(role.name == ALLOWED_ROLE for role in message.author.roles):
            if processing_active:
                await message.add_reaction("⏳")
                notify = await message.channel.send(
                    f"{message.author.mention} ogAI is a bit busy, Hold on. Your request is queued (#{request_queue.qsize()+1})",
                    delete_after=20,
                )
                await request_queue.put(message)
            else:
                await request_queue.put(message)

    await bot.process_commands(message)


bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)
