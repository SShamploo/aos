
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

# Shared storage for context between modals
TEMP_LINEUPS = {}

class LineupModal1(discord.ui.Modal):
    def __init__(self, match_row, emoji_map, player_count, sheet, match_id, key):
        super().__init__(title="Enter Shooters (1/2)", timeout=None)
        self.match_row = match_row
        self.emoji_map = emoji_map
        self.sheet = sheet
        self.match_id = match_id
        self.player_count = player_count
        self.key = key
        self.player_inputs = []

        for i in range(min(player_count, 5)):
            field = discord.ui.TextInput(label=f"Player {i + 1}", required=True)
            self.add_item(field)
            self.player_inputs.append(field)

    async def on_submit(self, interaction: discord.Interaction):
        names = [f"{self.emoji_map['ShadowJam']} {field.value}" for field in self.player_inputs]
        TEMP_LINEUPS[self.key] = {
            "match_row": self.match_row,
            "emoji_map": self.emoji_map,
            "shooters": names,
            "sheet": self.sheet,
            "match_id": self.match_id,
            "player_count": self.player_count
        }

        if self.player_count > 5:
            await interaction.response.send_modal(LineupModal2(self.key))
        else:
            await finalize_lineup(interaction, self.key)

class LineupModal2(discord.ui.Modal, title="Enter Shooters (2/2) + Subs"):
    def __init__(self, key):
        super().__init__(timeout=None)
        self.key = key
        self.player6 = discord.ui.TextInput(label="Player 6", required=True)
        self.sub1 = discord.ui.TextInput(label="Sub 1", required=True)
        self.sub2 = discord.ui.TextInput(label="Sub 2", required=True)
        self.add_item(self.player6)
        self.add_item(self.sub1)
        self.add_item(self.sub2)

    async def on_submit(self, interaction: discord.Interaction):
        ctx = TEMP_LINEUPS.get(self.key)
        if not ctx:
            await interaction.response.send_message("❌ Context expired.", ephemeral=True)
            return

        ctx["shooters"].append(f"{ctx['emoji_map']['ShadowJam']} {self.player6.value}")
        ctx["subs"] = [
            f"{ctx['emoji_map']['Weed_Gold']} {self.sub1.value}",
            f"{ctx['emoji_map']['Weed_Gold']} {self.sub2.value}"
        ]
        await finalize_lineup(interaction, self.key)

async def finalize_lineup(interaction: discord.Interaction, key: str):
    ctx = TEMP_LINEUPS.pop(key, None)
    if not ctx:
        await interaction.response.send_message("❌ Missing lineup data.", ephemeral=True)
        return

    match_line = (
        f"# {ctx['emoji_map']['AOSgold']} {ctx['match_row'][2]} | {ctx['match_row'][3]} | "
        f"{ctx['match_row'][4]} | {ctx['match_row'][5]} | {ctx['match_row'][6]} | ID: {ctx['match_row'][-1]}"
    )
    d9_line = ctx["emoji_map"]["D9"] * 10
    shooters = "\n".join(ctx["shooters"])
    subs = "\n".join(ctx.get("subs", [
        f"{ctx['emoji_map']['Weed_Gold']} Sub1",
        f"{ctx['emoji_map']['Weed_Gold']} Sub2"
    ]))

    message = (
        f"{match_line}\n"
        f"{d9_line}\n**Shooters:**\n"
        f"{shooters}\n"
        f"{d9_line}\n**Subs:**\n"
        f"{subs}\n{d9_line}"
    )

    await interaction.response.send_message(message)

    timestamp = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    sheet = ctx["sheet"]
    match_id = str(ctx["match_id"])
    all_rows = sheet.get_all_values()

    # Remove existing entries for this match ID
    to_delete = [i for i, row in enumerate(all_rows[1:], start=2) if row[1] == match_id]
    for idx in reversed(to_delete):
        sheet.delete_rows(idx)

    for i, line in enumerate(ctx["shooters"], 1):
        sheet.append_row([timestamp, match_id, f"Player {i}", line.split(' ', 1)[1]])
    for j, line in enumerate(ctx.get("subs", []), 1):
        sheet.append_row([timestamp, match_id, f"Sub {j}", line.split(' ', 1)[1]])

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

            emoji_map = {}
            for name in ["AOSgold", "D9", "ShadowJam", "Weed_Gold"]:
                emoji = discord.utils.get(interaction.guild.emojis, name=name)
                emoji_map[name] = str(emoji) if emoji else f":{name}:"

            key = f"{interaction.user.id}_{match_id}"
            await interaction.response.send_modal(LineupModal1(match_row, emoji_map, player_count, self.lineup_sheet, match_id, key))

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

async def setup(bot):
    await bot.add_cog(SetLineup(bot))
