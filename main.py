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
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# List of cog modules to load
initial_extensions = [
    "HCScheduler.hcavailabilityscheduler",  # ✅ HCScheduler/hcavailabilityscheduler.py
    "Results.results"                       # ✅ Results/results.py
]

# ✅ Async loader for discord.py v2+
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

# ✅ Load cogs before running the bot
async def main():
    await load_cogs()
    await bot.start(os.getenv("TOKEN"))

# Start the async main
asyncio.run(main())
