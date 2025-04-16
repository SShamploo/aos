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

class MatchResultsModal(discord.ui.Modal, title="📝 Submit Match Results"):
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.match_type = discord.ui.TextInput(label="Match Type", placeholder="OBJ / CB / CHALL / SCRIM / COMP", required=True)
        self.league = discord.ui.TextInput(label="League", placeholder="HC or AL", required=True)
        self.enemy_team = discord.ui.TextInput(label="Enemy Team", placeholder="Enter enemy team name", required=True)
        self.map_played = discord.ui.TextInput(label="Map Played", placeholder="Enter map name", required=True)
        self.win_loss = discord.ui.TextInput(label="W/L", placeholder="W or L", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map_played)
        self.add_item(self.win_loss)

    async def on_submit(self, interaction: discord.Interaction):
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.user_name = interaction.user.name
        self.user_id = interaction.user.id
        self.interaction = interaction

        channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if not channel:
            await interaction.response.send_message("❌ Could not find a #results channel.", ephemeral=True)
            return

        embed = discord.Embed(title="📊 Match Report", color=discord.Color.blurple())
        embed.add_field(name="Match Type", value=self.match_type.value, inline=True)
        embed.add_field(name="League", value=self.league.value, inline=True)
        embed.add_field(name="Enemy Team", value=self.enemy_team.value, inline=False)
        embed.add_field(name="Map", value=self.map_played.value, inline=True)
        embed.add_field(name="W/L", value=self.win_loss.value, inline=True)
        embed.set_footer(text=f"Submitted by {self.user_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.response.send_message("✅ Match results submitted! Please upload your screenshot now.", ephemeral=True)

        def check(m):
            return m.author.id == self.user_id and m.channel == interaction.channel and m.attachments

        try:
            msg = await interaction.client.wait_for("message", timeout=60.0, check=check)
            attachment = msg.attachments[0]
            screenshot_url = attachment.url

            # Post the embed first
            embed_message = await channel.send(embed=embed)

            # Then post the image directly below it (raw image, no caption)
            await channel.send(file=await attachment.to_file())
            await msg.delete()

            # Log to Google Sheets
            self.sheet.append_row([
                self.timestamp,
                self.user_name,
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map_played.value,
                self.win_loss.value,
                screenshot_url
            ])
        except Exception as e:
            print(f"⚠️ Error during screenshot upload or Google logging: {e}")

class MatchResultsView(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def match_results_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @app_commands.command(name="matchresultsprompt", description="Post the match results prompt.")
    async def matchresultsprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            async for msg in interaction.channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Failed to delete previous match results prompt: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await interaction.channel.send(file=file)
        await interaction.channel.send(view=MatchResultsView(self.sheet))

        await interaction.followup.send("✅ Match results prompt posted!", ephemeral=True)

async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsView(cog.sheet))
