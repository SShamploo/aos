import discord
from discord.ext import commands
from discord.utils import utcnow

LOG_CHANNEL_ID = 1350806413504544778  # Set to your actual log channel ID

class ActivityLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_log(self, guild: discord.Guild, embed: discord.Embed):
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if log_channel and log_channel.permissions_for(guild.me).send_messages:
            await log_channel.send(embed=embed)

    # Message Events
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        embed = discord.Embed(title="📥 Message Sent", description=message.content, color=discord.Color.green())
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.timestamp = message.created_at
        await self.send_log(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        embed = discord.Embed(title="✏️ Message Edited", color=discord.Color.orange())
        embed.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
        embed.add_field(name="Channel", value=before.channel.mention)
        embed.add_field(name="Before", value=before.content or "*empty*", inline=False)
        embed.add_field(name="After", value=after.content or "*empty*", inline=False)
        embed.timestamp = utcnow()
        await self.send_log(before.guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        embed = discord.Embed(title="❌ Message Deleted", description=message.content or "*empty*", color=discord.Color.red())
        embed.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.timestamp = utcnow()
        await self.send_log(message.guild, embed)

    # Member Events
    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(title="➕ Member Joined", description=member.mention, color=discord.Color.green())
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.timestamp = utcnow()
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(title="➖ Member Left", description=str(member), color=discord.Color.red())
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.timestamp = utcnow()
        await self.send_log(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        embed = discord.Embed(title="👤 Member Updated", color=discord.Color.blurple())
        changes = []

        if before.nick != after.nick:
            changes.append(f"**Nickname:** `{before.nick}` → `{after.nick}`")
        if before.roles != after.roles:
            before_roles = ", ".join(r.name for r in before.roles if r.name != "@everyone")
            after_roles = ", ".join(r.name for r in after.roles if r.name != "@everyone")
            changes.append(f"**Roles:** `{before_roles}` → `{after_roles}`")

        if changes:
            embed.set_author(name=str(after), icon_url=after.display_avatar.url)
            embed.description = "\n".join(changes)
            embed.timestamp = utcnow()
            await self.send_log(after.guild, embed)

    # Channel Events
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        embed = discord.Embed(title="📁 Channel Created", description=f"{channel.mention} (`{channel.name}`)", color=discord.Color.green())
        embed.timestamp = utcnow()
        await self.send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        embed = discord.Embed(title="🗑️ Channel Deleted", description=f"`{channel.name}`", color=discord.Color.red())
        embed.timestamp = utcnow()
        await self.send_log(channel.guild, embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.name != after.name:
            embed = discord.Embed(title="✏️ Channel Renamed", color=discord.Color.orange())
            embed.description = f"`{before.name}` → `{after.name}`"
            embed.timestamp = utcnow()
            await self.send_log(after.guild, embed)

    # Role Events
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        embed = discord.Embed(title="🔧 Role Created", description=f"`{role.name}`", color=discord.Color.green())
        embed.timestamp = utcnow()
        await self.send_log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        embed = discord.Embed(title="🗑️ Role Deleted", description=f"`{role.name}`", color=discord.Color.red())
        embed.timestamp = utcnow()
        await self.send_log(role.guild, embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if before.name != after.name:
            embed = discord.Embed(title="✏️ Role Renamed", description=f"`{before.name}` → `{after.name}`", color=discord.Color.orange())
            embed.timestamp = utcnow()
            await self.send_log(after.guild, embed)

# Required setup function
async def setup(bot):
    await bot.add_cog(ActivityLogger(bot))
