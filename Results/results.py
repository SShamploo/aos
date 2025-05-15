
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
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.match_id = discord.ui.TextInput(
            label="SCHEDULED MATCH ID",
            placeholder="The match ID attached to the scheduled match in Dates and Times",
            required=True
        )
        self.maps_won = discord.ui.TextInput(
            label="Maps Won",
            placeholder="Dealership 6-2, Hacienda 6-4, Protocol 6-5, etc.",
            required=True
        )
        self.maps_lost = discord.ui.TextInput(
            label="Maps Lost",
            placeholder="Dealership 2-6, Hacienda 4-6, Protocol 5-6, etc.",
            required=True
        )
        self.aos_players = discord.ui.TextInput(
            label="AOS Players",
            placeholder="Shamp, NxComp, Jay, etc.",
            required=True
        )
        self.cb_results = discord.ui.TextInput(
            label="CB Results",
            placeholder="Abbreviated W/L only",
            required=True
        )

        self.add_item(self.match_id)
        self.add_item(self.maps_won)
        self.add_item(self.maps_lost)
        self.add_item(self.aos_players)
        self.add_item(self.cb_results)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        results_channel = interaction.client.get_channel(1361457240929996980)
        if not results_channel:
            await interaction.response.send_message("❌ Results channel not found.", ephemeral=True)
            return

        # Triple-quoted message block to eliminate unterminated string issue
        result_message = f"""# MATCH RESULTS: {self.match_id.value.strip()}

# Maps Won
{self.maps_won.value.strip()}

# Maps Lost
{self.maps_lost.value.strip()}

# AOS Players
{self.aos_players.value.strip()}

# CB Results
{self.cb_results.value.strip()}"""

        await results_channel.send(result_message)
        await interaction.response.send_message("✅ Match results submitted!", ephemeral=True)

        # Log to Google Sheets
        self.sheet.append_row([
            timestamp,
            user.name,
            self.match_id.value.strip(),
            self.maps_won.value.strip(),
            self.maps_lost.value.strip(),
            self.aos_players.value.strip(),
            self.cb_results.value.strip()
        ])

class MatchResultsButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultsModal(self.sheet))

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

# Register View + Cog
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))
