import discord
from discord import app_commands
from discord.ext import commands

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="results", description="Submit a match report")
    @app_commands.describe(
        match_type="Type of match (e.g., Scrim, Ranked)",
        league="League name",
        enemy_team="Enemy team name",
        map_played="Map played",
        win_loss="Win or Loss",
        final_score="e.g., 13-9"
    )
    async def results(
        self,
        interaction: discord.Interaction,
        match_type: str,
        league: str,
        enemy_team: str,
        map_played: str,
        win_loss: str,
        final_score: str
    ):
        embed = discord.Embed(title="📊 Match Report", color=discord.Color.blurple())
        embed.add_field(name="Match Type", value=match_type, inline=False)
        embed.add_field(name="League", value=league, inline=False)
        embed.add_field(name="Enemy Team", value=enemy_team, inline=False)
        embed.add_field(name="Map", value=map_played, inline=False)
        embed.add_field(name="W/L", value=win_loss, inline=True)
        embed.add_field(name="Final Score", value=final_score, inline=True)
        embed.set_footer(text=f"Submitted by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if results_channel:
            await results_channel.send(embed=embed)
            await interaction.response.send_message("✅ Match report sent to #results!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Could not find a #results channel.", ephemeral=True)

# Required async setup
async def setup(bot):
    await bot.add_cog(MatchResults(bot))
