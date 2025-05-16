
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
            print("❌ No guild found in interaction.")
            return

        category = guild.get_channel(self.category_id)
        print(f"📂 Found category: {category.name if category else 'None'}")

        if not category:
            print(f"❌ Category ID {self.category_id} not found in guild.")
            return

        # Delete old voice channels
        voice_rows = self.voicechats_sheet.get_all_values()[1:]
        for row in voice_rows:
            try:
                vc = guild.get_channel(int(row[1]))
                if vc:
                    await vc.delete()
            except Exception as e:
                print(f"⚠️ Could not delete voice channel: {e}")

        self.voicechats_sheet.clear()
        self.voicechats_sheet.append_row(["Channel Name", "Channel ID"])

        matches = self.get_today_matches()
        print(f"📅 Matches for today: {matches}")
        for row in matches:
            enemy_team = row[4]
            league = row[5]
            date = row[2]
            time = row[3]
            players = row[7] if len(row) > 7 else "Unknown"
            name = f"{enemy_team} {league} {date} {time} {players}"
            try:
                vc = await guild.create_voice_channel(name, category=category)
                self.voicechats_sheet.append_row([name, str(vc.id)])
                print(f"✅ Created voice channel: {name}")
            except Exception as e:
                print(f"❌ Failed to create voice channel '{name}': {e}")

    @app_commands.command(name="creatematchvcs", description="Manually create today's match voice chats.")
    async def creatematchvcs(self, interaction: discord.Interaction):
        await self.create_today_voice_channels(interaction.guild)
        await interaction.response.send_message("✅ Match voice channels created for today.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def midnight_task(self):
        now = datetime.utcnow()
        if now.hour == 7 and now.minute == 0:  # 12AM PST
            pass  # Optional: Add fallback logic to access guild for auto execution

async def setup(bot):
    await bot.add_cog(MatchVoiceChannels(bot))
