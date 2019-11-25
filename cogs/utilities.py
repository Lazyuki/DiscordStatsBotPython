from discord.ext import commands
from datetime import datetime
import discord
import logging

BOOSTER_COLOR = 0xf47fff


class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings

    @commands.command()
    async def boosters(self, ctx):
        """Show Nitro Boosters"""
        embed = discord.Embed(colour=BOOSTER_COLOR)
        embed.title = f'Nitro Boosters: {len(ctx.guild.premium_subscribers)} members'
        embed.description = '\n'.join([f'**{sub}** - ' + sub.premium_since.strftime('%Y/%m/%d') for sub in sorted(ctx.guild.premium_subscribers, key=lambda m: m.premium_since)])
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'Nitro Boosts: {ctx.guild.premium_subscription_count} (Tier {ctx.guild.premium_tier})')
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Utilities(bot))