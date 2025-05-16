
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import base64
import gspread
from datetime import datetime
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class MatchVoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.matches_sheet = self.client.open("AOS").worksheet("matches")
        self.voicechats_sheet = self.client.open("AOS").worksheet("voicechats")

        self.category_id = 1360145897857482792
        self.midnight_task.start()

    def get_today_matches(self):
        today = datetime.now()
        today_strs = [
            today.strftime("%-m/%-d"),
            today.strftime("%-m/%d"),
            today.strftime("%m/%d"),
            today.strftime("%-m/%-d/%Y")
        ]
        print(f"🗓️ Accepting any of: {today_strs}")
        rows = self.matches_sheet.get_all_values()[1:]
        for row in rows:
            print(f"➡️ Date from sheet: {row[2].strip()}")
        return [row for row in rows if row[2].strip() in today_strs]

    async def create_today_voice_channels(self, guild):
        print(f"🔍 Found guild: {guild.name if guild else 'None'}")

        if not guild:
            print("❌ No guild found.")
            return

        category = guild.get_channel(self.category_id)
        print(f"📂 Found category: {category.name if category else 'None'}")

        if not category:
            print(f"❌ Category ID {self.category_id} not found in guild.")
            return

        # Get existing match IDs to prevent duplicates
        existing_rows = self.voicechats_sheet.get_all_values()
        existing_match_ids = set()
        for row in existing_rows:
            if len(row) >= 3 and row[2].strip().lower() != "match id":
                existing_match_ids.add(row[2].strip())

        matches = self.get_today_matches()
        print(f"📅 Matches for today: {matches}")
        for row in matches:
            if len(row) < 9:
                continue  # Ensure match ID exists

            match_id = row[8].strip()
            if match_id in existing_match_ids:
                print(f"⏩ Duplicate match ID detected: {match_id}, skipping.")
                continue

            enemy_team = row[4]
            league = row[5]
            date = row[2]
            time = row[3]
            players = row[7] if len(row) > 7 else "Unknown"
            name = f"{enemy_team} {league} {date} {time} {players}".strip()

            try:
                vc = await guild.create_voice_channel(name, category=category)
                self.voicechats_sheet.append_row([name, str(vc.id), match_id])
                print(f"✅ Created voice channel: {name}")
            except Exception as e:
                print(f"❌ Failed to create voice channel '{name}': {e}")

    @app_commands.command(name="creatematchvcs", description="Manually create today's match voice chats.")
    async def creatematchvcs(self, interaction: discord.Interaction):
        await self.create_today_voice_channels(interaction.guild)
        await interaction.response.send_message("✅ Match voice channels created for today.", ephemeral=True)

    @app_commands.command(name="clearmatchvcs", description="Clear all match voice channels listed in the voicechats tab.")
    async def clearmatchvcs(self, interaction: discord.Interaction):
        guild = interaction.guild
        deleted_channels = []
        failed_channels = []

        voice_rows = self.voicechats_sheet.get_all_values()[1:]
        for row in voice_rows:
            try:
                vc = guild.get_channel(int(row[1]))
                if vc:
                    await vc.delete()
                    deleted_channels.append(vc.name)
            except Exception as e:
                failed_channels.append(row[1])
                print(f"⚠️ Could not delete voice channel {row[1]}: {e}")

        self.voicechats_sheet.clear()
        await interaction.response.send_message(f"🧹 Cleared {len(deleted_channels)} match voice channels.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def midnight_task(self):
        now = datetime.utcnow()
        if now.hour == 7 and now.minute == 0:  # 12AM PST
            if self.bot.guilds:
                guild = self.bot.guilds[0]
                await self.create_today_voice_channels(guild)
                print("🌙 Auto-created voice channels at midnight PST.")
            else:
                print("❌ No guilds found for midnight task.")

async def setup(bot):
    await bot.add_cog(MatchVoiceChannels(bot))
