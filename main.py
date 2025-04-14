import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# List of command scripts to load (folder.filename)
initial_extensions = [
    "HCScheduler.scheduler",     # e.g., HCScheduler/scheduler.py
    "Results.match_results"      # e.g., Results/match_results.py
]

# Load extensions
for ext in initial_extensions:
    try:
        bot.load_extension(ext)
        print(f"✅ Loaded: {ext}")
    except Exception as e:
        print(f"❌ Failed to load {ext}: {e}")

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user.name}")

# Use TOKEN environment variable (your bot token)
bot.run(os.getenv("TOKEN"))

