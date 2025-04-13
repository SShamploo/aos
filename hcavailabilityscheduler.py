import discord
from discord.ext import commands
from discord.utils import get
from datetime import datetime, timedelta
import os

# Set up intents
intents = discord.Intents.default()
intents.message_content = True  # Enable access to message content

# Initialize the bot with the desired command prefix and intents
bot = commands.Bot(command_prefix="!", intents=intents)

# List of custom emoji names
emoji_names = ["5PM", "6PM", "7PM", "8PM", "9PM", "10PM", "11PM", "12PM"]

@bot.command(name='hcavailabilityscheduler')
async def hcavailabilityscheduler(ctx):
    """
    Sends each day of the current week (Sunday to Saturday) with corresponding dates,
    and reacts to each message with the specified custom emojis.
    """
    # Retrieve emoji objects from the guild
    emojis = []
    for name in emoji_names:
        emoji = get(ctx.guild.emojis, name=name)
        if emoji:
            emojis.append(emoji)
        else:
            await ctx.send(f"Emoji '{name}' not found in this server.")
            return  # Exit if any emoji is not found

    # Get today's date
    today = datetime.now().date()

    # Calculate the date for the most recent Sunday
    days_since_sunday = (today.weekday() + 1) % 7
    sunday = today - timedelta(days=days_since_sunday)

    # Send messages for each day of the week with corresponding dates
    for i in range(7):
        current_day = sunday + timedelta(days=i)
        day_name = current_day.strftime("%A")
        date_str = current_day.strftime("%m/%d")  # e.g., "04/13"
        message = await ctx.send(f"{day_name} {date_str}")
        for emoji in emojis:
            await message.add_reaction(emoji)

# Run the bot with your token from an environment variable
bot.run(os.getenv("DISCORD_TOKEN"))
