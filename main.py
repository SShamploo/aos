print("👋 main.py is running...")

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback  # ✅ added for full error trace

# Load environment variables from .env
load_dotenv()

# Set up bot intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix="!", intents=intents)

# Load your scripts using folder.filename (no .py)
initial_extensions = [
    "HCScheduler.hcavailabilityscheduler",  # ✅ HCScheduler/hcavailabilityscheduler.py
    "Results.results"                       # ✅ Results/results.py
]

# Load each extension with full error trace
for ext in initial_extensions:
    try:
        bot.load_extension(ext)
        print(f"✅ Loaded: {ext}")
    except Exception as e:
        print(f"❌ Failed to load {ext}: {e}")
        traceback.print_exc()  # ✅ print full error to Render logs

@bot.event
async def on_ready():
    print(f"🤖 Bot is online as {bot.user.name}")

# Run bot with TOKEN from .env
bot.run(os.getenv("TOKEN"))
