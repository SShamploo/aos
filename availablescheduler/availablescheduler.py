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

        # ✅ Google Sheets setup and exposed sheet
        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.gc = gspread.authorize(creds)
        self.sheet = self.gc.open("AOS").worksheet("availability")

    @app_commands.command(name="sendavailability", description="Send availability message (HC/AL)")
    async def sendavailability(self, interaction: discord.Interaction):
        await interaction.response.send_message("Select a League:", view=LeagueSelectView(self, "send"), ephemeral=True)

    @app_commands.command(name="deleteavailability", description="Delete availability messages from this channel")
    async def deleteavailability(self, interaction: discord.Interaction):
        await interaction.response.send_message("Deleting availability messages in this channel...", ephemeral=True)

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
            self.sent_messages[channel_id] = {}

        # Delete rows in Google Sheet that match message IDs from this channel
        try:
            all_rows = self.sheet.get_all_values()
            msg_ids = self.sent_messages.get(channel_id, {}).keys()
            to_delete = [
                i + 2 for i, row in enumerate(all_rows[1:])
                if row[4] in msg_ids
            ]
            for i in reversed(to_delete):
                self.sheet.delete_rows(i)
        except Exception as e:
            print(f"⚠️ Failed to delete from Google Sheet: {e}")

        await interaction.followup.send(f"🗑️ Deleted {deleted} messages and Google Sheet rows.", ephemeral=True)

    @app_commands.command(name="availability", description="View availability by league and day")
    async def availability(self, interaction: discord.Interaction):
        await interaction.response.send_message("Select a League to view:", view=LeagueSelectView(self, "view"), ephemeral=True)

    async def handle_send(self, interaction, league):
        emoji_names = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12AM"]
        emojis = []
        for name in emoji_names:
            emoji = discord.utils.get(interaction.guild.emojis, name=name)
            if emoji:
                emojis.append(emoji)
            else:
                await interaction.followup.send(f"❌ Emoji `{name}` not found in server.", ephemeral=True)
                return

        today = datetime.now().date()
        sunday = today - timedelta(days=(today.weekday() + 1) % 7)

        self.sent_messages[interaction.channel.id] = {}

        for i in range(7):
            day = sunday + timedelta(days=i)
            label = f"{day.strftime('%A').upper()} {day.strftime('%m/%d')} | {league}"
            msg = await interaction.channel.send(f"**{label}**")
            for emoji in emojis:
                await msg.add_reaction(emoji)
            self.sent_messages[interaction.channel.id][str(msg.id)] = label

    async def handle_view(self, interaction, league):
        await interaction.followup.send("Select a day to view:", view=DaySelectView(self, league), ephemeral=True)

    async def post_day_summary(self, interaction, league, day):
        rows = self.sheet.get_all_values()[1:]
        relevant = [r for r in rows if r[5].startswith(day.upper()) and r[6] == league]

        if not relevant:
            await interaction.followup.send(f"⚠️ No data found for {league} - {day}.", ephemeral=True)
            return

        order = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12AM"]
        result = f"**{day.upper()}**\n"
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

class LeagueSelectView(discord.ui.View):
    def __init__(self, cog, action):
        super().__init__(timeout=30)
        self.cog = cog
        self.action = action

    @discord.ui.select(
        placeholder="Select League",
        options=[
            discord.SelectOption(label="HC", value="HC"),
            discord.SelectOption(label="AL", value="AL"),
        ]
    )
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        league = select.values[0]
        if self.action == "send":
            await self.cog.handle_send(interaction, league)
        elif self.action == "delete":
            await self.cog.deleteavailability(interaction)
        elif self.action == "view":
            await self.cog.handle_view(interaction, league)

class DaySelectView(discord.ui.View):
    def __init__(self, cog, league):
        super().__init__(timeout=30)
        self.cog = cog
        self.league = league

    @discord.ui.select(
        placeholder="Select Day",
        options=[discord.SelectOption(label=day.upper(), value=day.upper()) for day in
                 ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]]
    )
    async def select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer()
        day = select.values[0]
        await self.cog.post_day_summary(interaction, self.league, day)

async def setup(bot):
    await bot.add_cog(AvailabilityScheduler(bot))
