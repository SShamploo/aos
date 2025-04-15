print("📦 Importing Results Cog...")
import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Load environment variables from the .env file
        load_dotenv()

        # Setup Google Sheets API using base64-decoded credentials
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_bytes = base64.b64decode(creds_b64.encode("utf-8"))
        creds_json = json.loads(creds_bytes.decode("utf-8"))

        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="results", description="Submit a match report")
    @app_commands.describe(
        match_type="Select match type",
        league="Select league",
        enemy_team="Enemy team name",
        map_played="Map played",
        win_loss="Match result (Win/Loss)",
        final_score="e.g., 13-9"
    )
    @app_commands.choices(
        match_type=[
            app_commands.Choice(name="OBJ", value="OBJ"),
            app_commands.Choice(name="CB", value="CB"),
            app_commands.Choice(name="CHALL", value="CHALL"),
            app_commands.Choice(name="SCRIM", value="SCRIM"),
            app_commands.Choice(name="COMP", value="COMP"),
        ],
        league=[
            app_commands.Choice(name="HC", value="HC"),
            app_commands.Choice(name="AL", value="AL"),
        ],
        win_loss=[
            app_commands.Choice(name="W", value="W"),
            app_commands.Choice(name="L", value="L"),
        ]
    )
    async def results(
        self,
        interaction: discord.Interaction,
        match_type: app_commands.Choice[str],
        league: app_commands.Choice[str],
        enemy_team: str,
        map_played: str,
        win_loss: app_commands.Choice[str],
        final_score: str
    ):
        user_name = str(interaction.user)

        embed = discord.Embed(title="📊 Match Report", color=discord.Color.blurple())
        embed.add_field(name="Match Type", value=match_type.value, inline=False)
        embed.add_field(name="League", value=league.value, inline=False)
        embed.add_field(name="Enemy Team", value=enemy_team, inline=False)
        embed.add_field(name="Map", value=map_played, inline=False)
        embed.add_field(name="W/L", value=win_loss.value, inline=True)
        embed.add_field(name="Final Score", value=final_score, inline=True)
        embed.set_footer(text=f"Submitted by {user_name}", icon_url=interaction.user.display_avatar.url)

        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if results_channel:
            await results_channel.send(embed=embed)
            await interaction.response.send_message("✅ Match report sent to #results!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Could not find a #results channel.", ephemeral=True)

        try:
            self.sheet.append_row([
                user_name,
                match_type.value,
                league.value,
                enemy_team,
                map_played,
                win_loss.value,
                final_score
            ])
        except Exception as e:
            print(f"⚠️ Failed to log to Google Sheets: {e}")

# Required async setup
async def setup(bot):
    await bot.add_cog(MatchResults(bot))
