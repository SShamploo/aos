import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timedelta

class HCAvailabilityScheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hcavailabilityscheduler", description="Post availability days and add time emojis")
    async def hcavailabilityscheduler(self, interaction: discord.Interaction):
        emoji_names = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12PM"]
        emojis = []

        for name in emoji_names:
            emoji = get(interaction.guild.emojis, name=name)
            if emoji:
                emojis.append(emoji)
            else:
                await interaction.response.send_message(f"Emoji '{name}' not found in this server.", ephemeral=True)
                return

        today = datetime.now().date()
        days_since_sunday = (today.weekday() + 1) % 7
        sunday = today - timedelta(days=days_since_sunday)

        await interaction.response.send_message("📅 Weekly Availability:", ephemeral=False)
        for i in range(7):
            current_day = sunday + timedelta(days=i)
            day_name = current_day.strftime("%A")
            date_str = current_day.strftime("%m/%d")
            message = await interaction.channel.send(f"{day_name} {date_str}")
            for emoji in emojis:
                await message.add_reaction(emoji)

# Required async setup function for loading the cog
async def setup(bot):
    await bot.add_cog(HCAvailabilityScheduler(bot))
