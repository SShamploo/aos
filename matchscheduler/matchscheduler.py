
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
    def __init__(self, league, match_type, players, sheet, archive_sheet):
        super().__init__(timeout=None)
        self.league = league
        self.match_type = match_type
        self.players = players
        self.sheet = sheet
        self.archive_sheet = archive_sheet

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

            archive_ids = self.archive_sheet.col_values(9)[1:]
            last_id = max([int(i) for i in archive_ids if i.isdigit()] or [0])
            match_id = last_id + 1

            message = (
                f"# {emoji_str} {self.date.value} | {self.time.value} | "
                f"{self.enemy_team.value} | {self.league} | {self.match_type} | {self.players} | ID: {match_id} {role_mention}"
            )

            sent_msg = await channel.send(message)
            await interaction.followup.send("✅ Match scheduled successfully!", ephemeral=True)

            new_row = [
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
            ]

            self.sheet.append_row(new_row)
            self.archive_sheet.append_row(new_row)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

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
        self.archive_sheet = self.client.open("AOS").worksheet("matcharchive")
        self.lineup_sheet = self.client.open("AOS").worksheet("lineups")

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
    async def schedulematch(self, interaction: discord.Interaction, league: app_commands.Choice[str], match_type: app_commands.Choice[str], players: app_commands.Choice[str]):
        await interaction.response.send_modal(MatchScheduleModal(league.value, match_type.value, players.value, self.sheet, self.archive_sheet))

    @app_commands.command(name="deletelineup", description="Delete a lineup by Match ID")
    async def deletelineup(self, interaction: discord.Interaction, match_id: int):
        await interaction.response.defer(ephemeral=True)
        try:
            values = self.lineup_sheet.get_all_values()
            headers = values[0]
            id_index = headers.index("Match ID")
            msg_index = headers.index("message id")
            chan_index = headers.index("channel id")
            target_row = None
            for idx, row in enumerate(values[1:], start=2):
                if row[id_index] == str(match_id):
                    target_row = idx
                    msg_id = int(row[msg_index])
                    chan_id = int(row[chan_index])
                    break

            if target_row:
                self.lineup_sheet.delete_rows(target_row)
                channel = self.bot.get_channel(chan_id)
                if channel:
                    try:
                        msg = await channel.fetch_message(msg_id)
                        await msg.delete()
                    except:
                        pass
                await interaction.followup.send(f"✅ Lineup for Match ID {match_id} deleted.", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ No lineup found for Match ID {match_id}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(MatchScheduler(bot))
