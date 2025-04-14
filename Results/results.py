import discord
from discord.ext import commands

class MatchResults(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="results")
    async def results_command(self, ctx, match_type, league, enemy_team, map_played, win_loss, final_score):
        embed = discord.Embed(title="📊 Match Report", color=discord.Color.blurple())
        embed.add_field(name="Match Type", value=match_type, inline=False)
        embed.add_field(name="League", value=league, inline=False)
        embed.add_field(name="Enemy Team", value=enemy_team, inline=False)
        embed.add_field(name="Map", value=map_played, inline=False)
        embed.add_field(name="W/L", value=win_loss, inline=True)
        embed.add_field(name="Final Score", value=final_score, inline=True)
        embed.set_footer(text=f"Submitted by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        results_channel = discord.utils.get(ctx.guild.text_channels, name="results")
        if results_channel:
            await results_channel.send(embed=embed)
            await ctx.send("✅ Match report sent to #results!")
        else:
            await ctx.send("❌ Could not find a #results channel.")

# Required async setup for discord.py v2+
async def setup(bot):
    await bot.add_cog(MatchResults(bot))

