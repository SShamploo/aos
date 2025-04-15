import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timedelta
import os
import json
import base64
import gspread
import atexit
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class HCAvailabilityScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # 🔐 Load Google Sheets credentials from environment
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_b64 = os.getenv("GOOGLE_SHEETS_CREDS_B64")
        creds_json = json.loads(base64.b64decode(creds_b64.encode("utf-8")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.gs_client = gspread.authorize(creds)
        self.sheet = self.gs_client.open("AOS").worksheet("hcavailability")

        # ✅ Persistent cache setup
        self.sent_messages_file = "availability_cache.json"
        self.sent_messages = self.load_sent_messages()
        atexit.register(self.save_sent_messages)

    def load_sent_messages(self):
        if os.path.exists(self.sent_messages_file):
            with open(self.sent_messages_file, "r") as f:
                return json.load(f)
        return {}

    def save_sent_messages(self):
        with open(self.sent_messages_file, "w") as f:
            json.dump(self.sent_messages, f)

    @app_commands.command(name="hcavailabilityscheduler", description="Post availability days and add time emojis")
    async def hcavailabilityscheduler(self, interaction: discord.Interaction):
        emoji_names = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12AM"]
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

        self.sent_messages[str(interaction.channel.id)] = {}

        for i in range(7):
            current_day = sunday + timedelta(days=i)
            day_name = current_day.strftime("%A").upper()  # ✅ ALL CAPS
            date_str = current_day.strftime("%m/%d")
            formatted_message = f"# {day_name} {date_str}"

            msg = await interaction.channel.send(formatted_message)
            for emoji in emojis:
                await msg.add_reaction(emoji)

            self.sent_messages[str(interaction.channel.id)][str(msg.id)] = f"{day_name} {date_str}"

        self.save_sent_messages()

    @app_commands.command(name="deletehcavailability", description="Delete availability messages and clear sheet data.")
    async def deletehcavailability(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        channel_id = str(interaction.channel.id)
        deleted = 0

        if channel_id in self.sent_messages:
            message_ids = list(self.sent_messages[channel_id].keys())

            # ✅ Step 1: Delete tracked messages in Discord
            for msg_id in message_ids:
                try:
                    msg = await interaction.channel.fetch_message(int(msg_id))
                    await msg.delete()
                    deleted += 1
                except discord.NotFound:
                    continue
                except discord.Forbidden:
                    print(f"❌ Cannot delete message {msg_id} - missing permissions.")
                except Exception as e:
                    print(f"⚠️ Failed to delete message {msg_id}: {e}")

            # ✅ Step 2: Remove matching rows from Google Sheets
            all_rows = self.sheet.get_all_values()
            header = all_rows[0]
            data_rows = all_rows[1:]

            rows_to_keep = [header]
            for row in data_rows:
                if len(row) >= 5 and row[4] not in message_ids:
                    rows_to_keep.append(row)

            # Clear and rewrite the sheet
            self.sheet.clear()
            self.sheet.append_rows(rows_to_keep)

            # ✅ Clear from local cache
            self.sent_messages[channel_id] = {}
            self.save_sent_messages()

            await interaction.followup.send(f"🗑️ Deleted {deleted} message(s) and cleaned up Google Sheet.", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ No tracked availability messages found in this channel.", ephemeral=True)

# Required to register the cog
async def setup(bot):
    await bot.add_cog(HCAvailabilityScheduler(bot))
