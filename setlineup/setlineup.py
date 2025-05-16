
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

class LineupView(discord.ui.View):
    def __init__(self, match_row, emoji_map, match_id, sheet):
        super().__init__(timeout=300)
        self.match_row = match_row
        self.emoji_map = emoji_map
        self.match_id = match_id
        self.sheet = sheet
        self.selected_users = {}

        self.add_item(LineupDropdown("Lineup Type", ["4v4", "5v5", "5v5+", "6v6"], self, "lineup_type"))
        self.add_item(LineupInput("Match ID", self, "match_id"))
        for i in range(6):
            self.add_item(UserSelect(f"Shooter {i+1}", self, f"shooter_{i+1}"))
        for i in range(2):
            self.add_item(UserSelect(f"Sub {i+1}", self, f"sub_{i+1}"))
        self.add_item(SubmitLineupButton(self))

class LineupInput(discord.ui.TextInput):
    def __init__(self, label, view, key):
        super().__init__(label=label, required=True)
        self.view = view
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_users[self.key] = self.value

class LineupDropdown(discord.ui.Select):
    def __init__(self, placeholder, options, view, key):
        opts = [discord.SelectOption(label=o) for o in options]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=opts)
        self.view = view
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_users[self.key] = self.values[0]
        await interaction.response.defer()

class UserSelect(discord.ui.UserSelect):
    def __init__(self, placeholder, view, key):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1)
        self.view = view
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_users[self.key] = self.values[0].display_name
        await interaction.response.defer()

class SubmitLineupButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(label="Submit Lineup", style=discord.ButtonStyle.success)
        self.view = view

    async def callback(self, interaction: discord.Interaction):
        data = self.view.selected_users
        shooters = [data.get(f"shooter_{i+1}", "") for i in range(6)]
        subs = [data.get(f"sub_{i+1}", "") for i in range(2)]
        match_id = data.get("match_id")
        lineup_type = data.get("lineup_type")
        match_row = self.view.match_row
        sheet = self.view.sheet

        league = match_row[5]
        role_name = "Capo" if league == "HC" else "Soldier"
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        role_mention = role.mention if role else f"@{role_name}"

        match_line = (
            f"# {self.view.emoji_map['AOSgold']} {match_row[2]} | {match_row[3]} | {match_row[4]} | "
            f"{match_row[5]} | {match_row[6]} | ID: {match_row[8]} {role_mention}"
        )

        d9_line = self.view.emoji_map["D9"] * 10
        shooters_lines = "\n".join([f"{self.view.emoji_map['ShadowJam']} {name}" for name in shooters])
        subs_lines = "\n".join([f"{self.view.emoji_map['Weed_Gold']} {name}" for name in subs]) if any(subs) else f"{self.view.emoji_map['Weed_Gold']} None"

        message = (
            f"{match_line}\n"
            f"{d9_line}\n**Shooters:**\n"
            f"{shooters_lines}\n"
            f"{d9_line}\n**Subs:**\n"
            f"{subs_lines}\n"
            f"{d9_line}"
        )

        await interaction.response.send_message(message)
        sent_msg = await interaction.original_response()

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, match_id, match_row[4], league] + shooters + subs
        row += [str(sent_msg.id), str(interaction.channel.id)]

        all_rows = sheet.get_all_values()
        to_delete = [i for i, row in enumerate(all_rows[1:], start=2) if row[1] == match_id]
        for idx in reversed(to_delete):
            sheet.delete_rows(idx)

        sheet.append_row(row)

class SetLineup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
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

            await interaction.response.send_message("Please fill out the lineup:", view=LineupView(match_row, emoji_map, match_id, self.lineup_sheet), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetLineup(bot))
