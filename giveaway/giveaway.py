
import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class GiveawayModal(discord.ui.Modal, title="GIVEAWAY ENTRIES"):
    def __init__(self, giveaway_sheet):
        super().__init__()
        self.giveaway_sheet = giveaway_sheet

        self.top_frag = discord.ui.TextInput(label="Top Frag?", required=True, placeholder="Yes or No")
        self.execution = discord.ui.TextInput(label="Execution:", required=False, placeholder="Enter a number")

        self.add_item(self.top_frag)
        self.add_item(self.execution)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            username = interaction.user.name
            user_mention = interaction.user.mention
            top_frag_raw = self.top_frag.value.strip().lower()
            top_frag_value = 1 if top_frag_raw in ["yes", "y"] else 0
            execution_value = int(self.execution.value.strip()) if self.execution.value.strip() else 0

            existing_rows = self.giveaway_sheet.get_all_values()
            headers = existing_rows[0]
            user_column_index = headers.index("Discord Username")
            found = False

            for i, row in enumerate(existing_rows[1:], start=2):
                if row[user_column_index].strip().lower() == username.lower():
                    current_frag = int(row[1]) if row[1] else 0
                    current_exec = int(row[3]) if row[3] else 0
                    new_row = [username, current_frag + top_frag_value, "", current_exec + execution_value]
                    self.giveaway_sheet.update(f"A{i}:D{i}", [new_row])
                    found = True
                    break

            if not found:
                new_row = [username, top_frag_value, "", execution_value]
                self.giveaway_sheet.append_row(new_row)

            target_channel = interaction.client.get_channel(1373018460401176657)
            if target_channel:
                message = (
                    f"# <a:BlackCrown:1353482149096853606> New Giveaway Entry Added by {user_mention} <a:BlackCrown:1353482149096853606>\n"
                    f"# <:CronusZen:1373022628146843671> Top Frag: `{top_frag_value}`\n"
                    f"# <a:GhostFaceMurder:1373023142750195862> Execution: `{execution_value}`"
                )
                await target_channel.send(message)

            await interaction.response.send_message("✅ Your giveaway entry has been submitted!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Submission failed: {e}", ephemeral=True)

class GiveawayButton(discord.ui.View):
    def __init__(self, giveaway_sheet):
        super().__init__(timeout=None)
        self.giveaway_sheet = giveaway_sheet

    @discord.ui.button(label="ENTER GIVEAWAY", style=discord.ButtonStyle.danger, custom_id="giveaway_button")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GiveawayModal(self.giveaway_sheet))

class GiveawayForm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.giveaway_sheet = self.client.open("AOS").worksheet("giveaway")

    @app_commands.command(name="giveawayform", description="Send a giveaway form with entry modal")
    async def giveawayform(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        try:
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")
        image_path = os.path.join(os.path.dirname(__file__), "Giveaway Entries.jpg")
        file = discord.File(fp=image_path, filename="Giveaway Entries.jpg")
        await channel.send(file=file)
        await channel.send(view=GiveawayButton(self.giveaway_sheet))
        await interaction.followup.send("✅ Giveaway prompt sent.", ephemeral=True)

    @app_commands.command(name="leaderboard", description="Display top 10 for Frags, Reactions, and Executions")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            rows = self.giveaway_sheet.get_all_values()[1:]
            if not rows:
                await interaction.followup.send("No data found.")
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

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Leaderboard failed: {e}", ephemeral=True)

async def setup(bot):
    cog = GiveawayForm(bot)
    await bot.add_cog(cog)
    bot.add_view(GiveawayButton(cog.giveaway_sheet))
