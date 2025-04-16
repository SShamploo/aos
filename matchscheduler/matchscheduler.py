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

class MatchResultsModal(discord.ui.Modal, title="AOS MATCH RESULTS"):
    def __init__(self, sheet, image_files):
        super().__init__()
        self.sheet = sheet
        self.image_files = image_files

        self.match_type = discord.ui.TextInput(label="MATCH TYPE (OBJ/CB/CHALL/SCRIM/COMP)", required=True)
        self.league = discord.ui.TextInput(label="LEAGUE (HC/AL)", required=True)
        self.enemy_team = discord.ui.TextInput(label="ENEMY TEAM", required=True)
        self.map = discord.ui.TextInput(label="MAP", required=True)
        self.wl = discord.ui.TextInput(label="W/L", placeholder="W or L", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map)
        self.add_item(self.wl)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if not results_channel:
            await interaction.response.send_message("❌ #results channel not found.", ephemeral=True)
            return

        # Message format
        message = (
            f"# MATCH RESULTS: {self.match_type.value.upper()} | {self.league.value.upper()} | "
            f"{self.enemy_team.value.upper()} | {self.map.value.upper()} | {self.wl.value.upper()}"
        )

        await results_channel.send(message)

        urls = []
        for file in self.image_files:
            discord_file = await file.to_file()
            sent = await results_channel.send(file=discord_file)
            urls.append(sent.attachments[0].url)

        await interaction.response.send_message("✅ Match results submitted.", ephemeral=True)

        # Log to sheet
        try:
            self.sheet.append_row([
                timestamp,
                user.name,
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map.value,
                self.wl.value,
                ", ".join(urls)
            ])
        except Exception as e:
            print(f"⚠️ Failed to log to Google Sheets: {e}")

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds, scope))
        self.sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="matchresults", description="Submit match results with multiple screenshots.")
    async def matchresults(self, interaction: discord.Interaction):
        await interaction.response.send_message("📸 Please upload 1–10 screenshot(s) now:", ephemeral=True)

        def check(msg):
            return (
                msg.author.id == interaction.user.id and
                msg.channel == interaction.channel and
                msg.attachments and
                1 <= len(msg.attachments) <= 10
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            image_files = msg.attachments
            await msg.delete()
            await interaction.followup.send("📝 Now filling out the match form...", ephemeral=True)
            await interaction.response.send_modal(MatchResultsModal(self.sheet, image_files))
        except Exception as e:
            print(f"⚠️ Image upload failed or timeout: {e}")
            await interaction.followup.send("❌ Image upload failed or timed out.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MatchResults(bot))
