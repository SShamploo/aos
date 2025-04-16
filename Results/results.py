
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

class MatchResultsModal(discord.ui.Modal, title="AOS MATCH RESULTS"):
    def __init__(self, sheet, results_channel, image_urls):
        super().__init__()
        self.sheet = sheet
        self.results_channel = results_channel
        self.image_urls = image_urls

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

        await self.results_channel.send(result_line)
        for url in self.image_urls:
            await self.results_channel.send(url)

        self.sheet.append_row([
            timestamp,
            user.name,
            self.match_type.value,
            self.league.value,
            self.enemy_team.value,
            self.map.value,
            self.wl.value,
            ", ".join(self.image_urls)
        ])

        await interaction.response.send_message("✅ Match results submitted!", ephemeral=True)

class ImageUploadView(discord.ui.View):
    def __init__(self, bot, sheet):
        super().__init__(timeout=300)
        self.bot = bot
        self.sheet = sheet
        self.image_urls = []
        self.image_messages = []
        self.user = None
        self.count = 1
        self.done = False
        self.uploading = False

    @discord.ui.button(label="Done Uploading Images", style=discord.ButtonStyle.primary, custom_id="done_uploading")
    async def done_uploading(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ You didn't start this upload.", ephemeral=True)
            return

        self.done = True
        await interaction.response.defer()
        await self.open_modal(interaction)

    async def collect_images(self, interaction):
        self.user = interaction.user
        channel = interaction.channel
        await channel.send("📸 Upload Match Screenshots now, send 1–10 screenshots one-by-one.", ephemeral=True)
        await channel.send(f"📸 Upload Image {self.count}:", view=self)

        def check(m):
            return m.author.id == self.user.id and m.attachments and m.channel == channel

        while self.count <= 10 and not self.done:
            try:
                msg = await self.bot.wait_for("message", timeout=300, check=check)
                resultimages_channel = discord.utils.get(interaction.guild.text_channels, name="resultimages")
                if not resultimages_channel:
                    await channel.send("❌ Could not find #resultimages channel.", ephemeral=True)
                    return

                new_msg = await resultimages_channel.send(file=await msg.attachments[0].to_file())
                self.image_urls.append(new_msg.attachments[0].url)
                self.image_messages.append(msg)

                self.count += 1
                if self.count <= 10 and not self.done:
                    await channel.send(f"📸 Upload Image {self.count} or click **Done Uploading Images**", ephemeral=True)
            except Exception:
                break

        if not self.done:
            await self.open_modal(interaction)

    async def open_modal(self, interaction):
        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if results_channel:
            await interaction.response.send_modal(MatchResultsModal(self.sheet, results_channel, self.image_urls))
        else:
            await interaction.followup.send("❌ #results channel not found.", ephemeral=True)

class MatchResultsButton(discord.ui.View):
    def __init__(self, bot, sheet):
        super().__init__(timeout=None)
        self.bot = bot
        self.sheet = sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ImageUploadView(self.bot, self.sheet)
        await view.collect_images(interaction)

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
