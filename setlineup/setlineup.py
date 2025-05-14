
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class SetLineup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matches")

    @app_commands.command(name="setlineup", description="Post lineup for a scheduled match.")
    @app_commands.choices(
        lineup_type=[
            app_commands.Choice(name="4v4", value="4v4"),
            app_commands.Choice(name="5v5", value="5v5"),
            app_commands.Choice(name="5v5+", value="5v5+"),
            app_commands.Choice(name="6v6", value="6v6"),
        ]
    )
    async def setlineup(self, interaction: discord.Interaction, match_id: int, lineup_type: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        try:
            data = self.sheet.get_all_values()
            rows = data[1:]
            match_row = next((row for row in rows if row[-1] == str(match_id)), None)

            if not match_row:
                await interaction.followup.send("❌ Match ID not found.", ephemeral=True)
                return

            match_line = (
                f"# 🟡 {match_row[2]} | {match_row[3]} | {match_row[4]} | "
                f"{match_row[5]} | {match_row[6]} | ID: {match_row[-1]}"
            )

            shooter_count = {
                "4v4": 4,
                "5v5": 5,
                "5v5+": 6,
                "6v6": 6
            }.get(lineup_type.value, 5)

            # Fetch custom emojis from guild
            d9 = discord.utils.get(interaction.guild.emojis, name="D9")
            shadow = discord.utils.get(interaction.guild.emojis, name="ShadowJam")
            weed = discord.utils.get(interaction.guild.emojis, name="Weed_Gold")

            d9_str = str(d9) if d9 else ":D9:"
            shadow_str = str(shadow) if shadow else ":ShadowJam:"
            weed_str = str(weed) if weed else ":Weed_Gold:"

            shooters = "\n".join([shadow_str for _ in range(shooter_count)])
            subs = "\n".join([weed_str for _ in range(2)])

            message = (
                f"{match_line}\n"
                f"{d9_str}\n**Shooters:**\n"
                f"{shooters}\n"
                f"{d9_str}\n**Subs:**\n"
                f"{subs}\n{d9_str}"
            )

            await interaction.followup.send(message)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetLineup(bot))
