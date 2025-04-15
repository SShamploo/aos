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

        self.activision_id = discord.ui.TextInput(
            label="Activision ID",
            placeholder="Enter your Activision ID",
            required=True
        )
        self.streaming_platform = discord.ui.TextInput(
            label="Streaming Platform",
            placeholder="Twitch, Kick, etc. or leave blank",
            required=False
        )

        self.add_item(self.activision_id)
        self.add_item(self.streaming_platform)

        # Dropdown for platform (as a Select)
        self.platform_select = discord.ui.Select(
            placeholder="Select your platform",
            options=[
                discord.SelectOption(label="PC", value="PC"),
                discord.SelectOption(label="PlayStation", value="PlayStation"),
                discord.SelectOption(label="Xbox", value="Xbox")
            ]
        )
        self.platform_select.callback = self.select_callback
        self.add_item(self.platform_select)
        self.platform = None

    async def select_callback(self, interaction: discord.Interaction):
        self.platform = self.platform_select.values[0]

    async def on_submit(self, interaction: discord.Interaction):
        self.platform = self.platform or self.platform_select.values[0]

        info_channel = discord.utils.get(interaction.guild.text_channels, name="playerinfo")
        if not info_channel:
            await interaction.response.send_message("❌ #playerinfo channel not found.", ephemeral=True)
            return

        embed = discord.Embed(title="📝 Player Info Submission", color=discord.Color.green())
        embed.add_field(name="Discord Username", value=interaction.user.mention, inline=False)
        embed.add_field(name="Activision ID", value=self.activision_id.value, inline=False)
        embed.add_field(name="Platform", value=self.platform, inline=False)
        embed.add_field(name="Streaming Platform", value=self.streaming_platform.value or "N/A", inline=False)

        await info_channel.send(embed=embed)
        await interaction.response.send_message("✅ Your info has been submitted to #playerinfo!", ephemeral=True)

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.sheet.append_row([
                timestamp,
                str(interaction.user),
                str(interaction.user.id),
                self.activision_id.value,
                self.platform,
                self.streaming_platform.value or "N/A"
            ])
        except Exception as e:
            print(f"⚠️ Failed to write to Google Sheet: {e}")

class PlayerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # ✅ Google Sheets setup
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("playerinformation")

    @app_commands.command(name="playerinfoprompt", description="Open the player info submission modal")
    async def playerinfoprompt(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PlayerInfoModal(sheet=self.sheet))

# Register cog
async def setup(bot):
    await bot.add_cog(PlayerInfo(bot))
