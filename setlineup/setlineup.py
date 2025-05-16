
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

class ShooterSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="Select up to 6 Shooters", min_values=1, max_values=6, custom_id="shooters")
        self.selected_users = []

    async def callback(self, interaction: discord.Interaction):
        self.selected_users = self.values
        await interaction.response.defer()

class SubSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="Select up to 2 Subs", min_values=0, max_values=2, custom_id="subs")
        self.selected_users = []

    async def callback(self, interaction: discord.Interaction):
        self.selected_users = self.values
        await interaction.response.defer()

class SubmitCompactButton(discord.ui.Button):
    def __init__(self, match_row, emoji_map, sheet, shooter_dropdown, sub_dropdown, match_id):
        super().__init__(label="✅ Submit Lineup", style=discord.ButtonStyle.success)
        self.match_row = match_row
        self.emoji_map = emoji_map
        self.sheet = sheet
        self.shooter_dropdown = shooter_dropdown
        self.sub_dropdown = sub_dropdown
        self.match_id = match_id

    async def callback(self, interaction: discord.Interaction):
        shooters = self.shooter_dropdown.selected_users
        subs = self.sub_dropdown.selected_users

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
        shooters_lines = "\n".join([f"{self.emoji_map['ShadowJam']} {user.mention}" for user in shooters])
        subs_lines = (
            "\n".join([f"{self.emoji_map['Weed_Gold']} {user.mention}" for user in subs])
            if subs else f"{self.emoji_map['Weed_Gold']} None"
        )

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
        shooter_names = [user.display_name for user in shooters] + [""] * (6 - len(shooters))
        sub_names = [user.display_name for user in subs] + [""] * (2 - len(subs))

        row = [timestamp, self.match_id, enemy_team, league] + shooter_names + sub_names
        row += [str(sent_msg.id), str(interaction.channel.id)]

        all_rows = self.sheet.get_all_values()
        to_delete = [i for i, row in enumerate(all_rows[1:], start=2) if row[1] == str(self.match_id)]
        for idx in reversed(to_delete):
            self.sheet.delete_rows(idx)

        self.sheet.append_row(row)
        await interaction.response.send_message("✅ Lineup submitted and posted!", ephemeral=True)

class CompactLineupView(discord.ui.View):
    def __init__(self, match_row, emoji_map, sheet, match_id):
        super().__init__(timeout=300)
        shooter_dd = ShooterSelect()
        sub_dd = SubSelect()
        self.add_item(shooter_dd)
        self.add_item(sub_dd)
        self.add_item(SubmitCompactButton(match_row, emoji_map, sheet, shooter_dd, sub_dd, match_id))

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

            view = CompactLineupView(match_row, emoji_map, self.lineup_sheet, match_id)
            await interaction.response.send_message("🎯 Select up to 6 Shooters and 2 Subs:", view=view, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SetLineup(bot))
