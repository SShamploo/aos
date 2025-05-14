
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from collections import defaultdict, deque
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

class AvailabilityScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_queue = deque()
        self.write_lock = asyncio.Lock()
        self.batch_writer.start()

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.gc = gspread.authorize(creds)
        self.sheet = self.gc.open("AOS").worksheet("availability")
        self.current_sheet = self.gc.open("AOS").worksheet("currentavailability")

    def cog_unload(self):
        self.batch_writer.cancel()

    @tasks.loop(seconds=5)
    async def batch_writer(self):
        async with self.write_lock:
            if not self.reaction_queue:
                return

            to_log = []
            seen = set()
            while self.reaction_queue:
                entry = self.reaction_queue.popleft()
                key = (entry["user_id"], entry["emoji"], entry["message_id"])
                if key not in seen:
                    seen.add(key)
                    to_log.append(entry)

            rows = self.sheet.get_all_values()
            existing = {(r[2], r[3], r[4]) for r in rows[1:] if len(r) >= 5}

            for r in to_log:
                if (r["user_id"], r["emoji"], r["message_id"]) not in existing:
                    try:
                        self.sheet.append_row([
                            r["timestamp"], r["user_name"], r["user_id"], r["emoji"],
                            r["message_id"], r["message_text"], r["league"]
                        ])
                    except Exception as e:
                        print(f"❌ Batch write failed: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.handle_reaction(payload, "add")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.handle_reaction(payload, "remove")

    async def handle_reaction(self, payload, event_type: str):
        if payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        channel_id = str(payload.channel_id)
        message_id = str(payload.message_id)
        emoji = payload.emoji.name if isinstance(payload.emoji, discord.PartialEmoji) else str(payload.emoji)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            current_rows = self.current_sheet.get_all_values()[1:]
            matched_row = next((r for r in current_rows if r[1] == channel_id and r[2] == message_id), None)

            if not matched_row:
                return

            league = matched_row[0]
            full_text = matched_row[3]
            message_text = full_text.split()[0].upper()

            if event_type == "add":
                self.reaction_queue.append({
                    "timestamp": timestamp,
                    "user_name": member.name,
                    "user_id": str(member.id),
                    "emoji": emoji,
                    "message_id": message_id,
                    "message_text": message_text,
                    "league": league
                })
            elif event_type == "remove":
                rows = self.sheet.get_all_values()
                for i, row in enumerate(rows[1:], start=2):
                    if len(row) >= 7 and row[2] == str(payload.user_id) and row[3] == emoji and row[4] == message_id:
                        self.sheet.delete_rows(i)
                        print(f"🗑️ Removed: {emoji} by {member.name} on {message_text}")
                        break

        except Exception as e:
            print(f"❌ Reaction tracking failed: {e}")

async def setup(bot):
    await bot.add_cog(AvailabilityScheduler(bot))
