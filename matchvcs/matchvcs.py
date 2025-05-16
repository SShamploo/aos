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

    def get_today_date_str(self):
        utc_now = datetime.utcnow()
        pst_now = utc_now.hour - 7
        adjusted_hour = (pst_now + 24) % 24
        date_now = utc_now.replace(hour=adjusted_hour)
        return date_now.strftime("%-m/%-d")  # e.g., 5/18

    def get_today_matches(self):
        today = self.get_today_date_str()
        rows = self.matches_sheet.get_all_values()[1:]
        return [row for row in rows if row[2].strip() == today]

    async def create_today_voice_channels(self):
        guild = discord.utils.get(self.bot.guilds)
        if not guild:
            print("❌ Guild not found.")
            return

        category = guild.get_channel(self.category_id)
        if not category:
            print("❌ Category not found.")
            return

        # Delete old channels from voicechats tab
        voice_rows = self.voicechats_sheet.get_all_values()[1:]
        for row in voice_rows:
            try:
                vc = guild.get_channel(int(row[1]))
                if vc:
                    await vc.delete()
            except Exception as e:
                print(f"⚠️ Failed to delete old VC: {e}")

        self.voicechats_sheet.clear()
        self.voicechats_sheet.append_row(["Channel Name", "Channel ID"])

        # Create new voice channels
        matches = self.get_today_matches()
        for row in matches:
            name = f"{row[4]} {row[5]} {row[2]} {row[3]}"
            try:
                vc = await guild.create_voice_channel(name, category=category)
                self.voicechats_sheet.append_row([name, str(vc.id)])
            except Exception as e:
                print(f"❌ Failed to create VC {name}: {e}")

    @app_commands.command(name="creatematchvcs", description="Manually create today's match voice chats.")
    async def creatematchvcs(self, interaction: discord.Interaction):
        await self.create_today_voice_channels()
        await interaction.response.send_message("✅ Match voice channels created for today.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def midnight_task(self):
        now_utc = datetime.utcnow()
        if now_utc.hour == 7 and now_utc.minute == 0:  # Midnight PST
            await self.create_today_voice_channels()

async def setup(bot):
    await bot.add_cog(MatchVoiceChannels(bot))
