
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
        try:
            # Defer safely and ensure no interaction timeout
            await interaction.response.defer(thinking=True)

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
            existing_rows = self.sheet.get_all_values()
            match_id = len(existing_rows)

            capo_role = discord.utils.get(interaction.guild.roles, name="Capo")
            soldier_role = discord.utils.get(interaction.guild.roles, name="Soldier")
            capo_mention = capo_role.mention if capo_role else "@CAPO"
            soldier_mention = soldier_role.mention if soldier_role else "@SOLDIER"
            message = (
                f"# **<:AOSgold:1350641872531624049> AOS CURRENT MATCHES {capo_mention} {soldier_mention} <:AOSgold:1350641872531624049>**\n\n"
                + f"# **AL LEAGUE MATCHES:**\n" + format_matches(al_matches) + "\n\n"
                + f"# **HC LEAGUE MATCHES:**\n" + format_matches(hc_matches)
            )
            await channel.send(message)
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
                match_id
            ])
        except Exception as e:
            try:
                await interaction.followup.send(f"❌ An error occurred: {e}", ephemeral=True)
            except:
                pass

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

    @app_commands.command(name="currentmatches", description="View all current AL and HC matches.")
    async def currentmatches(self, interaction: discord.Interaction):
        try:
            # Defer safely and ensure no interaction timeout
            await interaction.response.defer(thinking=True)
            rows = self.sheet.get_all_values()[1:]

            def parse_date_time(row):
                try:
                    dt_str = f"{row[2]} {row[3].strip().upper()}"
                    return datetime.strptime(dt_str, "%m/%d %I%p")
                except:
                    return datetime.min

            al_matches = sorted([row for row in rows if row[5].strip().upper() == "AL"], key=parse_date_time, reverse=False)
            hc_matches = sorted([row for row in rows if row[5].strip().upper() == "HC"], key=parse_date_time, reverse=False)

            def format_matches(match_list):
                return "\n".join([
                    f"**<a:flighttounge:1372704594072965201> {row[2]} | {row[3]} | {row[4]} | {row[6]} | {row[7]} | ID: {row[8]}**"
                    for row in match_list
                ]) or "No matches found."

            capo_role = discord.utils.get(interaction.guild.roles, name="Capo")
            soldier_role = discord.utils.get(interaction.guild.roles, name="Soldier")
            capo_mention = capo_role.mention if capo_role else "@CAPO"
            soldier_mention = soldier_role.mention if soldier_role else "@SOLDIER"
            message = (
                f"# **<:AOSgold:1350641872531624049> AOS CURRENT MATCHES {capo_mention} {soldier_mention} <:AOSgold:1350641872531624049>**\n\n"
                + f"# **AL LEAGUE MATCHES:**\n" + format_matches(al_matches) + "\n\n"
                + f"# **HC LEAGUE MATCHES:**\n" + format_matches(hc_matches)
            )
            )
            await interaction.followup.send(message)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to fetch matches: {e}", ephemeral=True)

# Setup
async def setup(bot):
    await bot.add_cog(MatchScheduler(bot))
