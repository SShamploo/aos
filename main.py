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

# ✅ Cogs list
initial_extensions = [
    "HCScheduler.hcavailabilityscheduler",
    "ALScheduler.alavailabilityscheduler",
    "Results.results",
    "ticketsystem.tickets",
    "activitylog.logging",
    "levels.xp",
    "vc_autochannel.vc_autochannel",
    "playerinfo.playerinformation",
    "matchscheduler.matchscheduler",
    "availablescheduler.availablescheduler"  # ✅ NEW: Combined HC/AL Availability Cog
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

# ✅ Combined Reaction ADD Handler (for HC + AL + Dropdown Availability)
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    await handle_reaction_event(payload, event_type="add")

# ✅ Combined Reaction REMOVE Handler (for HC + AL + Dropdown Availability)
@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    await handle_reaction_event(payload, event_type="remove")

# 🔁 Shared logic for availability reaction tracking
async def handle_reaction_event(payload, event_type: str):
    if payload.user_id == bot.user.id:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    # ✅ Check all availability-related cogs
    for cog_name in ["HCAvailabilityScheduler", "ALAvailabilityScheduler", "AvailabilityScheduler"]:
        cog = bot.get_cog(cog_name)
        if not cog:
            continue

        # Match against the tracked messages
        channel_id = str(payload.channel_id)
        message_id = str(payload.message_id)
        emoji = payload.emoji.name if isinstance(payload.emoji, discord.PartialEmoji) else str(payload.emoji)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message_text = cog.sent_messages.get(channel_id, {}).get(message_id)

        if not message_text:
            continue  # Not one of this cog's tracked messages

        try:
            sheet = cog.sheet
            all_rows = sheet.get_all_values()
            rows = all_rows[1:]

            if event_type == "add":
                for row in rows:
                    if len(row) >= 6 and row[2].strip() == str(member.id) and row[3].strip() == emoji and row[4].strip() == message_id:
                        return  # Already logged

                sheet.append_row([
                    timestamp,
                    member.name,
                    str(member.id),
                    emoji,
                    message_id,
                    message_text
                ])
                print(f"✅ [{cog_name}] Logged ADD: {member.name} → {emoji} on {message_text}")

            elif event_type == "remove":
                for index, row in enumerate(rows, start=2):
                    if len(row) >= 6 and row[2].strip() == str(payload.user_id) and row[3].strip() == emoji and row[4].strip() == message_id:
                        sheet.delete_rows(index)
                        print(f"🗑️ [{cog_name}] Removed: {emoji} by {member.name}")
                        return

        except Exception as e:
            print(f"⚠️ [{cog_name}] Failed to handle {event_type} reaction: {e}")

# 🔁 Start bot
asyncio.run(main())
