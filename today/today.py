
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
        self.giveaway_sheet = self.client.open("AOS").worksheet("giveaway")

    @app_commands.command(name="today", description="Post today's matches and the giveaway leaderboard")
    async def today(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            channel = interaction.channel
            today_date = datetime.now().strftime("%-m/%-d")
            matches = self.match_sheet.get_all_values()
            header = matches[0]
            rows = matches[1:]

            # EMOJI FETCH
            guild = interaction.guild
            emoji = discord.utils.get(guild.emojis, name="AOSgold")
            emoji_str = f"<:{emoji.name}:{emoji.id}>" if emoji else "🟡"

            for row in rows:
                if row[2].strip() == today_date:
                    date = row[2].strip()
                    time = row[3].strip()
                    enemy = row[4].strip()
                    league = row[5].strip()
                    match_type = row[6].strip()
                    players = row[7].strip()
                    match_id = row[8].strip()
                    role_name = "Capo" if league == "HC" else "Soldier"
                    role = discord.utils.get(guild.roles, name=role_name)
                    role_mention = role.mention if role else f"@{role_name}"

                    match_message = (
                        f"# {emoji_str} {date} | {time} | {enemy} | {league} | {match_type} | {players} | ID: {match_id} {role_mention}"
                    )
                    await channel.send(match_message)

            # --- GIVEAWAY LEADERBOARD BELOW ---
            rows = self.giveaway_sheet.get_all_values()[1:]
            if not rows:
                await channel.send("No giveaway data found.")
                return

            leaderboard_data = []
            for row in rows:
                username = row[0]
                frags = int(row[1]) if row[1].isdigit() else 0
                reactions = int(row[2]) if row[2].isdigit() else 0
                executions = int(row[3]) if row[3].isdigit() else 0
                leaderboard_data.append((username, frags, reactions, executions))

            top_frags = sorted(leaderboard_data, key=lambda x: x[1], reverse=True)[:10]
            top_reactions = sorted(leaderboard_data, key=lambda x: x[2], reverse=True)[:10]
            top_executions = sorted(leaderboard_data, key=lambda x: x[3], reverse=True)[:10]

            def format_column(title, data, emoji):
                lines = [f"**{emoji} {title.upper()}**"]
                for i, entry in enumerate(data):
                    user = entry[0]
                    if i == 0:
                        lines.append(f"<a:BlackCrown:1353482149096853606> **#{i+1} {user}**")
                    elif i == 1:
                        lines.append(f"<a:WhiteCrown:1353482417893277759> **#{i+1} {user}**")
                    else:
                        lines.append(f"**#{i+1} {user}**")
                return "\n\n".join(lines)

            frag_column = format_column("Top Frags", top_frags, "<:CronusZen:1373022628146843671>")
            react_column = format_column("Top Reactions", top_reactions, "🔁")
            exec_column = format_column("Top Executions", top_executions, "<a:GhostFaceMurder:1373023142750195862>")

            embed = discord.Embed(title="🏆 **GIVEAWAY LEADERBOARD**", color=discord.Color.red())
            embed.add_field(name="Top Frags", value=frag_column, inline=True)
            embed.add_field(name="Top Reactions", value=react_column, inline=True)
            embed.add_field(name="Top Executions", value=exec_column, inline=True)

            await channel.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Today(bot))
