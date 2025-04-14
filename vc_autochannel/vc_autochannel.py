import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio

CATEGORY_ID = 1360145897857482792
BASE_CHANNEL_NAME = "Join-To-Create-Voice-Chat"
INACTIVITY_SECONDS = 300  # 5 minutes

class VoiceChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}  # {channel_id: task}

    @app_commands.command(name="createautovoice", description="Creates a Join-to-Create voice channel.")
    async def createautovoice(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_ID)
        if not category or not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message("❌ Invalid category ID.", ephemeral=True)

        existing = discord.utils.get(guild.voice_channels, name=BASE_CHANNEL_NAME)
        if existing:
            return await interaction.response.send_message("⚠️ Channel already exists.", ephemeral=True)

        vc = await guild.create_voice_channel(BASE_CHANNEL_NAME, category=category)
        await interaction.response.send_message(f"✅ Created voice channel: {vc.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # User joins the base channel
        if after.channel and after.channel.name == BASE_CHANNEL_NAME:
            try:
                await member.send("🔊 What would you like to name your private voice channel?")
            except discord.Forbidden:
                return

            def check(m):
                return m.author == member and isinstance(m.channel, discord.DMChannel)

            try:
                response = await self.bot.wait_for("message", timeout=60, check=check)
                new_name = response.content.strip()[:32]
                category = member.guild.get_channel(CATEGORY_ID)

                new_channel = await member.guild.create_voice_channel(
                    name=new_name,
                    category=category,
                    user_limit=10
                )
                await member.move_to(new_channel)
                self.start_deletion_timer(new_channel)

                try:
                    await member.send(f"✅ Created voice channel: **{new_name}**.")
                except discord.Forbidden:
                    pass

            except asyncio.TimeoutError:
                try:
                    await member.send("⏰ You took too long. Cancelled channel creation.")
                except discord.Forbidden:
                    pass

        # If user leaves their custom channel
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

        # Cancel previous task if exists
        if channel.id in self.active_channels:
            self.active_channels[channel.id].cancel()

        task = asyncio.create_task(delete_if_empty())
        self.active_channels[channel.id] = task

# Required setup
async def setup(bot):
    await bot.add_cog(VoiceChannelManager(bot))
