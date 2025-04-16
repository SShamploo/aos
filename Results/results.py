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

class MatchResultsModal(discord.ui.Modal, title="📊 Submit Match Result"):
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.match_type = discord.ui.TextInput(
            label="Match Type (MUST BE: OBJ, CB, CHALL, SCRIM, COMP)",
            required=True
        )
        self.league = discord.ui.TextInput(
            label="League (MUST BE: HC or AL)",
            required=True
        )
        self.win_loss = discord.ui.TextInput(
            label="Win/Loss (MUST BE: W or L)",
            required=True
        )
        self.enemy_team = discord.ui.TextInput(
            label="Enemy Team",
            required=True
        )
        self.map_played = discord.ui.TextInput(
            label="Map Played",
            required=True
        )
        self.final_score = discord.ui.TextInput(
            label="Final Score (e.g., 13-9)",
            required=True
        )
        self.screenshot_url = discord.ui.TextInput(
            label="Screenshot URL (optional)",
            required=False
        )

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.win_loss)
        self.add_item(self.enemy_team)
        self.add_item(self.map_played)
        self.add_item(self.final_score)
        self.add_item(self.screenshot_url)

    async def on_submit(self, interaction: discord.Interaction):
        user_name = str(interaction.user)

        embed = discord.Embed(title="📊 Match Report", color=discord.Color.red())
        embed.add_field(name="Match Type", value=self.match_type.value.strip(), inline=False)
        embed.add_field(name="League", value=self.league.value.strip(), inline=False)
        embed.add_field(name="Enemy Team", value=self.enemy_team.value.strip(), inline=False)
        embed.add_field(name="Map", value=self.map_played.value.strip(), inline=False)
        embed.add_field(name="W/L", value=self.win_loss.value.strip(), inline=True)
        embed.add_field(name="Final Score", value=self.final_score.value.strip(), inline=True)
        embed.set_footer(text=f"Submitted by {user_name}", icon_url=interaction.user.display_avatar.url)

        screenshot = self.screenshot_url.value.strip()
        if screenshot.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
            embed.set_image(url=screenshot)

        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if results_channel:
            await results_channel.send(embed=embed)
        else:
            await interaction.response.send_message("❌ Could not find a #results channel.", ephemeral=True)
            return

        try:
            self.sheet.append_row([
                user_name,
                self.match_type.value.strip(),
                self.league.value.strip(),
                self.enemy_team.value.strip(),
                self.map_played.value.strip(),
                self.win_loss.value.strip(),
                self.final_score.value.strip(),
                screenshot if screenshot else "N/A"
            ])
        except Exception as e:
            print(f"⚠️ Failed to log to Google Sheets: {e}")

        await interaction.response.send_message("✅ Match submitted!", ephemeral=True)

class MatchResultsButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(
        label="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀AOS MATCH RESULTS⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
        style=discord.ButtonStyle.danger,
        custom_id="match_results_button"
    )
    async def launch_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @app_commands.command(name="matchresultprompt", description="Post the match results prompt + button.")
    async def matchresultprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel

        try:
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Could not clean old prompts: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "matchresults.jpg")
        file = discord.File(fp=image_path, filename="matchresults.jpg")
        await channel.send(file=file)
        await channel.send(view=MatchResultsButton(self.sheet))
        await interaction.followup.send("✅ Match result prompt sent.", ephemeral=True)

async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))
