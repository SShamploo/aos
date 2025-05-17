
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

class MatchScheduleModal(discord.ui.Modal, title="📆 Schedule a Match"):
    def __init__(self, league, match_type, players, sheet):
        super().__init__(timeout=None)
        self.league = league
        self.match_type = match_type
        self.players = players
        self.sheet = sheet

        self.date = discord.ui.TextInput(label="Date", placeholder="MM/DD", required=True)
        self.time = discord.ui.TextInput(label="Time", placeholder="e.g., 7PM, 8PM", required=True)
        self.enemy_team = discord.ui.TextInput(label="Enemy Team", placeholder="Enter team name", required=True)

        self.add_item(self.date)
        self.add_item(self.time)
        self.add_item(self.enemy_team)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            channel = interaction.guild.get_channel(1360237474454175814)
            if not channel:
                await interaction.followup.send("❌ Could not find the match schedule channel.", ephemeral=True)
                return

            emoji = discord.utils.get(interaction.guild.emojis, name="AOSgold")
            emoji_str = f"<:{emoji.name}:{emoji.id}>" if emoji else "🟡"

            role_name = "Capo" if self.league == "HC" else "Soldier"
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            role_mention = role.mention if role else f"@{role_name}"

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Use matcharchive to determine next Match ID
            archive_sheet = self.sheet.spreadsheet.worksheet("matcharchive")
            archive_ids = archive_sheet.col_values(9)[1:]  # Skip header
            match_id = max([int(i) for i in archive_ids if i.isdigit()] or [0]) + 1
            meta_sheet = self.sheet.spreadsheet.worksheet("meta")
            last_id = int(meta_sheet.acell("A2").value or 0)
            match_id = last_id + 1
            meta_sheet.update("A2", str(match_id))

            message = (
                f"# {emoji_str} {self.date.value} | {self.time.value} | "
                f"{self.enemy_team.value} | {self.league} | {self.match_type} | {self.players} | ID: {match_id} {role_mention}"
            )

            sent_msg = await channel.send(message)
            await interaction.followup.send("✅ Match scheduled successfully!", ephemeral=True)

            self.sheet.append_row([
                timestamp,
                str(interaction.user),
                self.date.value,
                self.time.value,
                self.enemy_team.value,
                self.league,
                self.match_type,
                self.players,
                match_id,
                str(sent_msg.id),
                str(sent_msg.channel.id)
            ])

            archive_sheet.append_row([
                timestamp,
                str(interaction.user),
                self.date.value,
                self.time.value,
                self.enemy_team.value,
                self.league,
                self.match_type,
                self.players,
                match_id,
                str(sent_msg.id),
                str(sent_msg.channel.id)
            ])
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Failed to schedule match: {e}", ephemeral=True)

class MatchScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matches")

    @app_commands.command(name="schedulematch", description="Schedule a match and notify the team.")
    @app_commands.choices(
        league=[
            app_commands.Choice(name="HC", value="HC"),
            app_commands.Choice(name="AL", value="AL"),
        ],
        match_type=[
            app_commands.Choice(name="OBJ", value="OBJ"),
            app_commands.Choice(name="CB", value="CB"),
            app_commands.Choice(name="CHALL", value="CHALL"),
            app_commands.Choice(name="SCRIM", value="SCRIM"),
            app_commands.Choice(name="COMP", value="COMP"),
        ],
        players=[
            app_commands.Choice(name="4v4", value="4v4"),
            app_commands.Choice(name="4v4+", value="4v4+"),
            app_commands.Choice(name="5v5", value="5v5"),
            app_commands.Choice(name="5v5+", value="5v5+"),
            app_commands.Choice(name="6v6", value="6v6"),
        ]
    )
    async def schedulematch(
        self,
        interaction: discord.Interaction,
        league: app_commands.Choice[str],
        match_type: app_commands.Choice[str],
        players: app_commands.Choice[str]
    ):
        await interaction.response.send_modal(MatchScheduleModal(league.value, match_type.value, players.value, self.sheet))

# Setup
async def setup(bot):
    await bot.add_cog(MatchScheduler(bot))
