
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

class MatchResultsModal(discord.ui.Modal, title="AOS MATCH RESULTS"):
    def __init__(self, sheet, image_urls):
        super().__init__()
        self.sheet = sheet
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
        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if not results_channel:
            await interaction.response.send_message("❌ #results channel not found.", ephemeral=True)
            return

        result_line = (
            f"# MATCH RESULTS: {self.match_type.value.upper()} | {self.league.value.upper()} | "
            f"{self.enemy_team.value.upper()} | {self.map.value.upper()} | {self.wl.value.upper()}"
        )

        # Post result summary
        await results_channel.send(result_line)

        # Post uploaded screenshots
        for url in self.image_urls:
            await results_channel.send(url)

        # Log to Google Sheet
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        except Exception as e:
            print(f"⚠️ Failed to log match results: {e}")

        await interaction.response.send_message("✅ Match results submitted!", ephemeral=True)


class ImageUploadView(discord.ui.View):
    def __init__(self, bot, sheet):
        super().__init__(timeout=300)
        self.bot = bot
        self.sheet = sheet
        self.image_urls = []
        self.author_id = None
        self.prompt_message = None
        self.image_count = 1
        self.modal_triggered = False

    @discord.ui.button(label="Done Uploading Images", style=discord.ButtonStyle.primary, custom_id="done_uploading")
    async def done_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You're not the one uploading images.", ephemeral=True)
            return

        self.modal_triggered = True
        await interaction.response.send_modal(MatchResultsModal(self.sheet, self.image_urls))

    async def collect_images(self, interaction: discord.Interaction):
        self.author_id = interaction.user.id
        channel = interaction.channel
        await interaction.followup.send(f"📸 Upload Image 1:", view=self, ephemeral=True)

        def check(m):
            return m.author.id == self.author_id and m.channel == channel and m.attachments

        while len(self.image_urls) < 10 and not self.modal_triggered:
            try:
                msg = await self.bot.wait_for("message", timeout=60.0, check=check)
                for attachment in msg.attachments:
                    if len(self.image_urls) < 10:
                        self.image_urls.append(attachment.url)
                await msg.delete()
                if not self.modal_triggered:
                    self.image_count += 1
                    await channel.send(f"📸 Upload Image {self.image_count} or click **Done Uploading Images**")
            except asyncio.TimeoutError:
                break

        if not self.modal_triggered:
            await channel.send("⏰ Upload timed out. Please try again.")


class MatchResultsButton(discord.ui.View):
    def __init__(self, bot, sheet):
        super().__init__(timeout=None)
        self.bot = bot
        self.sheet = sheet

    @discord.ui.button(label="AOS MATCH RESULTS", style=discord.ButtonStyle.danger, custom_id="match_results_button")
    async def open_uploader(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ImageUploadView(self.bot, self.sheet)
        await interaction.response.send_message(f"📸 Upload Match Screenshots now, send 1–10 screenshots one-by-one.", ephemeral=True)
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


# Register View + Cog
async def setup(bot):
    cog = MatchResults(bot)
    await bot.add_cog(cog)
    bot.add_view(MatchResultsButton(bot, cog.sheet))
