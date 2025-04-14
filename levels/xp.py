import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.utils import utcnow
import asyncio
from collections import defaultdict

XP_PER_MESSAGE = 5
XP_PER_MINUTE_VC = 10

class LevelSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_data = defaultdict(lambda: {"xp": 0, "level": 1, "vc_join": None})
        self.track_voice_time.start()

    def get_level_xp(self, level):
        return 100 * level

    def calculate_total_xp(self, user_id):
        data = self.xp_data[user_id]
        level = data["level"]
        base = sum(self.get_level_xp(lvl) for lvl in range(1, level))
        return base + data["xp"]

    async def handle_level_up(self, member: discord.Member, source_channel=None):
        data = self.xp_data[member.id]
        needed = self.get_level_xp(data["level"])

        while data["xp"] >= needed:
            data["level"] += 1
            data["xp"] -= needed
            needed = self.get_level_xp(data["level"])

            if source_channel:
                await source_channel.send(f"🎉 {member.mention} leveled up to **Level {data['level']}**!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        data = self.xp_data[message.author.id]
        data["xp"] += XP_PER_MESSAGE
        await self.handle_level_up(message.author, source_channel=message.channel)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        data = self.xp_data[member.id]

        if not before.channel and after.channel:
            data["vc_join"] = utcnow()

        elif before.channel and not after.channel:
            if data["vc_join"]:
                delta = (utcnow() - data["vc_join"]).total_seconds() // 60
                gained = int(delta * XP_PER_MINUTE_VC)
                data["xp"] += gained
                data["vc_join"] = None
                await self.handle_level_up(member)

    @tasks.loop(minutes=1)
    async def track_voice_time(self):
        now = utcnow()
        for user_id, data in self.xp_data.items():
            if data["vc_join"]:
                data["xp"] += XP_PER_MINUTE_VC
                user = self.bot.get_user(user_id)
                if user:
                    for guild in self.bot.guilds:
                        member = guild.get_member(user.id)
                        if member:
                            await self.handle_level_up(member)

    @track_voice_time.before_loop
    async def before_tracking(self):
        await self.bot.wait_until_ready()

    # 🧍 /rank
    @app_commands.command(name="rank", description="Check your current XP and level.")
    async def rank(self, interaction: discord.Interaction):
        user = interaction.user
        data = self.xp_data[user.id]
        total_xp = self.calculate_total_xp(user.id)
        next_level_xp = self.get_level_xp(data["level"])
        embed = discord.Embed(title=f"📊 Rank for {user.display_name}", color=discord.Color.blurple())
        embed.add_field(name="Level", value=data["level"])
        embed.add_field(name="XP", value=f"{data['xp']} / {next_level_xp}")
        embed.add_field(name="Total XP", value=total_xp)
        await interaction.response.send_message(embed=embed)

    # 🏆 /leaderboard
    @app_commands.command(name="leaderboard", description="View the top XP earners.")
    async def leaderboard(self, interaction: discord.Interaction):
        leaderboard = sorted(self.xp_data.items(), key=lambda x: self.calculate_total_xp(x[0]), reverse=True)[:10]
        embed = discord.Embed(title="🏆 XP Leaderboard", color=discord.Color.gold())
        for i, (user_id, data) in enumerate(leaderboard, start=1):
            user = self.bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            total = self.calculate_total_xp(user_id)
            embed.add_field(name=f"#{i} {name}", value=f"Level {data['level']} - {total} XP", inline=False)

        await interaction.response.send_message(embed=embed)

# Required setup
async def setup(bot):
    await bot.add_cog(LevelSystem(bot))
