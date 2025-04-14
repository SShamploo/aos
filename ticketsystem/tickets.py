import discord
from discord.ext import commands
from discord import app_commands
import asyncio

TICKET_CATEGORY_NAME = "Tickets"
TICKET_CHANNEL_PREFIX = "ticket"

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ticket_count = 0

    @app_commands.command(name="createticketpanel", description="Post the ticket panel for users to open tickets.")
    async def createticketpanel(self, interaction: discord.Interaction):
        view = TicketPanelView(self.bot, self)
        embed = discord.Embed(
            title="🎟️ Need Help?",
            description="Click the button below to open a ticket. Our team will assist you shortly.",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="closeticket", description="Close the current ticket.")
    async def closeticket(self, interaction: discord.Interaction):
        channel = interaction.channel

        if channel.name.startswith(TICKET_CHANNEL_PREFIX):
            await interaction.response.send_message("🛑 Closing ticket in 3 seconds...", ephemeral=True)
            await asyncio.sleep(3)
            await channel.delete()
        else:
            await interaction.response.send_message("❌ This is not a ticket channel.", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self, bot, cog):
        super().__init__(timeout=None)
        self.bot = bot
        self.cog = cog

    @discord.ui.button(label="Open Ticket", emoji="🎟️", style=discord.ButtonStyle.blurple)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        self.cog.ticket_count += 1
        ticket_number = self.cog.ticket_count
        ticket_name = f"{TICKET_CHANNEL_PREFIX}-{ticket_number:03}"

        guild = interaction.guild

        # Ensure category exists
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        # Define who can see the ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        # Optionally allow a "Staff" role to access
        staff_role = discord.utils.get(guild.roles, name="Staff")
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Create the channel
        ticket_channel = await guild.create_text_channel(
            name=ticket_name,
            category=category,
            overwrites=overwrites
        )

        await ticket_channel.send(f"🎫 Ticket created for {user.mention}. Use `/closeticket` to close this channel.")
        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)


# Required for cog loading
async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
