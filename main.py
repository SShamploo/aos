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
    "ticketsystem.tickets",
    "activitylog.logging",
    "levels.xp",
    "vc_autochannel.vc_autochannel",
    "playerinfo.playerinformation",
    "matchscheduler.matchscheduler",
    "availablescheduler.availablescheduler"
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

async def main():
    await load_cogs()
    await bot.start(os.getenv("TOKEN"))

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    await handle_reaction_event(payload, "add")

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    await handle_reaction_event(payload, "remove")

async def handle_reaction_event(payload, event_type: str):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    channel_id = str(payload.channel_id)
    message_id = str(payload.message_id)
    emoji = payload.emoji.name if isinstance(payload.emoji, discord.PartialEmoji) else str(payload.emoji)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ Load Google Sheet and match currentavailability entry
    try:
        # Setup Sheets access
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)

        current_sheet = client.open("AOS").worksheet("currentavailability")
        availability_sheet = client.open("AOS").worksheet("availability")

        rows = current_sheet.get_all_values()[1:]  # Skip header
        entry = next((r for r in rows if r[1] == channel_id and r[2] == message_id), None)

        if not entry:
            return  # Message ID not found

        league = entry[0]
        message_text = entry[3]

        # Check for duplicates in availability sheet
        all_data = availability_sheet.get_all_values()
        for row in all_data[1:]:
            if len(row) >= 7 and row[2] == str(member.id) and row[3] == emoji and row[4] == message_id:
                return  # Already logged

        if event_type == "add":
            availability_sheet.append_row([
                timestamp,
                member.name,
                str(member.id),
                emoji,
                message_id,
                message_text,
                league
            ])
            print(f"✅ Logged ADD: {member.name} → {emoji} on {message_text} ({league})")

        elif event_type == "remove":
            for index, row in enumerate(all_data[1:], start=2):
                if len(row) >= 7 and row[2] == str(payload.user_id) and row[3] == emoji and row[4] == message_id:
                    availability_sheet.delete_rows(index)
                    print(f"🗑️ Removed: {emoji} by {member.name}")
                    return

    except Exception as e:
        print(f"❌ Reaction tracking failed: {e}")

# Start bot
asyncio.run(main())
