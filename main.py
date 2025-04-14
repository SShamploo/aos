print("👋 main.py is running...")

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import asyncio

# Load environment variables from .env or Render dashboard
load_dotenv()

# Set up bot intents for full logging support
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Create bot instance with no prefix (slash commands only)
bot = commands.Bot(command_prefix=None, intents=intents)

# List of cog modules to load (match folders/filenames)
initial_extensions = [
    "HCScheduler.hcavailabilityscheduler",
    "Results.results",
    "ticketsystem.tickets",
    "activitylog.logging",
    "levels.xp",
    "vc_autochannel.vc_autochannel"
]

# Load each cog
async def load_cogs():
    for ext in initial_extensions:
        try:
            await bot.load_extension(ext)
            print(f"✅ Loaded: {ext}")
        except Exception as e:
            print(f"❌ Failed to load {ext}: {e}")
            traceback.print_exc()

# Sync and clear ghost commands on ready
@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user.name}")
    try:
        # Sync commands globally and remove ghost/unused ones
        synced = await bot.tree.sync(guild=None)
        print(f"✅ Synced {len(synced)} global slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
        traceback.print_exc()

# Main function to start bot
async def main():
    await load_cogs()
    await bot.start(os.getenv("TOKEN"))

asyncio.run(main())

