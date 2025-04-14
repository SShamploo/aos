import discord
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timedelta

class HCAvailabilityScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='hcavailabilityscheduler')
    async def hcavailabilityscheduler(self, ctx):
        """
        Sends each day of the current week (Sunday to Saturday) with corresponding dates,
        and reacts to each message with the specified custom emojis.
        """
        emoji_names = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12PM"]
        emojis = []

        for name in emoji_names:
            emoji = get(ctx.guild.emojis, name=name)
            if emoji:
                emojis.append(emoji)
            else:
                await ctx.send(f"Emoji '{name}' not found in this server.")
                return

        today = datetime.now().date()
        days_since_sunday = (today.weekday() + 1) % 7
        sunday = today - timedelta(days=days_since_sunday)

        for i in range(7):
            current_day = sunday + timedelta(days=i)
            day_name = current_day.strftime("%A")
            date_str = current_day.strftime("%m/%d")
            message = await ctx.send(f"{day_name} {date_str}")
            for emoji in emojis:
                await message.add_reaction(emoji)

# Required setup function for cogs
def setup(bot):
    bot.add_cog(HCAvailabilityScheduler(bot))
