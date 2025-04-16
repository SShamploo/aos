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

        self.match_type = discord.ui.TextInput(label="Match Type (OBJ / CB / CHALL / SCRIM / COMP)", required=True)
        self.league = discord.ui.TextInput(label="League (HC or AL)", required=True)
        self.enemy_team = discord.ui.TextInput(label="Enemy Team", required=True)
        self.map_played = discord.ui.TextInput(label="Map Played", required=True)
        self.win_loss = discord.ui.TextInput(label="W/L", placeholder="W or L", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map_played)
        self.add_item(self.win_loss)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Match report submitted! Please upload your screenshot.", ephemeral=True)

        # Send the match info to #results channel
        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if not results_channel:
            return

        message_content = (
            f"# {self.match_type.value} | {self.league.value} | "
            f"{self.enemy_team.value} | {self.map_played.value} | {self.win_loss.value}"
        )
        posted_msg = await results_channel.send(message_content)

        # Wait for screenshot from the same user
        def check(msg):
            return (
                msg.author == interaction.user and
                msg.channel == interaction.channel and
                msg.attachments and
                any(attachment.content_type.startswith("image/") for attachment in msg.attachments)
            )

        try:
            image_msg = await interaction.client.wait_for("message", timeout=60.0, check=check)
            image = image_msg.attachments[0]
            image_post = await results_channel.send(content=None, file=await image.to_file())
            await image_msg.delete()
        except Exception as e:
            await results_channel.send("⚠️ No screenshot provided in time.")
            image_post = None

        # Log to Google Sheets
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.sheet.append_row([
                timestamp,
                str(interaction.user),
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map_played.value,
                self.win_loss.value,
                image.url if image_post else "No Screenshot"
            ])
        except Exception as e:
            print(f"⚠️ Failed to log to Google Sheets: {e}")

class MatchResultsButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(
        label="AOS MATCH RESULTS",
        style=discord.ButtonStyle.danger,
        custom_id="match_results_button"
    )
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultsModal(self.sheet))

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="matchresultsprompt", description="Post match result image + button for leaders.")
    async def matchresultsprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Clean up old bot prompts
        try:
            async for msg in interaction.channel.history(limit=10):
                if msg.author.id == self.bot.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Failed to delete old messages: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await interaction.channel.send(file=file)
        await interaction.channel.send(view=MatchResultsButton(self.sheet))

        await interaction.followup.send("✅ Prompt sent.", ephemeral=True)

# 🔁 Register view on reload
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))
