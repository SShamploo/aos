
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
import pytz
import asyncio

CATEGORY_ID = 1360145897857482792
VOICECHAT_SHEET_NAME = "voicechats"

class MatchVoiceChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matches")
        self.log_sheet = self.client.open("AOS").worksheet(VOICECHAT_SHEET_NAME)
        self.create_voice_channels_daily.start()

    def cog_unload(self):
        self.create_voice_channels_daily.cancel()

    def get_today_date_str(self):
        central = pytz.timezone("US/Central")
        now = datetime.now(central)
        return now.strftime("%-m/%-d")

    def delete_logged_channels(self):
        rows = self.log_sheet.get_all_values()[1:]
        for row in rows:
            try:
                channel_id = int(row[1])
                channel = self.bot.get_channel(channel_id)
                if channel:
                    asyncio.create_task(channel.delete())
            except:
                pass
        if rows:
            self.log_sheet.batch_clear(["A2:B" + str(len(rows)+1)])

    def get_matches_for_today(self):
        today = self.get_today_date_str()
        matches = self.sheet.get_all_values()[1:]
        return [row for row in matches if row[2].strip() == today]

    async def create_voice_channels(self):
        self.delete_logged_channels()
        guild = discord.utils.get(self.bot.guilds)
        category = guild.get_channel(CATEGORY_ID)
        matches = self.get_matches_for_today()

        for row in matches:
            try:
                name = f"{row[4]} {row[5]} {row[2]} {row[3]}"
                vc = await guild.create_voice_channel(name, category=category)
                self.log_sheet.append_row([name, str(vc.id)])
            except Exception as e:
                print(f"Error creating channel: {e}")

    @tasks.loop(time=time(hour=0, minute=0, tzinfo=pytz.timezone('US/Central')))
    async def create_voice_channels_daily(self):
        await self.create_voice_channels()

    @app_commands.command(name="creatematchvcs", description="Manually create today's match voice channels.")
    async def creatematchvcs(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            await self.create_voice_channels()
            await interaction.followup.send("✅ Match voice channels created for today.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(MatchVoiceChannelManager(bot))
