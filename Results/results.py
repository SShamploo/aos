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

        self.match_type = discord.ui.TextInput(label="MATCH TYPE", placeholder="OBJ / CB / CHALL / SCRIM / COMP", required=True)
        self.league = discord.ui.TextInput(label="LEAGUE", placeholder="HC / AL", required=True)
        self.enemy_team = discord.ui.TextInput(label="ENEMY TEAM", placeholder="e.g., Phoenix Rising", required=True)
        self.map = discord.ui.TextInput(label="MAP", placeholder="e.g., Hotel", required=True)
        self.wl = discord.ui.TextInput(label="W/L", placeholder="W or L", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map)
        self.add_item(self.wl)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = interaction.user
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            screenshot_url = "N/A"

            # Prompt for screenshot
            await interaction.response.send_message("✅ Match info submitted! You have 60 seconds to reply with a screenshot.", ephemeral=True)

            def check(m):
                return (
                    m.author.id == user.id and
                    m.channel.id == interaction.channel.id and
                    m.attachments and
                    m.attachments[0].content_type.startswith("image/")
                )

            try:
                reply = await interaction.client.wait_for("message", check=check, timeout=60)
                if reply:
                    screenshot_url = reply.attachments[0].url
                    results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
                    if results_channel:
                        await results_channel.send(f"📸 Screenshot from {user.mention}:", file=await reply.attachments[0].to_file())
            except:
                pass  # No reply with image in 60 seconds

            # Append to Google Sheets
            values = [
                timestamp,
                user.name,
                str(user.id),
                self.match_type.value.upper(),
                self.league.value.upper(),
                self.enemy_team.value,
                self.map.value,
                self.wl.value.upper(),
                screenshot_url
            ]

            self.sheet.append_row(values)
        except Exception as e:
            print(f"❌ Error in modal submission: {e}")
            await interaction.followup.send("⚠️ Something went wrong while submitting match results.", ephemeral=True)

class MatchResultsButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(
        label="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀AOS MATCH RESULTS⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
        style=discord.ButtonStyle.danger,
        custom_id="match_results_button"
    )
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultsModal(self.sheet))

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Google Sheets auth
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8")
        creds_json = json.loads(creds)
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope))
        self.sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="matchresultprompt", description="Post the match result image + button.")
    async def matchresultprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel

        try:
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Failed to clean previous prompt: {e}")

        try:
            image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
            file = discord.File(fp=image_path, filename="matchresults.png")
            await channel.send(file=file)
        except Exception as e:
            print(f"❌ Failed to send match image: {e}")

        await channel.send(view=MatchResultsButton(self.sheet))
        await interaction.followup.send("✅ Match result prompt sent.", ephemeral=True)

# 🔁 Register view
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))
