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

# Modal form
class MatchResultsModal(discord.ui.Modal, title="Submit Match Result"):
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.match_type = discord.ui.TextInput(label="MATCH TYPE", placeholder="OBJ / CB / CHALL / SCRIM / COMP", required=True)
        self.league = discord.ui.TextInput(label="LEAGUE", placeholder="HC / AL", required=True)
        self.enemy_team = discord.ui.TextInput(label="ENEMY TEAM", required=True)
        self.map_played = discord.ui.TextInput(label="MAP", required=True)
        self.result = discord.ui.TextInput(label="W/L", placeholder="W or L", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map_played)
        self.add_item(self.result)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Post result message
        result_msg = f"# {self.match_type.value.upper()} | {self.league.value.upper()} | {self.enemy_team.value} | {self.map_played.value} | {self.result.value.upper()}"
        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")

        if not results_channel:
            await interaction.response.send_message("❌ Could not find #results channel.", ephemeral=True)
            return

        posted_msg = await results_channel.send(result_msg)

        # Prompt for screenshot
        await interaction.response.send_message("📸 Please upload a screenshot in the next message.", ephemeral=True)

        def check(m):
            return m.author == user and m.channel == interaction.channel and m.attachments

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60)
            attachment = msg.attachments[0]
            screenshot = await results_channel.send(attachment.url)

            # Delete original user message
            await msg.delete()

            # Save to Google Sheets
            try:
                load_dotenv()
                scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                creds = base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8")
                creds_json = json.loads(creds)
                client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope))
                sheet = client.open("AOS").worksheet("matchresults")

                sheet.append_row([
                    timestamp,
                    str(user),
                    self.match_type.value,
                    self.league.value,
                    self.enemy_team.value,
                    self.map_played.value,
                    self.result.value.upper(),
                    attachment.url
                ])
            except Exception as e:
                print(f"⚠️ Failed to write to Google Sheet: {e}")

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Timeout: No screenshot received.", ephemeral=True)

# Button view
class MatchResultsView(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def match_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultsModal(self.sheet))

# Cog
class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8")
        creds_json = json.loads(creds)
        client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope))
        self.sheet = client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="results", description="Post the match result submission button + image.")
    async def results_prompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        try:
            # Clean up any previous prompts
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")

        # Send image and button
        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await channel.send(file=file)
        await channel.send(view=MatchResultsView(self.sheet))

        await interaction.followup.send("✅ Prompt sent.", ephemeral=True)

# Setup
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsView(cog.sheet))
