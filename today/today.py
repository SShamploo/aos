
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

class Today(commands.Cog):
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
        self.giveaway_sheet = self.client.open("AOS").worksheet("giveaway")

    @app_commands.command(name="today", description="Post today's scheduled lineups and leaderboard")
    async def today(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            today_str = datetime.now().strftime("%-m/%-d")
            match_data = self.match_sheet.get_all_values()
            lineup_data = self.lineup_sheet.get_all_values()
            match_id_to_date = {row[8]: row[2] for row in match_data[1:] if len(row) > 8 and row[2] == today_str}

            for row in lineup_data[1:]:
                if len(row) > 1 and row[1] in match_id_to_date:
                    shooters = [user for user in row[4:10] if user]
                    subs = [user for user in row[10:12] if user]
                    league = row[3]
                    role_mention = "@Capo" if league == "HC" else "@Soldier"
                    match_id = row[1]
                    enemy_team = row[2]

                    header = f"**# 🥇 {today_str} | {enemy_team} | {league} | ID: {match_id} {role_mention}**"
                    shooters_block = "
".join([f"<:ShadowJam:1357240936849211583> {s}" for s in shooters])
                    subs_block = "
".join([f"<:Weed_Gold:1234567890> {s}" for s in subs]) if subs else "<:Weed_Gold:1234567890> None"

                    msg = f"""{header}
<:D9:1234567890> <:D9:1234567890> <:D9:1234567890>
**Shooters:**
{shooters_block}
<:D9:1234567890> <:D9:1234567890> <:D9:1234567890>
**Subs:**
{subs_block}
<:D9:1234567890> <:D9:1234567890> <:D9:1234567890>"""

                    await interaction.channel.send(msg)

            # leaderboard
            rows = self.giveaway_sheet.get_all_values()[1:]
            data = [(row[0], int(row[1]) if row[1].isdigit() else 0,
                            int(row[2]) if row[2].isdigit() else 0,
                            int(row[3]) if row[3].isdigit() else 0) for row in rows]
            top_frags = sorted(data, key=lambda x: x[1], reverse=True)[:10]
            top_execs = sorted(data, key=lambda x: x[3], reverse=True)[:10]
            top_reacts = sorted(data, key=lambda x: x[2], reverse=True)[:10]

            def leaderboard_block(title, records, emoji):
                lines = [f"**{emoji} {title.upper()}**"]
                for i, (name, *_rest) in enumerate(records):
                    if i == 0:
                        lines.append(f"<a:BlackCrown:1353482149096853606> **#{i+1} {name}**")
                    elif i == 1:
                        lines.append(f"<a:WhiteCrown:1353482417893277759> **#{i+1} {name}**")
                    else:
                        lines.append(f"**#{i+1} {name}**")
                return "\n\n".join(lines)

            embed = discord.Embed(title="🏆 **GIVEAWAY LEADERBOARD**", color=discord.Color.red())
            embed.add_field(name="Top Frags", value=leaderboard_block("Top Frags", top_frags, "<:CronusZen:1373022628146843671>"), inline=True)
            embed.add_field(name="Top Reactions", value=leaderboard_block("Top Reactions", top_reacts, "🔁"), inline=True)
            embed.add_field(name="Top Executions", value=leaderboard_block("Top Executions", top_execs, "<a:GhostFaceMurder:1373023142750195862>"), inline=True)

            await interaction.channel.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Today(bot))
