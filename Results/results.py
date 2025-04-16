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
            label="League (MUST BE: HC or AL)",
            required=True
        )
        self.match_type_and_result = discord.ui.TextInput(
            label="Match Type + W/L (MUST BE: OBJ/CB/CHALL/SCRIM/COMP and W or L, e.g. OBJ W)",
            required=True
        )
        self.enemy_team = discord.ui.TextInput(
            label="Enemy Team",
            required=True
        )
        self.map_and_score = discord.ui.TextInput(
            label="Map + Final Score (e.g., Hotel 13-9)",
            required=True
        )
        self.screenshot_url = discord.ui.TextInput(
            label="Screenshot URL (optional)",
            required=False
        )

        self.add_item(self.league)
        self.add_item(self.match_type_and_result)
        self.add_item(self.enemy_team)
        self.add_item(self.map_and_score)
        self.add_item(self.screenshot_url)

    async def on_submit(self, interaction: discord.Interaction):
        user_name = str(interaction.user)
        league = self.league.value.strip()
        match_type_result = self.match_type_and_result.value.strip()
        enemy_team = self.enemy_team.value.strip()
        map_score = self.map_and_score.value.strip()
        screenshot = self.screenshot_url.value.strip()

        try:
            # Parse match_type and win_loss from combined input
            parts = match_type_result.split()
            match_type = parts[0] if len(parts) > 0 else "UNKNOWN"
            win_loss = parts[1] if len(parts) > 1 else "UNKNOWN"

            map_played = " ".join(map_score.split()[:-1])
            final_score = map_score.split()[-1]

            embed = discord.Embed(title="📊 Match Report", color=discord.Color.red())
            embed.add_field(name="Match Type", value=match_type, inline=True)
            embed.add_field(name="League", value=league, inline=True)
            embed.add_field(name="Enemy Team", value=enemy_team, inline=False)
            embed.add_field(name="Map", value=map_played, inline=True)
            embed.add_field(name="W/L", value=win_loss, inline=True)
            embed.add_field(name="Final Score", value=final_score, inline=True)
            embed.set_footer(text=f"Submitted by {user_name}", icon_url=interaction.user.display_avatar.url)

            if screenshot.lower().endswith((".jpg", ".png", ".gif", ".jpeg")):
                embed.set_image(url=screenshot)

            results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
            if results_channel:
                await results_channel.send(embed=embed)
            else:
                await interaction.response.send_message("❌ Could not find #results channel.", ephemeral=True)
                return

            # Log to Google Sheets
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
            print(f"⚠️ Submission failed: {e}")
            await interaction.response.send_message("❌ There was an error processing your match report.", ephemeral=True)

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
