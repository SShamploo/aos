print("👋 main.py is running...")

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import asyncio
from datetime import datetime

# Load environment variables from .env or Render dashboard
load_dotenv()

# Set up bot intents for full logging support
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True  # Needed for on_raw_reaction_add

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
        synced = await bot.tree.sync(guild=None)
        print(f"✅ Synced {len(synced)} global slash command(s)")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")
        traceback.print_exc()

# Main function to start bot
async def main():
    await load_cogs()
    await bot.start(os.getenv("TOKEN"))

# 👇 REACTION TRACKING WITH EMOJI NAME + DUPLICATE CHECK 👇
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    hc_cog = bot.get_cog("HCAvailabilityScheduler")
    if not hc_cog:
        print("⚠️ HCAvailabilityScheduler cog not loaded yet.")
        return

    channel_id = payload.channel_id
    message_id = payload.message_id

    # ✅ Extract emoji name only
    emoji = payload.emoji.name if isinstance(payload.emoji, discord.PartialEmoji) else str(payload.emoji)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message_text = hc_cog.sent_messages.get(channel_id, {}).get(message_id)

    if not message_text:
        return  # Not one of the tracked messages

    try:
        # ✅ Check for duplicates before logging
        existing_rows = hc_cog.sheet.get_all_values()
        for row in existing_rows[1:]:  # Skip headers
            if len(row) >= 6:
                uid = row[2].strip()
                em = row[3].strip()
                msg = row[4].strip()
                if uid == str(member.id) and em == emoji and msg == str(message_id):
                    print(f"⚠️ Duplicate reaction found — skipping log for {member.name}")
                    return

        # ✅ Log to Google Sheets
        hc_cog.sheet.append_row([
            timestamp,
            member.name,
            str(member.id),
            emoji,
            str(message_id),
            message_text
        ])
        print(f"✅ Logged: {member.name} reacted with {emoji} to '{message_text}'")
    except Exception as e:
        print(f"⚠️ Failed to write to Google Sheet: {e}")

# Run the bot
asyncio.run(main())

