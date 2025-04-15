import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class MatchScheduleModal(discord.ui.Modal, title="📆 Schedule a Match"):
    def __init__(self, league, match_type, sheet):
        super().__init__()
        self.league = league
        self.match_type = match_type
        self.sheet = sheet

        self.date = discord.ui.TextInput(label="Date", placeholder="MM/DD/YYYY", required=True)
        self.time = discord.ui.TextInput(label="Time", placeholder="e.g., 7PM CST", required=True)
        self.enemy_team = discord.ui.TextInput(label="Enemy Team", placeholder="Enter team name", required=True)

        self.add_item(self.date)
        self.add_item(self.time)
        self.add_item(self.enemy_team)

    async def on_submit(self, interaction: discord.Interaction):
        # Format and send to #datesandtimes
        channel = discord.utils.get(interaction.guild.text_channels, name="datesandtimes")
        if not channel:
            await interaction.response.send_message("❌ #datesandtimes channel not found.", ephemeral=True)
            return

        role_mention = "@CAPO" if self.league == "HC" else "@SOLDIER"

        message = (
            f"# :AOSgold: {self.date.value} | {self.time.value} | "
            f"{self.enemy_team.value} | {self.league} | {self.match_type} {role_mention}"
        )
        await channel.send(message)
        await interaction.response.send_message("✅ Match scheduled successfully!", ephemeral=True)

        # Log to Google Sheet
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.sheet.append_row([
                timestamp,
                str(interaction.user),
                self.date.value,
                self.time.value,
                self.enemy_team.value,
                self.league,
                self.match_type
            ])
        except Exception as e:
            print(f"⚠️ Failed to write to Google Sheet: {e}")

class MatchScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Google Sheets setup
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matches")

    @app_commands.command(name="schedulematch", description="Schedule a match and notify the team.")
    @app_commands.choices(
        league=[
            app_commands.Choice(name="HC", value="HC"),
            app_commands.Choice(name="AL", value="AL"),
        ],
        match_type=[
            app_commands.Choice(name="OBJ", value="OBJ"),
            app_commands.Choice(name="CB", value="CB"),
            app_commands.Choice(name="CHALL", value="CHALL"),
            app_commands.Choice(name="SCRIM", value="SCRIM"),
            app_commands.Choice(name="COMP", value="COMP"),
        ]
    )
    async def schedulematch(
        self,
        interaction: discord.Interaction,
        league: app_commands.Choice[str],
        match_type: app_commands.Choice[str]
    ):
        await interaction.response.send_modal(MatchScheduleModal(league.value, match_type.value, self.sheet))

# Setup
async def setup(bot):
    await bot.add_cog(MatchScheduler(bot))

