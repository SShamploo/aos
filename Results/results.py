import discord
from discord.ext import commands

class MatchReportModal(discord.ui.Modal, title="Match Report Form"):
    match_type = discord.ui.TextInput(label="Match Type")
    league = discord.ui.TextInput(label="League")
    enemy_team = discord.ui.TextInput(label="Enemy Team")
    map_played = discord.ui.TextInput(label="Map")
    win_loss = discord.ui.TextInput(label="W/L", placeholder="Win or Loss")
    final_score = discord.ui.TextInput(label="Final Score", placeholder="e.g. 13-9")

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title="📊 Match Report", color=discord.Color.blurple())
        embed.add_field(name="Match Type", value=self.match_type.value, inline=False)
        embed.add_field(name="League", value=self.league.value, inline=False)
        embed.add_field(name="Enemy Team", value=self.enemy_team.value, inline=False)
        embed.add_field(name="Map", value=self.map_played.value, inline=False)
        embed.add_field(name="W/L", value=self.win_loss.value, inline=True)
        embed.add_field(name="Final Score", value=self.final_score.value, inline=True)
        embed.set_footer(text=f"Submitted by {interaction.user}", icon_url=interaction.user.display_avatar.url)

        results_channel = discord.utils.get(interaction.guild.text_channels, name="results")
        if results_channel:
            await results_channel.send(embed=embed)
            await interaction.response.send_message("✅ Match report submitted!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 'results' channel not found.", ephemeral=True)

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="results")
    async def results(self, ctx):
        await ctx.send_modal(MatchReportModal())

# ✅ Updated for discord.py v2+
async def setup(bot):
    await bot.add_cog(MatchResults(bot))
