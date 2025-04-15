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

class PlayerInfoModal(discord.ui.Modal, title="🎮 Submit Your Player Info"):
    def __init__(self, sheet):
        super().__init__()
        self.sheet = sheet

        self.activision = discord.ui.TextInput(label="Activision ID", placeholder="e.g., Username#123456", required=True)
        self.platform = discord.ui.TextInput(label="Platform", placeholder="PC / Xbox / Playstation", required=True)
        self.stream = discord.ui.TextInput(label="Streaming Platform", placeholder="e.g., Twitch.tv/yourname", required=False)

        self.add_item(self.activision)
        self.add_item(self.platform)
        self.add_item(self.stream)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        values = [
            timestamp,
            user.name,
            str(user.id),
            self.activision.value,
            self.platform.value,
            self.stream.value if self.stream.value else "N/A"
        ]

        channel = discord.utils.get(interaction.guild.text_channels, name="playerinfo")
        if channel:
            response = (
                f"**Discord Username:** {user.mention}\n"
                f"**Activision ID:** {self.activision.value}\n"
                f"**Platform:** {self.platform.value}\n"
                f"**Streaming Platform:** {self.stream.value if self.stream.value else 'N/A'}"
            )
            await channel.send(response)

        try:
            rows = self.sheet.get_all_values()
            updated = False

            for idx, row in enumerate(rows[1:], start=2):  # Skip header
                if len(row) >= 3 and row[2] == str(user.id):
                    self.sheet.update(f"A{idx}:F{idx}", [values])
                    updated = True
                    break

            if not updated:
                self.sheet.append_row(values)

        except Exception as e:
            print(f"⚠️ Failed to log/update Google Sheet: {e}")

        await interaction.response.send_message("✅ Your player info was submitted!", ephemeral=True)

class PlayerInfoButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(
        label="⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀AOS PLAYER INFORMATION⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀",
        style=discord.ButtonStyle.danger,
        custom_id="player_info_button"
    )
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PlayerInfoModal(self.sheet))

class PlayerInformation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8")
        creds_json = json.loads(creds)
        self.client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope))
        self.sheet = self.client.open("AOS").worksheet("playerinformation")
        self.users_sheet = self.client.open("AOS").worksheet("Users")

    @app_commands.command(name="playerinfoprompt", description="Post the player info submission image + button.")
    async def playerinfoprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        channel = interaction.channel

        try:
            async for msg in channel.history(limit=10):
                if msg.author.id == interaction.client.user.id and (msg.attachments or msg.components):
                    await msg.delete()
        except Exception as e:
            print(f"⚠️ Failed to clean previous prompt: {e}")

        image_path = os.path.join(os.path.dirname(__file__), "Playerinfo Report.jpg")
        file = discord.File(fp=image_path, filename="Playerinfo Report.jpg")
        await channel.send(file=file)

        await channel.send(view=PlayerInfoButton(self.sheet))

        await interaction.followup.send("✅ Prompt sent.", ephemeral=True)

    @app_commands.command(name="userinformation", description="View player info or show all.")
    @app_commands.describe(user="Select a user or choose yourself. Use @everyone to show all.")
    async def userinformation(self, interaction: discord.Interaction, user: discord.User = None):
        all_rows = self.sheet.get_all_values()
        rows = all_rows[1:]

        if user is None or user == interaction.guild.default_role:  # @everyone
            if not rows:
                await interaction.response.send_message("⚠️ No entries found.", ephemeral=True)
                return

            lines = []
            for row in rows:
                if len(row) >= 6:
                    line = f"{row[1]}    {row[3]}    {row[4]}    {row[5]}"
                    lines.append(line)

            info = "\n".join(lines)
            embed = discord.Embed(title="📋 AOS Player Information", description=f"```{info}```", color=discord.Color.purple())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        for row in rows:
            if len(row) >= 4 and row[2] == str(user.id):
                embed = discord.Embed(
                    title=f"📋 Info for {user.display_name}",
                    color=discord.Color.green()
                )
                embed.add_field(name="Activision ID", value=row[3], inline=False)
                embed.add_field(name="Platform", value=row[4], inline=True)
                embed.add_field(name="Streaming", value=row[5] if len(row) > 5 else "N/A", inline=True)
                embed.set_footer(text="Fetched from playerinformation sheet")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

        await interaction.response.send_message("⚠️ No player info found for that user.", ephemeral=True)

    @app_commands.command(name="syncusers", description="Sync current Discord users and remove outdated entries.")
    async def syncusers(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("⚠️ Command must be run in a server.")
            return

        members = [m for m in guild.members if not m.bot]
        user_data = [[str(m), str(m.id)] for m in members]

        # Clear and update Users sheet
        self.users_sheet.clear()
        self.users_sheet.append_row(["Username", "User ID"])
        self.users_sheet.append_rows(user_data)

        # Build set of valid user IDs
        valid_ids = set(str(m.id) for m in members)

        # Get current playerinformation rows
        all_rows = self.sheet.get_all_values()
        rows = all_rows[1:]
        deleted = 0

        for i in reversed(range(len(rows))):  # Reverse to avoid shifting rows
            row = rows[i]
            if len(row) >= 3 and row[2] not in valid_ids:
                self.sheet.delete_rows(i + 2)  # Offset for header
                deleted += 1

        await interaction.followup.send(
            f"✅ Synced {len(user_data)} users to 'Users' sheet.\n🗑️ Removed {deleted} outdated entries from playerinformation.",
            ephemeral=True
        )

# ✅ Register persistent view
async def setup(bot):
    cog = PlayerInformation(bot)
    await bot.add_cog(cog)
    bot.add_view(PlayerInfoButton(cog.sheet))
