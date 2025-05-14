
print("👋 main.py is running...")

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import asyncio
from datetime import datetime
import json
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Import view from match results
from Results.results import MatchResultsButton

# Load environment variables
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix=None, intents=intents)

initial_extensions = [
    "Results.results",
    "playerinfo.playerinformation",
    "matchscheduler.matchscheduler",
    "availablescheduler.availablescheduler",
    "setlineup.setlineup"
]

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
        synced = await bot.tree.sync(guild=None)
        print(f"✅ Synced {len(synced)} global slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
        traceback.print_exc()

    # ✅ Register persistent match results view
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open("AOS").worksheet("matchresults")
        bot.add_view(MatchResultsButton(sheet))
        print("✅ Registered MatchResultsButton persistent view")
    except Exception as e:
        print(f"❌ Failed to register MatchResultsButton view: {e}")

# 🚀 Start bot
async def main():
    await load_cogs()
    await bot.start(os.getenv("TOKEN"))

asyncio.run(main())
