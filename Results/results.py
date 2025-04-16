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

        self.league = discord.ui.TextInput(
            label="League (MUST BE: HC or AL)", required=True
        )
        self.match_type_and_result = discord.ui.TextInput(
            label="Match Type + W/L (e.g., OBJ W)", required=True
        )
        self.enemy_team = discord.ui.TextInput(
            label="Enemy Team", required=True
        )
        self.map_and_score = discord.ui.TextInput(
            label="Map + Final Score (e.g., Hotel 13-9)", required=True
        )
        self.screenshot_url = discord.ui.TextInput(
            label="Screenshot URL (optional)", required=False
        )

        self.add_item(self.league)
        self.add_item(self.match_type_and_result)
        self.add_item(self.enemy_team)
        self.add_item(self.map_and_score)
        self.add_item(self.screenshot_url)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_name = str(interaction.user)
            league = self.league.value.strip().upper()
            match_type_result = self.match_type_and_result.value.strip()
            enemy_team = self.enemy_team.value.strip()
            map_score = self.map_and_score.value.strip()
            screenshot = self.screenshot_url.value.strip()

            # ✅ Safely parse match type + W/L
            mt_parts = match_type_result.split()
            if len(mt_parts) == 2:
                match_type, win_loss = mt_parts
            else:
                match_type, win_loss = "UNKNOWN", "UNKNOWN"

            # ✅ Safely parse map + score
            ms_parts = map_score.rsplit(" ", 1)
            if len(ms_parts) == 2:
                map_played, final_score = ms_parts
            else:
                map_played, final_score = "UNKNOWN", "UNKNOWN"

            embed = discord.Embed(title="📊 Match Report", color=discord.Color.red())
            embed.add_field(name="Match Type", value=match_type, inline=True)
            embed.add_field(name="League", value=league, inline=True)
            embed.add_field(name="Enemy Team", value=enemy_team, inline=False)
            embed.add_field(name="Map", value=map_played, inline=True)
            embed.add_field(name="W/L", value=win_loss, inline=True)
            embed.add_field(name="Final Score", value=final_score, inline=True)
            embed.set_footer(text=f"Submitted by {user_name}", icon_url=interaction.user.display_avatar.url)

            if screenshot and screenshot.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                embed.set_image(url=screenshot)

            results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
            if results_channel:
                await results_channel.send(embed=embed)
            else:
                await interaction.response.send_message("❌ Could not find a #results channel.", ephemeral=True)
                return

            self.sheet.append_row([
                user_name,
                match_type,
                league,
                enemy_team,
                map_played,
                win_loss,
                final_score,
                screenshot if screenshot else "N/A"
            ])

            await interaction.response.send_message("✅ Match submitted!", ephemeral=True)

        except Exception as e:
            print(f"⚠️ Modal error: {e}")
            await interaction.response.send_message("❌ Error submitting match.", ephemeral=True)

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

        try:
            async for msg in interaction.channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Cleanup failed: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await interaction.channel.send(file=file)
        await interaction.channel.send(view=MatchResultsButton(self.sheet))
        await interaction.followup.send("✅ Match result prompt sent.", ephemeral=True)

async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.sheet))  # 🔒 Required for persistent view
