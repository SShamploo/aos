
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
import base64
import gspread
from datetime import datetime
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

class MatchVoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv()

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = json.loads(base64.b64decode(os.getenv("GOOGLE_SHEETS_CREDS_B64")).decode("utf-8"))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        self.client = gspread.authorize(creds)
        self.matches_sheet = self.client.open("AOS").worksheet("matches")
        self.voicechats_sheet = self.client.open("AOS").worksheet("voicechats")

        self.category_id = 1360145897857482792
        self.midnight_task.start()

    def get_today_matches(self):
        today = datetime.now()
        today_strs = [
            today.strftime("%-m/%-d"),
            today.strftime("%-m/%d"),
            today.strftime("%m/%d"),
            today.strftime("%-m/%-d/%Y")
        ]
        rows = self.matches_sheet.get_all_values()[1:]
        return [row for row in rows if row[2].strip() in today_strs]

    def log_match_data(self, matches):
        for row in matches:
            if len(row) >= 9:
                match_id = row[8].strip()
                if not match_id or match_id.lower() == "match id":
                    continue
                enemy_team = row[4]
                league = row[5]
                date = row[2]
                time = row[3]
                players = row[7] if len(row) > 7 else "Unknown"
                name = f"{enemy_team} {league} {date} {time} {players}".strip()
                if name.lower() == "channel name":
                    continue
                self.voicechats_sheet.append_row([name, "", match_id], value_input_option="RAW")

    def clean_voicechats_log(self):
        rows = self.voicechats_sheet.get_all_values()
        seen_ids = set()
        to_keep = []

        for row in rows:
            if len(row) < 3:
                continue
            name = row[0].strip()
            match_id = row[2].strip()

            if not match_id or match_id.lower() == "match id":
                continue
            if name.lower() == "channel name":
                continue
            if match_id in seen_ids:
                continue
            seen_ids.add(match_id)
            to_keep.append([name, "", match_id])

        self.voicechats_sheet.clear()
        for row in to_keep:
            self.voicechats_sheet.append_row(row, value_input_option="RAW")

        return {row[2]: row[0] for row in to_keep}

    async def create_voice_channels(self, guild, match_data):
        category = guild.get_channel(self.category_id)
        if not category:
            print(f"❌ Category ID {self.category_id} not found in guild.")
            return

        for match_id, channel_name in match_data.items():
            try:
                vc = await guild.create_voice_channel(channel_name, category=category)
                all_rows = self.voicechats_sheet.get_all_values()
                for i, row in enumerate(all_rows):
                    if len(row) >= 3 and row[2] == match_id:
                        self.voicechats_sheet.update_cell(i + 1, 2, str(vc.id))
                        break
                print(f"✅ Created voice channel: {channel_name}")
            except Exception as e:
                print(f"❌ Failed to create voice channel '{channel_name}': {e}")

    async def create_today_voice_channels(self, guild):
        matches = self.get_today_matches()
        self.log_match_data(matches)
        filtered_matches = self.clean_voicechats_log()
        await self.create_voice_channels(guild, filtered_matches)

    @app_commands.command(name="creatematchvcs", description="Manually create today's match voice chats.")
    async def creatematchvcs(self, interaction: discord.Interaction):
        await self.create_today_voice_channels(interaction.guild)
        await interaction.response.send_message("✅ Match voice channels created for today.", ephemeral=True)

    @app_commands.command(name="clearmatchvcs", description="Clear all match voice channels listed in the voicechats tab.")
    async def clearmatchvcs(self, interaction: discord.Interaction):
        guild = interaction.guild
        deleted_channels = []

        voice_rows = self.voicechats_sheet.get_all_values()
        for row in voice_rows:
            try:
                vc = guild.get_channel(int(row[1]))
                if vc:
                    await vc.delete()
                    deleted_channels.append(vc.name)
            except Exception as e:
                print(f"⚠️ Could not delete voice channel {row[1]}: {e}")

        self.voicechats_sheet.clear()
        await interaction.response.send_message(f"🧹 Cleared {len(deleted_channels)} match voice channels.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def midnight_task(self):
        now = datetime.utcnow()
        if now.hour == 7 and now.minute == 0:  # 12AM PST
            if self.bot.guilds:
                guild = self.bot.guilds[0]
                await self.create_today_voice_channels(guild)
                print("🌙 Auto-created voice channels at midnight PST.")
            else:
                print("❌ No guilds found for midnight task.")

async def setup(bot):
    await bot.add_cog(MatchVoiceChannels(bot))
