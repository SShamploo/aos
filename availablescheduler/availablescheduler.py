import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
import os
import json
import base64
import asyncio
from pathlib import Path
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from collections import deque, defaultdict

class AvailabilityScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reaction_queue = deque()
        self.write_lock = asyncio.Lock()

        load_dotenv()
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.gc = gspread.authorize(creds)
        self.sheet = self.gc.open("AOS").worksheet("availability")
        self.current_sheet = self.gc.open("AOS").worksheet("currentavailability")

    def cache_reaction(self, entry):
        cache_path = Path("reaction_cache.json")
        try:
            if cache_path.exists():
                with cache_path.open("r") as f:
                    data = json.load(f)
            else:
                data = []
            data.append(entry)
            with cache_path.open("w") as f:
                json.dump(data, f)
            print(f"📝 Cached reaction: {entry}")
        except Exception as e:
            print(f"❌ Failed to cache reaction: {e}")

    @tasks.loop(seconds=30)
    async def batch_writer(self):
        async with self.write_lock:
            cache_path = Path("reaction_cache.json")
            if not cache_path.exists():
                return
            try:
                with cache_path.open("r") as f:
                    data = json.load(f)
                if not data:
                    return
                rows = [
                    [r["timestamp"], r["user_name"], r["user_id"], r["emoji"], r["message_id"], r["message_text"], r["league"]]
                    for r in data
                ]
                self.sheet.append_rows(rows)
                print(f"📤 Attempting to upload {len(rows)} cached reactions...")
                with cache_path.open("w") as f:
                    json.dump([], f)
            except Exception as e:
                print(f"❌ Failed to flush reactions to sheet: {e}")

    async def cog_load(self):
        self.batch_writer.start()

    def cog_unload(self):
        self.batch_writer.cancel()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.handle_reaction(payload, "add")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.handle_reaction(payload, "remove")

    async def handle_reaction(self, payload, event_type: str):
        if payload.user_id == self.bot.user.id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return
        channel_id = str(payload.channel_id)
        message_id = str(payload.message_id)
        emoji = payload.emoji.name if isinstance(payload.emoji, discord.PartialEmoji) else str(payload.emoji)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            current_rows = self.current_sheet.get_all_values()[1:]
            matched_row = next((r for r in current_rows if r[1] == channel_id and r[2] == message_id), None)
            if not matched_row:
                return
            league = matched_row[0]
            full_text = matched_row[3]
            message_text = full_text.split()[0].upper()

            if event_type == "add":
                self.cache_reaction({
                    "timestamp": timestamp,
                    "user_name": member.name,
                    "user_id": str(member.id),
                    "emoji": emoji,
                    "message_id": message_id,
                    "message_text": message_text,
                    "league": league
                })
            elif event_type == "remove":
                rows = self.sheet.get_all_values()
                for i, row in enumerate(rows[1:], start=2):
                    if len(row) >= 7 and row[2] == str(payload.user_id) and row[3] == emoji and row[4] == message_id:
                        self.sheet.delete_rows(i)
                        print(f"🗑️ Removed: {emoji} by {member.name} on {message_text}")
                        break
        except Exception as e:
            print(f"❌ Reaction tracking failed: {e}")

    @app_commands.command(name="sendavailability", description="Post availability messages for a league.")
    @app_commands.choices(
        league=[app_commands.Choice(name="HC", value="HC"), app_commands.Choice(name="AL", value="AL")]
    )
    async def sendavailability(self, interaction: discord.Interaction, league: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        # Check if there is already an active message for this league
        existing_rows = self.current_sheet.get_all_values()[1:]
        for row in existing_rows:
            if row[0] == league.value:
                class ConfirmView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=60)
                        self.response = None

                    @discord.ui.button(label='Yes', style=discord.ButtonStyle.danger)
                    async def confirm(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                        self.response = 'yes'
                        await interaction_button.response.defer()
                        self.stop()

                    @discord.ui.button(label='No', style=discord.ButtonStyle.secondary)
                    async def cancel(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                        self.response = 'no'
                        await interaction_button.response.defer()
                        self.stop()
                        await interaction_button.followup.send('Thank you.', ephemeral=True)

                view = ConfirmView()
                await interaction.followup.send(
                    f'There is already a {league.value} Availability Sent out, Would you like to delete the previous one and send a new one?',
                    view=view, ephemeral=True
                )
                await view.wait()
                if view.response != 'yes':
                    return
                await self._delete_availability_data(str(interaction.channel.id), league.value)
                break

        # Check if there is already an active message for this league
        existing_rows = self.current_sheet.get_all_values()[1:]
        for row in existing_rows:
            if row[0] == league.value:
                class ConfirmView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=60)
                        self.response = None

                    @discord.ui.button(label='Yes', style=discord.ButtonStyle.danger)
                    async def confirm(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                        self.response = 'yes'
                        self.stop()

                    @discord.ui.button(label='No', style=discord.ButtonStyle.secondary)
                    async def cancel(self, interaction_button: discord.Interaction, button: discord.ui.Button):
                        self.response = 'no'
                        self.stop()

                view = ConfirmView()
                await interaction.followup.send(
                    f'There is already a {league.value} Availability Sent out, Would you like to delete the previous one and send a new one?',
                    view=view, ephemeral=True
                )
                await view.wait()
                if view.response != 'yes':
                    return
                await self._delete_availability_data(str(interaction.channel.id), league.value)
                break

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
        rows_to_append = []
        for i in range(7):
            day = sunday + timedelta(days=i)
            label = f"{day.strftime('%A').upper()} {day.strftime('%m/%d')} | {league.value}"
            msg = await interaction.channel.send(f"**{label}**")
            for emoji in emojis:
                await msg.add_reaction(emoji)
            rows_to_append.append([league.value, str(interaction.channel.id), str(msg.id), label])
        try:
            self.current_sheet.append_rows(rows_to_append)
        except Exception as e:
            print(f"⚠️ Failed to write to currentavailability sheet: {e}")
        await interaction.followup.send(f"✅ Posted availability for {league.value}", ephemeral=True)

    @app_commands.command(name="deleteavailability", description="Delete availability messages and clear sheet rows.")
    @app_commands.choices(
        league=[app_commands.Choice(name="HC", value="HC"), app_commands.Choice(name="AL", value="AL")]
    )
    async def deleteavailability(self, interaction: discord.Interaction, league: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        await self._delete_availability_data(str(interaction.channel.id), league.value)
        channel_id = str(interaction.channel.id)
        try:
            rows = self.current_sheet.get_all_values()[1:]
            to_delete = []
            msg_ids_to_delete = []
            for i, row in enumerate(rows):
                if row[0] == league.value and row[1] == channel_id:
                    to_delete.append(i + 2)
                    msg_ids_to_delete.append(row[2])
            for msg_id in msg_ids_to_delete:
                try:
                    msg = await interaction.channel.fetch_message(msg_id)
                    await msg.delete()
                    deleted += 1
                except:
                    continue
            avail_rows = self.sheet.get_all_values()
            avail_delete_rows = [
                i + 2 for i, row in enumerate(avail_rows[1:])
                if row[4] in msg_ids_to_delete and row[6] == league.value
            ]
            for i in reversed(avail_delete_rows):
                self.sheet.delete_rows(i)
            for i in reversed(to_delete):
                self.current_sheet.delete_rows(i)
        except Exception as e:
            print(f"⚠️ Error during deleteavailability: {e}")
        await interaction.followup.send(f"🗑️ Deleted {deleted} messages and cleaned up Google Sheets for {league.value}.", ephemeral=True)


    @app_commands.command(name="checkavailability", description="Check current availability numbers for HC or AL")
    @app_commands.choices(
        league=[
            app_commands.Choice(name="HC", value="HC"),
            app_commands.Choice(name="AL", value="AL"),
        ]
    )
    async def checkavailability(self, interaction: discord.Interaction, league: app_commands.Choice[str]):
        await interaction.response.defer()
        data = self.sheet.get_all_values()[1:]
        counts = defaultdict(lambda: defaultdict(int))
        for row in data:
            if len(row) < 7:
                continue
            _, _, _, emoji, _, message_text, row_league = row
            if row_league != league.value:
                continue
            day = message_text.upper()
            counts[day][emoji] += 1
        days = ["SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
        times = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12AM"]
        lines = [f"**AOS CURRENT {league.value} AVAILABILITY**"]
        for day in days:
            line = [f"{time} {counts[day][time]}" for time in times if counts[day][time] > 0]
            if line:
                lines.append(f"**{day}:** " + " | ".join(line))
        await interaction.followup.send("\n".join(lines))

    async def _delete_availability_data(self, channel_id, league_value):
        deleted = 0
        try:
            rows = self.current_sheet.get_all_values()[1:]
            to_delete = []
            msg_ids_to_delete = []
            for i, row in enumerate(rows):
                if row[0] == league_value and row[1] == channel_id:
                    to_delete.append(i + 2)
                    msg_ids_to_delete.append(row[2])
            channel = self.bot.get_channel(int(channel_id))
            for msg_id in msg_ids_to_delete:
                try:
                    msg = await channel.fetch_message(int(msg_id))
                    await msg.delete()
                    deleted += 1
                except:
                    continue
            avail_rows = self.sheet.get_all_values()
            avail_delete_rows = [
                i + 2 for i, row in enumerate(avail_rows[1:])
                if row[4] in msg_ids_to_delete and row[6] == league_value
            ]
            for i in reversed(avail_delete_rows):
                self.sheet.delete_rows(i)
            for i in reversed(to_delete):
                self.current_sheet.delete_rows(i)
        except Exception as e:
            print(f"⚠️ Error during internal availability deletion: {e}")

async def setup(bot):
    await bot.add_cog(AvailabilityScheduler(bot))
