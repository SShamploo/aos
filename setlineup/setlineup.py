
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class LineupModal(discord.ui.Modal):
    def __init__(self, match_row, emoji_map, player_count, sheet, match_id):
        super().__init__(title="Enter Player Names", timeout=None)
        self.match_row = match_row
        self.emoji_map = emoji_map
        self.sheet = sheet
        self.match_id = match_id
        self.player_inputs = []

        for i in range(player_count):
            player_input = discord.ui.TextInput(label=f"Player {i + 1}", required=True)
            self.add_item(player_input)
            self.player_inputs.append(player_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            match_line = (
                f"# {self.emoji_map['AOSgold']} {self.match_row[2]} | {self.match_row[3]} | {self.match_row[4]} | "
                f"{self.match_row[5]} | {self.match_row[6]} | ID: {self.match_row[-1]}"
            )

            d9_line = self.emoji_map["D9"] * 10
            shooters = "\n".join([f"{self.emoji_map['ShadowJam']} {input.value}" for input in self.player_inputs])
            subs = "\n".join([f"{self.emoji_map['Weed_Gold']} Sub1", f"{self.emoji_map['Weed_Gold']} Sub2"])

            message = (
                f"{match_line}\n"
                f"{d9_line}\n**Shooters:**\n"
                f"{shooters}\n"
                f"{d9_line}\n**Subs:**\n"
                f"{subs}\n{d9_line}"
            )

            await interaction.response.send_message(message)

            timestamp = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            for i, input in enumerate(self.player_inputs):
                self.sheet.append_row([
                    timestamp,
                    self.match_id,
                    f"Player {i + 1}",
                    input.value
                ])

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

class SetLineup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.match_sheet = self.client.open("AOS").worksheet("matches")
        self.lineup_sheet = self.client.open("AOS").worksheet("lineups")

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
        await interaction.response.defer(thinking=True)

        try:
            data = self.match_sheet.get_all_values()
            rows = data[1:]
            match_row = next((row for row in rows if row[-1] == str(match_id)), None)

            if not match_row:
                await interaction.followup.send("❌ Match ID not found.")
                return

            player_count = {
                "4v4": 4,
                "5v5": 5,
                "5v5+": 6,
                "6v6": 6
            }.get(lineup_type.value, 5)

            # Fetch emojis
            emoji_map = {}
            for name in ["AOSgold", "D9", "ShadowJam", "Weed_Gold"]:
                emoji = discord.utils.get(interaction.guild.emojis, name=name)
                emoji_map[name] = str(emoji) if emoji else f":{name}:"

            await interaction.followup.send("📋 Please enter player names...", ephemeral=True)
            await interaction.response.send_modal(LineupModal(match_row, emoji_map, player_count, self.lineup_sheet, match_id))

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(SetLineup(bot))
