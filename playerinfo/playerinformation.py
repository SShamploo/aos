import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

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
        response = (
            f"**Discord Username:** {user.mention}\n"
            f"**Activision ID:** {self.activision.value}\n"
            f"**Platform:** {self.platform.value}\n"
            f"**Streaming Platform:** {self.stream.value if self.stream.value else 'N/A'}"
        )

        channel = discord.utils.get(interaction.guild.text_channels, name="playerinfo")
        if channel:
            await channel.send(response)

        try:
            self.sheet.append_row([
                str(user),
                self.activision.value,
                self.platform.value,
                self.stream.value if self.stream.value else "N/A"
            ])
        except Exception as e:
            print(f"⚠️ Failed to write to Google Sheet: {e}")

        await interaction.response.send_message("✅ Player info submitted!", ephemeral=True)

class PlayerInfoButton(discord.ui.View):
    def __init__(self, sheet):
        super().__init__(timeout=None)
        self.sheet = sheet

    @discord.ui.button(label="AOS", style=discord.ButtonStyle.danger)
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
        self.last_prompt_id = None

    @app_commands.command(name="playerinfoprompt", description="Post the player info submission image + button.")
    async def playerinfoprompt(self, interaction: discord.Interaction):
        channel = interaction.channel

        # Delete previous prompt
        if self.last_prompt_id:
            try:
                prev = await channel.fetch_message(self.last_prompt_id)
                await prev.delete()
            except:
                pass

        # Send image (must be saved in same folder as this script)
        image_path = os.path.join(os.path.dirname(__file__), "Playerinfo Report.jpg")
        file = discord.File(fp=image_path, filename="Playerinfo Report.jpg")
        image_msg = await channel.send(file=file)

        # Send button
        button_msg = await channel.send(view=PlayerInfoButton(self.sheet))

        self.last_prompt_id = image_msg.id
        await interaction.response.send_message("✅ Prompt sent.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PlayerInformation(bot))
