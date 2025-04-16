print("📦 Importing Results Cog...")

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

class MatchResultsModal(discord.ui.Modal, title="📊 MATCH RESULTS FORM"):
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.match_type = discord.ui.TextInput(label="MATCH TYPE (OBJ/CB/CHALL/SCRIM/COMP)", required=True)
        self.league = discord.ui.TextInput(label="LEAGUE (HC/AL)", required=True)
        self.enemy_team = discord.ui.TextInput(label="ENEMY TEAM", required=True)
        self.map_played = discord.ui.TextInput(label="MAP", required=True)
        self.win_loss = discord.ui.TextInput(label="W/L (W or L)", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map_played)
        self.add_item(self.win_loss)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        channel = discord.utils.get(interaction.guild.text_channels, name="results")

        # Send embed first
        embed = discord.Embed(title="📊 Match Report", color=discord.Color.blurple())
        embed.add_field(name="Match Type", value=self.match_type.value, inline=True)
        embed.add_field(name="League", value=self.league.value, inline=True)
        embed.add_field(name="Enemy Team", value=self.enemy_team.value, inline=False)
        embed.add_field(name="Map", value=self.map_played.value, inline=True)
        embed.add_field(name="W/L", value=self.win_loss.value, inline=True)
        embed.set_footer(text=f"Submitted by {user.name}", icon_url=user.display_avatar.url)

        if not channel:
            await interaction.response.send_message("❌ #results channel not found.", ephemeral=True)
            return

        await interaction.response.send_message("✅ Now upload the screenshot...", ephemeral=True)
        embed_msg = await channel.send(embed=embed)

        # Wait for screenshot image
        def check(m):
            return m.author.id == user.id and m.channel.id == channel.id and m.attachments

        try:
            msg = await interaction.client.wait_for("message", timeout=60.0, check=check)
            attachment = msg.attachments[0]
            screenshot_msg = await channel.send(content=None, file=await attachment.to_file())
            await msg.delete()
        except Exception:
            screenshot_msg = await channel.send("⚠️ Screenshot not provided.")
            attachment = None

        # Log to Google Sheets
        try:
            load_dotenv()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            image_url = attachment.url if attachment else "N/A"

            self.sheet.append_row([
                timestamp,
                str(user),
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map_played.value,
                self.win_loss.value,
                image_url
            ])
        except Exception as e:
            print(f"⚠️ Failed to log to Google Sheet: {e}")

class MatchResultsButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def send_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultsModal(self.sheet))

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="matchresultprompt", description="Post the match results submission prompt")
    async def matchresultprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel

        # Clean old prompts
        try:
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Failed to clean old prompt: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await channel.send(file=file)
        await channel.send(view=MatchResultsButton(self.sheet))

        await interaction.followup.send("✅ Prompt sent.", ephemeral=True)

# Setup
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))
