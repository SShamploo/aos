
import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class LineupTextModal(discord.ui.Modal, title="Enter Lineup Names"):
    def __init__(self, match_row, emoji_map, match_id, sheet):
        super().__init__(timeout=None)
        self.match_row = match_row
        self.emoji_map = emoji_map
        self.match_id = match_id
        self.sheet = sheet

        self.shooters_input = discord.ui.TextInput(
            label="Shooters (comma-separated)", placeholder="e.g. Name1, Name2, Name3", required=True, style=discord.TextStyle.paragraph)
        self.subs_input = discord.ui.TextInput(
            label="Subs (comma-separated)", placeholder="e.g. Sub1, Sub2", required=False, style=discord.TextStyle.paragraph)

        self.add_item(self.shooters_input)
        self.add_item(self.subs_input)

    async def on_submit(self, interaction: discord.Interaction):
        shooters = [s.strip() for s in self.shooters_input.value.split(",") if s.strip()]
        subs = [s.strip() for s in self.subs_input.value.split(",") if s.strip()]
        league = self.match_row[5]

        role_name = "Capo" if league == "HC" else "Soldier"
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        role_mention = role.mention if role else f"@{role_name}"

        match_line = (
            f"# {self.emoji_map['AOSgold']} {self.match_row[2]} | {self.match_row[3]} | {self.match_row[4]} | "
            f"{self.match_row[5]} | {self.match_row[6]} | ID: {self.match_row[8]} {role_mention}"
        )

        d9_line = self.emoji_map["D9"] * 10
        shooters_lines = "\n".join([f"{self.emoji_map['ShadowJam']} {name}" for name in shooters])
        subs_lines = "\n".join([f"{self.emoji_map['Weed_Gold']} {name}" for name in subs]) if subs else f"{self.emoji_map['Weed_Gold']} None"

        message = (
            f"{match_line}\n"
            f"{d9_line}\n**Shooters:**\n"
            f"{shooters_lines}\n"
            f"{d9_line}\n**Subs:**\n"
            f"{subs_lines}\n"
            f"{d9_line}"
        )

        sent_msg = await interaction.response.send_message(message)

        timestamp = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        match_id = str(self.match_id)
        enemy_team = self.match_row[4]

        shooters += [""] * (6 - len(shooters))
        subs += [""] * (2 - len(subs))

        row = [timestamp, match_id, enemy_team, league] + shooters[:6] + subs[:2]
        row += [str(sent_msg.id), str(interaction.channel.id)]

        all_rows = self.sheet.get_all_values()
        to_delete = [i for i, row in enumerate(all_rows[1:], start=2) if row[1] == match_id]
        for idx in reversed(to_delete):
            self.sheet.delete_rows(idx)

        self.sheet.append_row(row)

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
        try:
            data = self.match_sheet.get_all_values()
            rows = data[1:]
            match_row = next((row for row in rows if row[-1] == str(match_id)), None)

            if not match_row:
                await interaction.response.send_message("❌ Match ID not found.", ephemeral=True)
                return

            emoji_map = {}
            for name in ["AOSgold", "D9", "ShadowJam", "Weed_Gold"]:
                emoji = discord.utils.get(interaction.guild.emojis, name=name)
                emoji_map[name] = str(emoji) if emoji else f":{name}:"

            await interaction.response.send_modal(LineupTextModal(match_row, emoji_map, match_id, self.lineup_sheet))

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetLineup(bot))
