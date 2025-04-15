import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

class PlayerInfoModal(discord.ui.Modal, title="🎮 Submit Your Player Info"):
    activision_id = discord.ui.TextInput(label="Activision ID", placeholder="Your Activision ID", required=True)
    streaming_platform = discord.ui.TextInput(label="Streaming Platform", placeholder="Twitch, Kick, etc. or leave blank", required=False)

    def __init__(self, platform, interaction, sheet):
        super().__init__()
        self.platform = platform
        self.interaction = interaction
        self.sheet = sheet

    async def on_submit(self, interaction: discord.Interaction):
        channel = discord.utils.get(interaction.guild.text_channels, name="playerinformation")
        if not channel:
            await interaction.response.send_message("❌ #playerinformation channel not found.", ephemeral=True)
            return

        # ✅ Format for display
        embed = discord.Embed(title="📝 Player Info Submission", color=discord.Color.green())
        embed.add_field(name="Discord Username", value=interaction.user.mention, inline=False)
        embed.add_field(name="Activision ID", value=self.activision_id.value, inline=False)
        embed.add_field(name="Platform", value=self.platform, inline=False)
        embed.add_field(name="Streaming Platform", value=self.streaming_platform.value or "N/A", inline=False)

        await channel.send(embed=embed)
        await interaction.response.send_message("✅ Your info has been submitted to #playerinformation!", ephemeral=True)

        # ✅ Save to Google Sheet
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
        self.prompt_message_id = None

        # ✅ Google Sheet Setup
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open("AOS").worksheet("playerinformation")

    @commands.Cog.listener()
    async def on_ready(self):
        channel = discord.utils.get(self.bot.get_all_channels(), name="playerinfo")  # Target channel for reaction message
        if not channel:
            print("⚠️ #playerinfo channel not found.")
            return

        if self.prompt_message_id is None:
            message = await channel.send("Click 📝 to submit your player information.")
            await message.add_reaction("📝")
            self.prompt_message_id = message.id
            print(f"✅ Player info prompt sent (ID: {self.prompt_message_id})")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.bot.user.id:
            return

        if payload.message_id != self.prompt_message_id or str(payload.emoji) != "📝":
            return

        guild = self.bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        if not member:
            return

        class PlatformSelect(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.selected = None

            @discord.ui.select(
                placeholder="Select your platform...",
                options=[
                    discord.SelectOption(label="PC", value="PC"),
                    discord.SelectOption(label="PlayStation", value="PlayStation"),
                    discord.SelectOption(label="Xbox", value="Xbox"),
                ]
            )
            async def select_callback(self, interaction: discord.Interaction, select):
                self.selected = select.values[0]
                self.stop()

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        view = PlatformSelect()
        try:
            prompt = await channel.send(f"<@{payload.user_id}>, select your platform:", view=view)
            await view.wait()
            await prompt.delete()
        except Exception as e:
            print(f"⚠️ Platform select failed: {e}")
            return

        if view.selected:
            await member.send_modal(PlayerInfoModal(platform=view.selected, interaction=payload, sheet=self.sheet))

# Setup function
async def setup(bot):
    await bot.add_cog(PlayerInfo(bot))
