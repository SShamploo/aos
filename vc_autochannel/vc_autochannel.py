import discord
from discord.ext import commands
from discord import app_commands
import asyncio

CATEGORY_ID = 1360145897857482792
BASE_CHANNEL_NAME = "Join-To-Create-Voice-Chat"
INACTIVITY_SECONDS = 300  # 5 minutes
CHANNEL_PREFIX = "Bitch #"

class VoiceChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}         # {channel_id: task}
        self.created_for_user = {}        # {user_id: channel_id}

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
        # Exit if moved into a custom channel the bot already created
        if member.id in self.created_for_user:
            tracked_channel = self.created_for_user[member.id]
            if after.channel and after.channel.id == tracked_channel:
                return

        # User joined the base channel (not moving between VCs)
        if (
            after.channel
            and after.channel.name == BASE_CHANNEL_NAME
            and (not before.channel or before.channel.id != after.channel.id)
        ):
            category = member.guild.get_channel(CATEGORY_ID)
            if not category:
                return

            # Count existing channels named Bitch #
            count = sum(1 for ch in category.voice_channels if ch.name.startswith(CHANNEL_PREFIX))
            channel_name = f"{CHANNEL_PREFIX}{count + 1}"

            new_channel = await member.guild.create_voice_channel(name=channel_name, category=category)
            await member.move_to(new_channel)

            self.created_for_user[member.id] = new_channel.id
            self.start_deletion_timer(new_channel)

        # User left a bot-created voice channel
        if before.channel and before.channel.id in self.active_channels:
            self.start_deletion_timer(before.channel)

    def start_deletion_timer(self, channel):
        async def delete_if_empty():
            await asyncio.sleep(INACTIVITY_SECONDS)
            if len(channel.members) == 0:
                try:
                    await channel.delete()
                    self.active_channels.pop(channel.id, None)

                    # Remove users who were linked to this channel
                    self.created_for_user = {k: v for k, v in self.created_for_user.items() if v != channel.id}
                except Exception:
                    pass

        # Cancel previous timer if exists
        if channel.id in self.active_channels:
            self.active_channels[channel.id].cancel()

        task = asyncio.create_task(delete_if_empty())
        self.active_channels[channel.id] = task

# Required setup
async def setup(bot):
    await bot.add_cog(VoiceChannelManager(bot))
