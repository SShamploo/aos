
print("📦 Importing Results Cog...")

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

MAX_IMAGES = 10

class ImageUploadView(discord.ui.View):
    def __init__(self, bot, sheet):
        super().__init__(timeout=180)
        self.bot = bot
        self.sheet = sheet
        self.images = []
        self.user = None
        self.interaction = None
        self.done = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.user

    @discord.ui.button(label="Done Uploading Images", style=discord.ButtonStyle.primary)
    async def done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.done = True
        await interaction.response.defer()
        self.stop()

    async def collect_images(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.user = interaction.user
        channel = interaction.channel

        try:
            prompt_msg = await channel.send("📸 Upload Image 1:", view=self)

            for i in range(1, MAX_IMAGES + 1):
                def check(msg):
                    return msg.author.id == self.user.id and msg.attachments and msg.channel == channel

                try:
                    msg = await self.bot.wait_for("message", timeout=120, check=check)
                    self.images.append(msg.attachments[0])
                    await msg.delete()

                    if i < MAX_IMAGES and not self.done:
                        await channel.send(f"📸 Upload Image {i+1} or click **Done Uploading Images**", view=self)
                except asyncio.TimeoutError:
                    break

                if self.done:
                    break

            await prompt_msg.delete()
        except Exception as e:
            print(f"⚠️ Image collection failed: {e}")
            await interaction.followup.send("❌ Something went wrong while collecting images.", ephemeral=True)

class MatchResultsModal(discord.ui.Modal, title="AOS MATCH RESULTS"):
    def __init__(self, sheet, images, results_channel):
        super().__init__()
        self.sheet = sheet
        self.images = images
        self.results_channel = results_channel

        self.match_type = discord.ui.TextInput(label="MATCH TYPE (OBJ/CB/CHALL/SCRIM/COMP)", required=True)
        self.league = discord.ui.TextInput(label="LEAGUE (HC/AL)", required=True)
        self.enemy_team = discord.ui.TextInput(label="ENEMY TEAM", required=True)
        self.map = discord.ui.TextInput(label="MAP", required=True)
        self.wl = discord.ui.TextInput(label="W/L", placeholder="W or L", required=True)

        self.add_item(self.match_type)
        self.add_item(self.league)
        self.add_item(self.enemy_team)
        self.add_item(self.map)
        self.add_item(self.wl)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        result_line = (
            f"# MATCH RESULTS: {self.match_type.value.upper()} | {self.league.value.upper()} | "
            f"{self.enemy_team.value.upper()} | {self.map.value.upper()} | {self.wl.value.upper()}"
        )

        try:
            sent = await self.results_channel.send(result_line)

            for img in self.images:
                await self.results_channel.send(file=await img.to_file())

            self.sheet.append_row([
                timestamp,
                user.name,
                self.match_type.value,
                self.league.value,
                self.enemy_team.value,
                self.map.value,
                self.wl.value,
                " / ".join([img.url for img in self.images])
            ])

            await interaction.response.send_message("✅ Match results submitted!", ephemeral=True)

        except Exception as e:
            print(f"⚠️ Failed to handle results: {e}")
            await interaction.response.send_message("❌ Something went wrong while submitting results.", ephemeral=True)

class MatchResultsButton(discord.ui.View):
    def __init__(self, bot, sheet):
        super().__init__(timeout=None)
        self.bot = bot
        self.sheet = sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        view = ImageUploadView(self.bot, self.sheet)
        await channel.send("📸 Upload Match Screenshots now, send 1–10 screenshots one-by-one.", view=view)
        await view.collect_images(interaction)

        if view.images:
            await interaction.followup.send("📝 Opening the match form...", ephemeral=True)
            await interaction.response.send_modal(MatchResultsModal(self.sheet, view.images, channel))
        else:
            await interaction.followup.send("❌ No images received. Please try again.", ephemeral=True)

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("matchresults")

    @app_commands.command(name="matchresultsprompt", description="Send AOS match results prompt")
    async def matchresultsprompt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
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
        await channel.send(view=MatchResultsButton(self.bot, self.sheet))

        await interaction.followup.send("✅ Prompt sent.", ephemeral=True)

async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(bot, cog.sheet))
