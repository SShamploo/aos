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

class MatchResultsModal(discord.ui.Modal, title="📊 AOS MATCH RESULTS"):
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.match_type = discord.ui.TextInput(label="MATCH TYPE (OBJ, CB, CHALL, SCRIM, COMP)", required=True)
        self.league = discord.ui.TextInput(label="LEAGUE (HC or AL)", required=True)
        self.enemy_team = discord.ui.TextInput(label="ENEMY TEAM", required=True)
        self.map_played = discord.ui.TextInput(label="MAP", required=True)
        self.wl = discord.ui.TextInput(label="W/L", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map_played)
        self.add_item(self.wl)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        channel = discord.utils.get(interaction.guild.text_channels, name="results")

        embed = discord.Embed(title="📊 Match Report", color=discord.Color.red())
        embed.add_field(name="Match Type", value=self.match_type.value, inline=True)
        embed.add_field(name="League", value=self.league.value, inline=True)
        embed.add_field(name="Enemy Team", value=self.enemy_team.value, inline=True)
        embed.add_field(name="Map", value=self.map_played.value, inline=True)
        embed.add_field(name="W/L", value=self.wl.value, inline=True)
        embed.set_footer(text=f"Submitted by {user.name}", icon_url=user.display_avatar.url)

        image_link = "N/A"

        if channel:
            result_message = await channel.send(embed=embed)
            await interaction.response.send_message("📸 Please upload a screenshot to this channel.", ephemeral=True)

            def check(m):
                return m.author.id == user.id and m.channel == channel and m.attachments

            try:
                response = await interaction.client.wait_for("message", check=check, timeout=60)
                attachment = response.attachments[0]
                image_link = attachment.url
                await channel.send(file=await attachment.to_file())
                await response.delete()
            except Exception as e:
                print(f"⚠️ Screenshot upload failed: {e}")
        else:
            await interaction.response.send_message("❌ Could not find #results channel.", ephemeral=True)
            return

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.sheet.append_row([
                timestamp,
                str(user),
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map_played.value,
                self.wl.value,
                image_link
            ])
        except Exception as e:
            print(f"⚠️ Failed to log to Google Sheets: {e}")

class MatchResultsButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @app_commands.command(name="matchresultsprompt", description="Post the match results image + button.")
    async def matchresultsprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel
        try:
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await channel.send(file=file)
        await channel.send(view=MatchResultsButton(self.sheet))
        await interaction.followup.send("✅ Prompt sent.", ephemeral=True)

# Register the view and cog
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))
