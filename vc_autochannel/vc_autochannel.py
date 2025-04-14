import discord
from discord.ext import commands
import asyncio

CATEGORY_ID = 1360145897857482792
BASE_CHANNEL_NAME = "Join-To-Create-Voice-Chat"
INACTIVITY_SECONDS = 300  # 5 minutes

class VoiceChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}  # {channel_id: task}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # If user joins the base channel
        if after.channel and after.channel.name == BASE_CHANNEL_NAME:
            category = member.guild.get_channel(CATEGORY_ID)
            if not category:
                return

            # Create a channel with user's display name
            vc_name = f"Voice - {member.display_name[:25]}"
            new_channel = await member.guild.create_voice_channel(name=vc_name, category=category)
            await member.move_to(new_channel)
            self.start_deletion_timer(new_channel)

        # If user leaves their custom voice channel
        if before.channel and before.channel.id in self.active_channels:
            self.start_deletion_timer(before.channel)

    def start_deletion_timer(self, channel):
        async def delete_if_empty():
            await asyncio.sleep(INACTIVITY_SECONDS)
            if len(channel.members) == 0:
                try:
                    await channel.delete()
                    self.active_channels.pop(channel.id, None)
                except Exception:
                    pass

        if channel.id in self.active_channels:
            self.active_channels[channel.id].cancel()

        task = asyncio.create_task(delete_if_empty())
        self.active_channels[channel.id] = task

    @commands.command(name="createautovoice")
    async def create_base_channel(self, ctx):
        """Manually creates the Join-To-Create voice channel."""
        guild = ctx.guild
        category = guild.get_channel(CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            return await ctx.send("❌ Invalid category ID.")

        existing = discord.utils.get(guild.voice_channels, name=BASE_CHANNEL_NAME)
        if existing:
            return await ctx.send("⚠️ Channel already exists.")

        vc = await guild.create_voice_channel(BASE_CHANNEL_NAME, category=category)
        await ctx.send(f"✅ Created voice channel: {vc.mention}")

# Required setup
async def setup(bot):
    await bot.add_cog(VoiceChannelManager(bot))
