import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import os
import json
import base64
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class AvailabilityScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_messages = {}  # {channel_id: {message_id: message_text}}

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.gc = gspread.authorize(creds)
        self.sheet = self.gc.open("AOS").worksheet("availability")

    @app_commands.command(name="sendavailability", description="Post availability messages for a league.")
    @app_commands.choices(
        league=[app_commands.Choice(name="HC", value="HC"), app_commands.Choice(name="AL", value="AL")]
    )
    async def sendavailability(self, interaction: discord.Interaction, league: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)

        emoji_names = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12AM"]
        emojis = []
        for name in emoji_names:
            emoji = discord.utils.get(interaction.guild.emojis, name=name)
            if emoji:
                emojis.append(emoji)
            else:
                await interaction.followup.send(f"❌ Emoji `{name}` not found.", ephemeral=True)
                return

        today = datetime.now().date()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)
        self.sent_messages[interaction.channel.id] = {}

        for i in range(7):
            day = sunday + timedelta(days=i)
            label = f"{day.strftime('%A').upper()} {day.strftime('%m/%d')} | {league.value}"
            msg = await interaction.channel.send(f"**{label}**")
            for emoji in emojis:
                await msg.add_reaction(emoji)
            self.sent_messages[interaction.channel.id][str(msg.id)] = label

        await interaction.followup.send(f"✅ Posted availability for {league.value}", ephemeral=True)

    @app_commands.command(name="deleteavailability", description="Delete availability messages and clear sheet rows.")
    @app_commands.choices(
        league=[app_commands.Choice(name="HC", value="HC"), app_commands.Choice(name="AL", value="AL")]
    )
    async def deleteavailability(self, interaction: discord.Interaction, league: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        channel_id = interaction.channel.id

        if channel_id in self.sent_messages:
            for msg_id in self.sent_messages[channel_id]:
                try:
                    msg = await interaction.channel.fetch_message(msg_id)
                    await msg.delete()
                    deleted += 1
                except Exception:
                    continue
            tracked_ids = list(self.sent_messages[channel_id].keys())
            self.sent_messages[channel_id] = {}
        else:
            tracked_ids = []

        try:
            all_rows = self.sheet.get_all_values()
            to_delete = [
                i + 2 for i, row in enumerate(all_rows[1:])
                if row[4] in tracked_ids and row[6] == league.value
            ]
            for i in reversed(to_delete):
                self.sheet.delete_rows(i)
        except Exception as e:
            print(f"⚠️ Google Sheet deletion failed: {e}")

        await interaction.followup.send(f"🗑️ Deleted {deleted} messages and cleared related rows for {league.value}.", ephemeral=True)

    @app_commands.command(name="availability", description="Display availability for a specific league and day.")
    @app_commands.choices(
        league=[app_commands.Choice(name="HC", value="HC"), app_commands.Choice(name="AL", value="AL")],
        day=[
            app_commands.Choice(name=day.upper(), value=day.upper())
            for day in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        ]
    )
    async def availability(self, interaction: discord.Interaction, league: app_commands.Choice[str], day: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        rows = self.sheet.get_all_values()[1:]
        relevant = [r for r in rows if r[5].startswith(day.value) and r[6] == league.value]

        if not relevant:
            await interaction.followup.send(f"⚠️ No data found for {league.value} - {day.value}.", ephemeral=True)
            return

        order = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12AM"]
        result = f"**{day.value}**\n"
        users = {}

        for r in relevant:
            uid = r[2]
            time = r[3]
            users.setdefault(uid, []).append(time)

        for uid, times in users.items():
            ordered = [t for t in order if t in times]
            result += f"<@{uid}>: {', '.join(ordered)}\n"

        channel = discord.utils.get(interaction.guild.text_channels, name="availability")
        if channel:
            await channel.send(result)
            await interaction.followup.send("✅ Sent to #availability", ephemeral=True)
        else:
            await interaction.followup.send(result, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AvailabilityScheduler(bot))
