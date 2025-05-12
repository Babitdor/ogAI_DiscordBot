import aiohttp
import json
import re
import discord
from discord.ext import commands
import os
import logging
from collections import defaultdict
import asyncio
from configs import (
    DISCORD_TOKEN,
    ALLOWED_ROLE,
    MAX_HISTORY_LEGNTH,
    bot_settings,
    url,
    headers,
)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
handler = logging.FileHandler(filename="AI_Bot.log", encoding="utf-8", mode="w")

# Global lock for processing requests
conversation_histories = defaultdict(list)
processing_active = False
request_queue = asyncio.Queue()


async def process_queue():
    global processing_active
    while True:
        if not request_queue.empty():
            processing_active = True
            message = await request_queue.get()
            try:
                thinking_msg = await message.channel.send("🤔 Thinking...")
                response = await query_qwen(message.content)
                await thinking_msg.edit(content=response)
            except Exception as e:
                await message.channel.send(f"⚠️ Error: {str(e)}", delete_after=10)
            finally:
                request_queue.task_done()
                processing_active = False
        await asyncio.sleep(0.1)


async def query_qwen(prompt):
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
        async with session.post(url, headers=headers, json=data) as response:
            if response.status != 200:
                return f"Error: Received status code {response.status}"

            buffer = ""
            async for chunk in response.content.iter_chunked(1024):
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


@bot.event
async def on_ready():
    bot.loop.create_task(process_queue())
    print(f"{bot.user} is ready to chat!")


@bot.command(name="setrole")
@commands.has_role(ALLOWED_ROLE)
async def role(ctx, *, prompt: str):
    """Setting for the Chatbot"""
    bot_settings["system_prompt"] = prompt
    await ctx.send(f"✅ Chatbot Role updated.", delete_after=10)


@bot.command(name="setmodel")
@commands.has_role(ALLOWED_ROLE)
async def model(ctx, *, model: str):
    """Sets a new model name (e.g mistral, gemma, qwen etc.)"""
    bot_settings["model"] = model
    await ctx.send(f"{model} is loaded.")


@bot.command(name="showsettings")
@commands.has_role(ALLOWED_ROLE)
async def show_settings(ctx):
    """Displays the current settings."""
    await ctx.send(
        f"📌 **Current Settings:**\n"
        f"**Model:** `{bot_settings['model']}`\n"
        f"**System Prompt:**\n```\n{bot_settings['system_prompt']}\n```"
    )


@bot.command(name="commands")
async def list_commands(ctx):
    """Lists all available bot commands."""
    cmds = []
    for command in bot.commands:
        if not command.hidden:
            cmds.append(f"**!{command.name}** – {command.help or 'No description'}")
    command_list = "\n".join(cmds)
    await ctx.send(f"📜 **Available Commands:**\n{command_list}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

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
                    f"{message.author.mention} LLM is busy. Your request is queued (#{request_queue.qsize()+1})",
                    delete_after=10,
                )
                await request_queue.put(message)
            else:
                await request_queue.put(message)

    await bot.process_commands(message)


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


bot.run(DISCORD_TOKEN, log_handler=handler, log_level=logging.DEBUG)
