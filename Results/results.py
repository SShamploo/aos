
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
    def __init__(self, sheet, image_urls):
        super().__init__()
        self.sheet = sheet
        self.image_urls = image_urls

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

        await results_channel.send(result_line)

        for url in self.image_urls:
            await results_channel.send(url)

        try:
            self.sheet.append_row([
                timestamp,
                user.name,
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map.value,
                self.wl.value,
                ", ".join(self.image_urls)
            ])
        except Exception as e:
            print(f"⚠️ Failed to log to sheet: {e}")

        await interaction.response.send_message("✅ Match results submitted!", ephemeral=True)

class MatchResultsImageCollector(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet
        self.image_urls = []

    @discord.ui.button(label="Done uploading images", style=discord.ButtonStyle.success, custom_id="done_uploading_images")
    async def done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultsModal(self.sheet, self.image_urls))

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

        view = MatchResultsImageCollector(self.sheet)
        prompt = await channel.send("📸 **Upload Match Screenshots now, send 1–10 screenshots in a SINGLE message**", view=view)

        def check(msg):
            return msg.author.id == interaction.user.id and msg.attachments and msg.channel == interaction.channel

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=120)
            for attachment in msg.attachments:
                view.image_urls.append(attachment.url)
            await msg.delete()
        except Exception as e:
            print(f"⚠️ Image collection failed: {e}")
            await interaction.followup.send("❌ No images received in time.", ephemeral=True)
            return

        await interaction.followup.send("✅ Images received! Click 'Done uploading images' to continue.", ephemeral=True)

# Register View + Cog
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
