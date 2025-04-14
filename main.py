import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load environment variables (for bot token, etc.)
load_dotenv()

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True  # Needed if using message commands

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# List of scripts to load (use folder.filename, no ".py")
initial_extensions = [
    "HCScheduler.scheduler",     # File: HCScheduler/scheduler.py
    "Results.match_results"      # File: Results/match_results.py
]

# Load all command modules
for ext in initial_extensions:
    try:
        bot.load_extension(ext)
        print(f"✅ Loaded: {ext}")
    except Exception as e:
        print(f"❌ Failed to load {ext}: {e}")

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user.name}")

# Run bot with token from .env file
bot.run(os.getenv("DISCORD_TOKEN"))
