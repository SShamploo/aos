import discord
from discord.ext import commands
from discord import app_commands
import asyncio

CATEGORY_ID = 1360145897857482792
BASE_CHANNEL_NAME = "Join-To-Create-Voice-Chat"
CUSTOM_CHANNEL_NAME = "User Channel"
INACTIVITY_SECONDS = 300  # 5 minutes

class VoiceChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}     # {channel_id: asyncio.Task}
        self.assigned_users = set()   # Track users already moved to prevent duplication

    @app_commands.command(name="createautovoice", description="Create the Join-To-Create-Voice-Chat channel")
    async def createautovoice(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)

        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Invalid category ID or category not found.", ephemeral=True)
            return

        existing = discord.utils.get(guild.voice_channels, name=BASE_CHANNEL_NAME)
        if existing:
            await interaction.response.send_message("⚠️ Base channel already exists.", ephemeral=True)
            return

        vc = await guild.create_voice_channel(BASE_CHANNEL_NAME, category=category)
        await interaction.response.send_message(f"✅ Created voice channel: {vc.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # ✅ Prevent double creation by tracking already moved users
        if (
            after.channel
            and after.channel.name == BASE_CHANNEL_NAME
            and member.id not in self.assigned_users
        ):
            category = member.guild.get_channel(CATEGORY_ID)
            if not category:
                return

            # Create channel and move user
            new_channel = await member.guild.create_voice_channel(CUSTOM_CHANNEL_NAME, category=category)
            await member.move_to(new_channel)

            # Track this user to avoid duplication
            self.assigned_users.add(member.id)

            # Start cleanup timer
            self.start_deletion_timer(new_channel)

        # ✅ Start deletion timer when leaving a custom channel
        if before.channel and before.channel.id in self.active_channels:
            self.start_deletion_timer(before.channel)

        # ✅ Reset tracking if user leaves all voice channels
        if not after.channel and member.id in self.assigned_users:
            self.assigned_users.remove(member.id)

    def start_deletion_timer(self, channel):
        async def delete_if_empty():
            await asyncio.sleep(INACTIVITY_SECONDS)
            if len(channel.members) == 0:
                try:
                    await channel.delete()
                    self.active_channels.pop(channel.id, None)
                except Exception:
                    pass

        # Cancel previous task if exists
        if channel.id in self.active_channels:
            self.active_channels[channel.id].cancel()

        task = asyncio.create_task(delete_if_empty())
        self.active_channels[channel.id] = task

# Required setup
async def setup(bot):
    await bot.add_cog(VoiceChannelManager(bot))
