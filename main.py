print("👋 main.py is running...")

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import asyncio

# Load environment variables from .env
load_dotenv()

# Set up bot intents
intents = discord.Intents.default()
# You can now omit message_content if you're only using slash commands

# Create bot instance (no command prefix needed)
bot = commands.Bot(command_prefix=None, intents=intents)

# List of cog modules to load
initial_extensions = [
    "HCScheduler.hcavailabilityscheduler",
    "Results.results"
]

# Async loader for slash-compatible cogs
async def load_cogs():
    for ext in initial_extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded: {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")
            traceback.print_exc()

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
        traceback.print_exc()

# Main entry to load and run the bot
async def main():
    await load_cogs()
    await bot.start(os.getenv("TOKEN"))

asyncio.run(main())

