
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

class Today(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.lineup_sheet = self.client.open("AOS").worksheet("lineups")
        self.match_sheet = self.client.open("AOS").worksheet("matches")

    @app_commands.command(name="today", description="Post today's lineups and leaderboard")
    async def today(self, interaction: discord.Interaction):
        print('📌 Step 1: deferring response')
        await interaction.response.defer()
        print('📌 Step 2: fetching members')
        members = await interaction.guild.fetch_members().flatten()

        try:
            # Match today's lineups
            match_data = self.match_sheet.get_all_values()
            match_headers = match_data[0]
            matches = match_data[1:]

            lineup_data = self.lineup_sheet.get_all_values()
            lineup_headers = lineup_data[0]
            lineups = lineup_data[1:]

            today_str = datetime.now().strftime("%-m/%-d")  # MM/DD
            posted_lineups = []

            emoji_map = {}
            for name in ["AOSgold", "D9", "ShadowJam", "Weed_Gold"]:
                emoji = discord.utils.get(interaction.guild.emojis, name=name)
                emoji_map[name] = str(emoji) if emoji else f":{name}:\n"
            for lineup in lineups:
                match_id = lineup[1]
                matching_match = next((row for row in matches if row[8] == match_id), None)
                if matching_match and matching_match[2] == today_str:
                    league = lineup[3]
                    enemy_team = lineup[2]
                    shooters = [name for name in lineup[4:10] if name]
                    subs = [name for name in lineup[10:12] if name]

                    # Role mention
                    role_name = "Capo" if league == "HC" else "Soldier\n"                    role = discord.utils.get(interaction.guild.roles, name=role_name)
                    role_mention = role.mention if role else f"@{role_name}\n"
                    match_line = (
                        f"# {emoji_map['AOSgold']} {matching_match[2]} | {matching_match[3]} | {matching_match[4]} | \n"                        f"{matching_match[5]} | {matching_match[6]} | ID: {matching_match[8]} {role_mention}\n"                    )

                    d9_line = emoji_map["D9"] * 10

                    shooters_lines = \n"".join([
                        f"{emoji_map['ShadowJam']} " + (next((m.mention for m in members if m.display_name == s or m.name == s), s))
                        for s in shooters
                    ])
                    subs_lines = (
                        \n"".join([
                            f"{emoji_map['Weed_Gold']} " + (next((m.mention for m in members if m.display_name == s or m.name == s), s))
                            for s in subs
                        ]) if subs else f"{emoji_map['Weed_Gold']} None\n"                    )

                    message = (
                        f"{match_line}
\n"                        f"{d9_line}
**Shooters:**
\n"                        f"{shooters_lines}
\n"                        f"{d9_line}
**Subs:**
\n"                        f"{subs_lines}
\n"                        f"{d9_line}\n"                    )

                    await interaction.followup.send(message)
                    posted_lineups.append(match_id)

            # Leaderboard
            rows = self.client.open("AOS").worksheet("giveaway").get_all_values()[1:]
            if not rows:
                await interaction.channel.send("No data found.")
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
                return \n"
".join(lines)

            frag_column = format_column("Top Frags", top_frags, "<:CronusZen:1373022628146843671>")
            react_column = format_column("Top Reactions", top_reactions, "🔁")
            exec_column = format_column("Top Executions", top_executions, "<a:GhostFaceMurder:1373023142750195862>")

            embed = discord.Embed(title="🏆 **GIVEAWAY LEADERBOARD**", color=discord.Color.red())
            embed.add_field(name="Top Frags", value=frag_column, inline=True)
            embed.add_field(name="Top Reactions", value=react_column, inline=True)
            embed.add_field(name="Top Executions", value=exec_column, inline=True)

            await interaction.channel.send(embed=embed)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(tb)
            await interaction.followup.send(f"""❌ Error: {e}
```{tb}```""", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Today(bot))
