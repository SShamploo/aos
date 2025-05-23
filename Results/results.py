print("📦 Importing Results Cog...")

import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from collections import defaultdict

class MatchResultsModal(discord.ui.Modal, title="AOS MATCH RESULTS"):
    def __init__(self, match_sheet, result_sheet):
        super().__init__()
        self.match_sheet = match_sheet
        self.result_sheet = result_sheet

        self.match_id = discord.ui.TextInput(label="SCHEDULED MATCH ID", required=True)
        self.maps_won = discord.ui.TextInput(label="Maps Won", required=True)
        self.maps_lost = discord.ui.TextInput(label="Maps Lost", required=True)
        self.aos_players = discord.ui.TextInput(label="AOS Players", required=True)
        self.cb_results = discord.ui.TextInput(label="CB Results", required=True)

        self.add_item(self.match_id)
        self.add_item(self.maps_won)
        self.add_item(self.maps_lost)
        self.add_item(self.aos_players)
        self.add_item(self.cb_results)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = interaction.user
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            match_id_val = self.match_id.value.strip().lower()

            results_channel = interaction.client.get_channel(1361457240929996980)
            if not results_channel:
                await interaction.response.send_message("❌ Results channel not found.", ephemeral=True)
                return

            submitted_data = self.result_sheet.get_all_records()
            for row in submitted_data:
                existing_id = str(row.get("Match Id", "")).strip().lower()
                if existing_id == match_id_val:
                    await interaction.response.send_message("HEY DUMBFUCK THIS WAS ALREADY SUBMITTED", ephemeral=True)
                    return

            match_data = self.match_sheet.get_all_records()
            match_row = next((row for row in match_data if str(row.get("Match ID", "")).strip() == self.match_id.value.strip()), None)

            if not match_row:
                await interaction.response.send_message(f"❌ Match ID {self.match_id.value.strip()} not found in schedule.", ephemeral=True)
                return

            date = match_row["Date"]
            time = match_row["Time"]
            enemy_team = match_row["Enemy Team"]
            league = match_row["League"]
            match_type = match_row["Match Type"]

            header_emoji = "<a:BlackCrown:1353482149096853606>"
            section_emoji = "<a:ShadowJam:1357240936849211583>"
            submitter_emoji = "<a:wut:1372687602305732618>"
            cb_outcome = self.cb_results.value.strip().upper()
            cb_text = "AOS WIN" if cb_outcome == "W" else "AOS LOSS" if cb_outcome == "L" else cb_outcome

            combined_message = f"""**# {header_emoji} {date} | {time} | {enemy_team} | {league} | {match_type} | ID: {self.match_id.value.strip()} {header_emoji}**
{section_emoji} **MAPS WON:** {self.maps_won.value.strip()}
{section_emoji} **MAPS LOST:** {self.maps_lost.value.strip()}
{section_emoji} **AOS PLAYERS:** {self.aos_players.value.strip()}
{section_emoji} **CB RESULTS:** {cb_text}
{submitter_emoji} **SUBMITTED BY:** <@{user.id}>"""

            await results_channel.send(combined_message)
            await interaction.response.send_message("✅ Match results submitted!", ephemeral=True)

            # Cleanup matches and lineups after submission
            try:
                lineup_sheet = self.match_sheet.spreadsheet.worksheet("lineups")
                lineup_rows = lineup_sheet.get_all_values()
                for idx, row in enumerate(lineup_rows[1:], start=2):
                    if (row[1].strip().lower() == match_id_val and
                        row[2].strip().lower() == enemy_team.lower() and
                        row[3].strip().lower() == league.lower()):
                        msg_id = row[13].strip()
                        chan_id = row[14].strip()
                        try:
                            chan = interaction.client.get_channel(int(chan_id))
                            if chan:
                                msg = await chan.fetch_message(int(msg_id))
                                await msg.delete()
                        except:
                            pass
                        lineup_sheet.delete_rows(idx)
                        break

                match_rows = self.match_sheet.get_all_values()
                for idx, row in enumerate(match_rows[1:], start=2):
                    if (row[8].strip().lower() == match_id_val and
                        row[4].strip().lower() == enemy_team.lower() and
                        row[5].strip().lower() == league.lower()):
                        msg_id = row[9].strip()
                        chan_id = row[10].strip()
                        try:
                            chan = interaction.client.get_channel(int(chan_id))
                            if chan:
                                msg = await chan.fetch_message(int(msg_id))
                                await msg.delete()
                        except:
                            pass
                        self.match_sheet.delete_rows(idx)
                        break
            except Exception as cleanup_error:
                print(f"Cleanup error: {cleanup_error}")

            self.result_sheet.append_row([
                timestamp,
                user.name,
                self.match_id.value.strip(),
                self.maps_won.value.strip(),
                self.maps_lost.value.strip(),
                self.aos_players.value.strip(),
                cb_outcome,
                enemy_team
            ])
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Modal error: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Modal error: {e}", ephemeral=True)

class MatchResultsButton(discord.ui.View):
    def __init__(self, match_sheet, result_sheet):
        super().__init__(timeout=None)
        self.match_sheet = match_sheet
        self.result_sheet = result_sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatchResultsModal(self.match_sheet, self.result_sheet))

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.match_sheet = self.client.open("AOS").worksheet("matches")
        self.result_sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="matchresultsprompt", description="Send AOS match results prompt")
    async def matchresultsprompt(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        try:
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
        image_path = os.path.join(os.path.dirname(__file__), "matchresults.png")
        file = discord.File(fp=image_path, filename="matchresults.png")
        await channel.send(file=file)
        await channel.send(view=MatchResultsButton(self.match_sheet, self.result_sheet))
        await interaction.followup.send("✅ Prompt sent.", ephemeral=True)

    @app_commands.command(name="spy", description="Spy on enemy team results")
    @app_commands.describe(enemy_team="Enemy team name to search for")
    async def spy(self, interaction: discord.Interaction, enemy_team: str):
        await interaction.response.defer()
        try:
            enemy_team = enemy_team.strip().lower()
            records = self.result_sheet.get_all_values()[1:]
            matched = [row for row in records if row[7].strip().lower() == enemy_team]
            if not matched:
                await interaction.followup.send(f"❌ No match results found for `{enemy_team}`")
                return

            spy_emoji = "<a:Spy_Kids_Glasses_Check:1372752191198068796>"
            cheer_emoji = "<a:cheers:1372752619159945226>"
            angry_emoji = "<a:angry:1372752617641349120>"
            header = f"# {spy_emoji} SPY NETWORK ({enemy_team.upper()}) {spy_emoji}\n\n"


            maps_won_group = defaultdict(list)
            for row in matched:
                for map in row[3].split(','):
                    map = map.strip()
                    if map:
                        maps_won_group[map].append(map)
            maps_won = '\n'.join(f"{cheer_emoji} {', '.join(group)}" for group in maps_won_group.values()) or 'None'

            maps_lost_group = defaultdict(list)
            for row in matched:
                for map in row[4].split(','):
                    map = map.strip()
                    if map:
                        maps_lost_group[map].append(map)
            maps_lost = '\n'.join(f"{angry_emoji} {', '.join(group)}" for group in maps_lost_group.values()) or 'None'

            body = f"**MAPS WON:**\n{maps_won}\n\n**MAPS LOST:**\n{maps_lost}"
            await interaction.followup.send(header + body)
        except Exception as e:
            await interaction.followup.send(f"❌ SPY command failed: {e}")

# Register View + Cog
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(cog.match_sheet, cog.result_sheet))
