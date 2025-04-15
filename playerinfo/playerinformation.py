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

# Modal for submitting info
class PlayerInfoModal(discord.ui.Modal, title="🎮 Submit Your Player Info"):
    def __init__(self, platform, sheet):
        super().__init__()
        self.platform = platform
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

    async def on_submit(self, interaction: discord.Interaction):
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
        await interaction.response.send_message("✅ Your info has been submitted!", ephemeral=True)

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

# Dropdown view triggered by button
class PlatformSelectView(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=60)
        self.sheet = sheet

    @discord.ui.select(
        placeholder="Select your platform...",
        options=[
            discord.SelectOption(label="PC", value="PC"),
            discord.SelectOption(label="PlayStation", value="PlayStation"),
            discord.SelectOption(label="Xbox", value="Xbox")
        ]
    )
    async def select_platform(self, interaction: discord.Interaction, select):
        selected = select.values[0]
        await interaction.response.send_modal(PlayerInfoModal(platform=selected, sheet=self.sheet))

# Main button that starts the flow
class PlayerInfoButtonView(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(label="Submit Player Info", style=discord.ButtonStyle.danger, custom_id="submit_info_btn")
    async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select your platform:", view=PlatformSelectView(self.sheet), ephemeral=True)

# Main cog setup
class PlayerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Google Sheets Setup
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("playerinformation")

    @app_commands.command(name="playerinfoprompt", description="Post the player info button")
    async def playerinfoprompt(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Click the button below to submit your player information:",
            view=PlayerInfoButtonView(self.sheet)
        )

    @app_commands.command(name="userinformation", description="Look up a user's player info")
    @app_commands.describe(user="Select the user to look up")
    async def userinformation(self, interaction: discord.Interaction, user: discord.User):
        user_id = str(user.id)
        rows = self.sheet.get_all_values()

        result = None
        for row in rows[1:]:  # Skip header
            if len(row) >= 6 and row[2].strip() == user_id:
                result = row
                break

        if result:
            # Format info
            timestamp, name, _, activision_id, platform, streaming_platform = result
            embed = discord.Embed(title="🔍 Player Info Lookup", color=discord.Color.blurple())
            embed.add_field(name="Discord", value=name, inline=False)
            embed.add_field(name="Activision ID", value=activision_id, inline=False)
            embed.add_field(name="Platform", value=platform, inline=False)
            embed.add_field(name="Streaming Platform", value=streaming_platform or "N/A", inline=False)
            embed.set_footer(text=f"Last updated: {timestamp}")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ No info found for {user.mention}.", ephemeral=True)

# Register the cog
async def setup(bot):
    await bot.add_cog(PlayerInfo(bot))
