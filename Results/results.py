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

        self.enemy_team = discord.ui.TextInput(label="Enemy Team", required=True, placeholder="Team name")
        self.map_played = discord.ui.TextInput(label="Map Played", required=True, placeholder="Map name")
        self.final_score = discord.ui.TextInput(label="Final Score", required=True, placeholder="e.g. 13-9")
        self.screenshot_url = discord.ui.TextInput(label="Screenshot URL (optional)", required=False, placeholder="Paste image link")

        self.add_item(self.enemy_team)
        self.add_item(self.map_played)
        self.add_item(self.final_score)
        self.add_item(self.screenshot_url)

        self.match_type = discord.ui.Select(
            placeholder="Match Type",
            options=[
                discord.SelectOption(label="OBJ", value="OBJ"),
                discord.SelectOption(label="CB", value="CB"),
                discord.SelectOption(label="CHALL", value="CHALL"),
                discord.SelectOption(label="SCRIM", value="SCRIM"),
                discord.SelectOption(label="COMP", value="COMP")
            ]
        )
        self.league = discord.ui.Select(
            placeholder="League",
            options=[
                discord.SelectOption(label="HC", value="HC"),
                discord.SelectOption(label="AL", value="AL")
            ]
        )
        self.win_loss = discord.ui.Select(
            placeholder="Win or Loss",
            options=[
                discord.SelectOption(label="W", value="W"),
                discord.SelectOption(label="L", value="L")
            ]
        )

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.win_loss)

    async def on_submit(self, interaction: discord.Interaction):
        user_name = str(interaction.user)
        match_type = self.match_type.values[0]
        league = self.league.values[0]
        win_loss = self.win_loss.values[0]
        screenshot = self.screenshot_url.value.strip()

        embed = discord.Embed(title="📊 Match Report", color=discord.Color.red())
        embed.add_field(name="Match Type", value=match_type, inline=False)
        embed.add_field(name="League", value=league, inline=False)
        embed.add_field(name="Enemy Team", value=self.enemy_team.value, inline=False)
        embed.add_field(name="Map", value=self.map_played.value, inline=False)
        embed.add_field(name="W/L", value=win_loss, inline=True)
        embed.add_field(name="Final Score", value=self.final_score.value, inline=True)
        embed.set_footer(text=f"Submitted by {user_name}", icon_url=interaction.user.display_avatar.url)

        if screenshot and any(screenshot.lower().endswith(ext) for ext in [".jpg", ".png", ".gif"]):
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
                match_type,
                league,
                self.enemy_team.value,
                self.map_played.value,
                win_loss,
                self.final_score.value,
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
