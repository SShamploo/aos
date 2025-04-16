
print("📦 Importing Results Cog...")

import discord
from discord import app_commands
from discord.ext import commands
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

        result_line = (
            f"# MATCH RESULTS: {self.match_type.value.upper()} | {self.league.value.upper()} | "
            f"{self.enemy_team.value.upper()} | {self.map.value.upper()} | {self.wl.value.upper()}"
        )

        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if not results_channel:
            await interaction.response.send_message("❌ #results channel not found.", ephemeral=True)
            return

        try:
            await results_channel.send(result_line)
            for file in self.image_files:
                await results_channel.send(file=file)

            for f in self.image_files:
                try:
                    await f.close()
                except:
                    pass

            self.sheet.append_row([
                timestamp,
                user.name,
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map.value,
                self.wl.value,
                "Images attached"
            ])

            await interaction.response.send_message("✅ Match results posted.", ephemeral=True)

        except Exception as e:
            print(f"⚠️ Failed to send results or log to sheet: {e}")
            await interaction.response.send_message("❌ Something went wrong posting results.", ephemeral=True)

class MatchResultsButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet
        self.buffer = {}

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def collect_images(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("📸 Upload Match Screenshots now, send 1–10 screenshots in a SINGLE message", ephemeral=True)

        def check(msg):
            return msg.author.id == interaction.user.id and msg.channel == interaction.channel and len(msg.attachments) <= 10

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=90)
            image_files = [await a.to_file() for a in msg.attachments]
            await msg.delete()

            await interaction.followup.send("📝 Now opening the match form...", ephemeral=True)
            await interaction.response.send_modal(MatchResultsModal(self.sheet, image_files))

        except Exception as e:
            print(f"⚠️ Image collection error: {e}")
            await interaction.followup.send("❌ Timeout or error. Please try again.", ephemeral=True)

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="matchresultsprompt", description="Send AOS match results prompt")
    async def matchresultsprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        try:
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await channel.send(file=file)
        await channel.send(view=MatchResultsButton(self.sheet))

        await interaction.followup.send("✅ Prompt sent.", ephemeral=True)

# Register Cog
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))
