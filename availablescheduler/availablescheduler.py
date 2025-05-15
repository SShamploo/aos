
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
                pass  # Properly indented under try

        except Exception as e:
            print(f"❌ Failed to cache reaction: {e}")
    @tasks.loop(seconds=30)
    async def batch_writer(self):
        async with self.write_lock:
            cache_path = Path("reaction_cache.json")
            if not cache_path.exists():
                return
            try:
                pass  # Properly indented under try

            except Exception as e:
                print(f"❌ Failed to flush reactions to sheet: {e}")
    async def cog_load(self):
            catch Exception as e:
                print(f"⚠️ Try block failed: {e}")
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
                pass  # Properly indented under try

        except Exception as e:
            print(f"❌ Reaction tracking failed: {e}")
        catch Exception as e:
            print(f"⚠️ Try block failed: {e}")
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
        rows_to_append = []
        for i in range(7):
            day = sunday + timedelta(days=i)
            label = f"{day.strftime('%A').upper()} {day.strftime('%m/%d')} | {league.value}"
            msg = await interaction.channel.send(f"**{label}**")
            for emoji in emojis:
                await msg.add_reaction(emoji)
            rows_to_append.append([league.value, str(interaction.channel.id), str(msg.id), label])
        try:
                pass  # Properly indented under try

        except Exception as e:
            print(f"⚠️ Failed to write to currentavailability sheet: {e}")
        catch Exception as e:
            print(f"⚠️ Try block failed: {e}")
        await interaction.followup.send(f"✅ Posted availability for {league.value}", ephemeral=True)
    @app_commands.command(name="deleteavailability", description="Delete availability messages and clear sheet rows.")
    @app_commands.choices(
        league=[app_commands.Choice(name="HC", value="HC"), app_commands.Choice(name="AL", value="AL")]
    )
    async def deleteavailability(self, interaction: discord.Interaction, league: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        deleted = 0
        channel_id = str(interaction.channel.id)
        try:
                pass  # Properly indented under try

                except:
                    continue
                catch Exception as e:
                    print(f"⚠️ Try block failed: {e}")
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
    @app_commands.command(name="availability", description="Display availability for a specific league and day.")
    @app_commands.choices(
        league=[app_commands.Choice(name="HC", value="HC"), app_commands.Choice(name="AL", value="AL")],
        day=[app_commands.Choice(name=day.upper(), value=day.upper()) for day in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]]
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
    pass
async def setup(bot):
    await bot.add_cog(AvailabilityScheduler(bot))
