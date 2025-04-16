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
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.match_type = discord.ui.TextInput(label="MATCH TYPE (OBJ / CB / CHALL / SCRIM / COMP)", required=True)
        self.league = discord.ui.TextInput(label="LEAGUE (HC / AL)", required=True)
        self.enemy_team = discord.ui.TextInput(label="ENEMY TEAM", required=True)
        self.map = discord.ui.TextInput(label="MAP", required=True)
        self.win_loss = discord.ui.TextInput(label="W/L (W / L)", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map)
        self.add_item(self.win_loss)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Match info received. Please upload your screenshot now.", ephemeral=True)

        def check(m):
            return (
                m.author.id == interaction.user.id and
                m.channel.id == interaction.channel.id and
                m.attachments and
                m.attachments[0].content_type.startswith("image/")
            )

        try:
            msg = await interaction.client.wait_for("message", check=check, timeout=60)
            image_url = msg.attachments[0].url

            # Send result message
            channel = discord.utils.get(interaction.guild.text_channels, name="results")
            if not channel:
                await interaction.followup.send("❌ #results channel not found.", ephemeral=True)
                return

            message = f"# {self.match_type.value} | {self.league.value} | {self.enemy_team.value} | {self.map.value} | {self.win_loss.value}"
            await channel.send(message)
            image_message = await channel.send(image_url)

            await msg.delete()

            # Log to Google Sheets
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.sheet.append_row([
                timestamp,
                str(interaction.user),
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map.value,
                self.win_loss.value,
                image_url
            ])

        except Exception as e:
            await interaction.followup.send("⚠️ Screenshot not received or an error occurred.", ephemeral=True)
            print(f"⚠️ Error waiting for image: {e}")

class MatchResultsButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(
        label="AOS MATCH RESULTS",
        style=discord.ButtonStyle.danger,
        custom_id="match_results_button"
    )
    async def send_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultsModal(self.sheet))

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8")
        creds_json = json.loads(creds)
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope))
        self.sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="matchresultprompt", description="Post match results image + button.")
    async def matchresultprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            async for msg in interaction.channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Failed to delete old prompt: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await interaction.channel.send(file=file)
        await interaction.channel.send(view=MatchResultsButton(self.sheet))

        await interaction.followup.send("✅ Prompt posted to channel.", ephemeral=True)

async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))
