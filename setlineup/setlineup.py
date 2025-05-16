
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

class LineupDropdown(discord.ui.UserSelect):
    def __init__(self, label):
        super().__init__(placeholder=label, min_values=1, max_values=1, custom_id=label)
        self.selected_user = None

    async def callback(self, interaction: discord.Interaction):
        self.selected_user = self.values[0]
        await interaction.response.defer()

class SubmitLineupButton(discord.ui.Button):
    def __init__(self, match_row, emoji_map, sheet, dropdowns, match_id):
        super().__init__(label="✅ Submit Lineup", style=discord.ButtonStyle.success)
        self.match_row = match_row
        self.emoji_map = emoji_map
        self.sheet = sheet
        self.dropdowns = dropdowns
        self.match_id = match_id

    async def callback(self, interaction: discord.Interaction):
        shooters = []
        subs = []

        for dd in self.dropdowns:
            selected = dd.selected_user
            if "Shooter" in dd.placeholder:
                shooters.append(selected.display_name if selected else "")
            elif "Sub" in dd.placeholder:
                subs.append(selected.display_name if selected else "")

        shooters += [""] * (6 - len(shooters))
        subs += [""] * (2 - len(subs))

        league = self.match_row[5]
        enemy_team = self.match_row[4]

        role_name = "Capo" if league == "HC" else "Soldier"
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        role_mention = role.mention if role else f"@{role_name}"

        match_line = (
            f"# {self.emoji_map['AOSgold']} {self.match_row[2]} | {self.match_row[3]} | {self.match_row[4]} | "
            f"{self.match_row[5]} | {self.match_row[6]} | ID: {self.match_row[8]} {role_mention}"
        )

        d9_line = self.emoji_map["D9"] * 10
        shooters_lines = "\n".join([f"{self.emoji_map['ShadowJam']} {name}" for name in shooters])
        subs_lines = "\n".join([f"{self.emoji_map['Weed_Gold']} {name}" for name in subs]) if any(subs) else f"{self.emoji_map['Weed_Gold']} None"

        message = (
            f"{match_line}\n"
            f"{d9_line}\n**Shooters:**\n"
            f"{shooters_lines}\n"
            f"{d9_line}\n**Subs:**\n"
            f"{subs_lines}\n"
            f"{d9_line}"
        )

        sent_msg = await interaction.channel.send(message)

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, self.match_id, enemy_team, league] + shooters[:6] + subs[:2]
        row += [str(sent_msg.id), str(interaction.channel.id)]

        all_rows = self.sheet.get_all_values()
        to_delete = [i for i, row in enumerate(all_rows[1:], start=2) if row[1] == str(self.match_id)]
        for idx in reversed(to_delete):
            self.sheet.delete_rows(idx)

        self.sheet.append_row(row)
        await interaction.response.send_message("✅ Lineup submitted and posted!", ephemeral=True)

class LineupView(discord.ui.View):
    def __init__(self, match_row, emoji_map, sheet, match_id):
        super().__init__(timeout=300)
        self.dropdowns = []

        for i in range(6):
            dd = LineupDropdown(f"Shooter {i+1}")
            self.dropdowns.append(dd)
            self.add_item(dd)

        for i in range(2):
            dd = LineupDropdown(f"Sub {i+1}")
            self.dropdowns.append(dd)
            self.add_item(dd)

        self.add_item(SubmitLineupButton(match_row, emoji_map, sheet, self.dropdowns, match_id))

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
    async def setlineup(self, interaction: discord.Interaction, match_id: int):
        try:
            data = self.match_sheet.get_all_values()
            rows = data[1:]
            match_row = next((row for row in rows if row[8] == str(match_id)), None)

            if not match_row:
                await interaction.response.send_message("❌ Match ID not found.", ephemeral=True)
                return

            emoji_map = {}
            for name in ["AOSgold", "D9", "ShadowJam", "Weed_Gold"]:
                emoji = discord.utils.get(interaction.guild.emojis, name=name)
                emoji_map[name] = str(emoji) if emoji else f":{name}:"

            view = LineupView(match_row, emoji_map, self.lineup_sheet, match_id)
            await interaction.response.send_message("🎯 Select Shooters and Subs below:", view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetLineup(bot))
