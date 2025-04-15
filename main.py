print("👋 main.py is running...")

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import asyncio
from datetime import datetime

# Load environment variables
load_dotenv()

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix=None, intents=intents)

# ✅ Cogs list (ONLY new system)
initial_extensions = [
    "Results.results",
    "ticketsystem.tickets",
    "activitylog.logging",
    "levels.xp",
    "vc_autochannel.vc_autochannel",
    "playerinfo.playerinformation",
    "matchscheduler.matchscheduler",
    "availablescheduler.availablescheduler"  # ✅ Only active availability cog
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

# ✅ Track reactions from dropdown-based scheduler
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    await handle_reaction_event(payload, "add")

@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    await handle_reaction_event(payload, "remove")

# 🔁 Unified handler for new availability system
async def handle_reaction_event(payload, event_type: str):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    cog = bot.get_cog("AvailabilityScheduler")
    if not cog:
        print("⚠️ AvailabilityScheduler cog not found.")
        return

    channel_id = str(payload.channel_id)
    message_id = str(payload.message_id)
    emoji = payload.emoji.name if isinstance(payload.emoji, discord.PartialEmoji) else str(payload.emoji)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 🔍 Find message in tracked sent_messages
    message_text = None
    league = None

    for league_key, league_dict in cog.sent_messages.items():
        if channel_id in league_dict and message_id in league_dict[channel_id]:
            message_text = league_dict[channel_id][message_id]
            league = league_key
            break

    if not message_text:
        return  # Not tracked

    try:
        sheet = cog.sheet
        all_rows = sheet.get_all_values()
        rows = all_rows[1:]

        if event_type == "add":
            for row in rows:
                if len(row) >= 7 and row[2].strip() == str(member.id) and row[3].strip() == emoji and row[4].strip() == message_id:
                    return  # Duplicate

            sheet.append_row([
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
            for index, row in enumerate(rows, start=2):
                if len(row) >= 7 and row[2].strip() == str(payload.user_id) and row[3].strip() == emoji and row[4].strip() == message_id:
                    sheet.delete_rows(index)
                    print(f"🗑️ Removed: {emoji} by {member.name}")
                    return

    except Exception as e:
        print(f"⚠️ Failed to handle {event_type} reaction: {e}")

# 🔁 Start bot
asyncio.run(main())
