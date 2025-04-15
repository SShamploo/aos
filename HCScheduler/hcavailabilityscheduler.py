import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timedelta
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class HCAvailabilityScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_messages = {}  # {channel_id: {message_id: message_text}}

        # 🔐 Load Google Sheets credentials from environment
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.gs_client = gspread.authorize(creds)

        # 🗂️ Open the AOS > hcavailability worksheet
        self.sheet = self.gs_client.open("AOS").worksheet("hcavailability")

    @app_commands.command(name="hcavailabilityscheduler", description="Post availability days and add time emojis")
    async def hcavailabilityscheduler(self, interaction: discord.Interaction):
        emoji_names = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12PM"]
        emojis = []

        for name in emoji_names:
            emoji = get(interaction.guild.emojis, name=name)
            if emoji:
                emojis.append(emoji)
            else:
                await interaction.response.send_message(f"Emoji '{name}' not found in this server.", ephemeral=True)
                return

        today = datetime.now().date()
        days_since_sunday = (today.weekday() + 1) % 7
        sunday = today - timedelta(days=days_since_sunday)

        await interaction.response.send_message("📅 Weekly Availability:", ephemeral=False)

        self.sent_messages[interaction.channel.id] = {}

        for i in range(7):
            current_day = sunday + timedelta(days=i)
            day_name = current_day.strftime("%A")
            date_str = current_day.strftime("%m/%d")
            msg = await interaction.channel.send(f"{day_name} {date_str}")
            for emoji in emojis:
                await msg.add_reaction(emoji)
            self.sent_messages[interaction.channel.id][msg.id] = f"{day_name} {date_str}"

    @app_commands.command(name="deletehcavailability", description="Delete availability messages created by the bot.")
    async def deletehcavailability(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id
        deleted = 0

        if channel_id in self.sent_messages:
            for msg_id in self.sent_messages[channel_id]:
                try:
                    msg = await interaction.channel.fetch_message(msg_id)
                    await msg.delete()
                    deleted += 1
                except discord.NotFound:
                    continue
                except discord.Forbidden:
                    print(f"❌ Cannot delete message {msg_id} - missing permissions.")
                except Exception as e:
                    print(f"⚠️ Failed to delete message {msg_id}: {e}")

            self.sent_messages[channel_id] = {}
            await interaction.followup.send(f"🗑️ Deleted {deleted} availability message(s).", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ No availability messages found to delete in this channel.", ephemeral=True)

# Required to register the cog
async def setup(bot):
    await bot.add_cog(HCAvailabilityScheduler(bot))
