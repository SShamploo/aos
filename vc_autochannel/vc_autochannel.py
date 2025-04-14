import discord
from discord.ext import commands
from discord import app_commands
import asyncio

CATEGORY_ID = 1360145897857482792
BASE_CHANNEL_NAME = "Join-To-Create-Voice-Chat"
INACTIVITY_SECONDS = 300  # 5 minutes

class VoiceChannelManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_channels = {}     # {channel_id: asyncio.Task}
        self.user_channels = {}       # {user_id: channel_id}

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
        await interaction.response.send_message(f"✅ Created base voice channel: {vc.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Ignore if user already has an active channel
        if member.id in self.user_channels:
            return

        # When user joins the base VC
        if (
            after.channel
            and after.channel.name == BASE_CHANNEL_NAME
            and (not before.channel or before.channel.id != after.channel.id)
        ):
            category = member.guild.get_channel(CATEGORY_ID)
            if not category:
                return

            display_name = member.display_name[:25]
            channel_name = f"{display_name}'s Channel"

            new_channel = await member.guild.create_voice_channel(name=channel_name, category=category)
            await member.move_to(new_channel)

            self.user_channels[member.id] = new_channel.id
            self.start_deletion_timer(new_channel)

        # Start deletion timer when someone leaves their personal VC
        if before.channel and before.channel.id in self.active_channels:
            self.start_deletion_timer(before.channel)

        # Cleanup if user leaves all VCs
        if not after.channel and member.id in self.user_channels:
            self.user_channels.pop(member.id, None)

    def start_deletion_timer(self, channel):
        async def delete_if_empty():
            await asyncio.sleep(INACTIVITY_SECONDS)
            if len(channel.members) == 0:
                try:
                    await channel.delete()
                    self.active_channels.pop(channel.id, None)

                    # Remove from user tracking
                    for uid, cid in list(self.user_channels.items()):
                        if cid == channel.id:
                            self.user_channels.pop(uid)
                except Exception:
                    pass

        if channel.id in self.active_channels:
            self.active_channels[channel.id].cancel()

        task = asyncio.create_task(delete_if_empty())
        self.active_channels[channel.id] = task

# Required setup
async def setup(bot):
    await bot.add_cog(VoiceChannelManager(bot))
