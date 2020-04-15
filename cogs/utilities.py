from discord.ext import commands
from datetime import datetime
import discord
import logging
import asyncio 

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

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Notify ban"""
        # Fetch audit log to get who banned them
        banner = None
        reason = None
        await asyncio.sleep(1)
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                banner = entry.user
                reason = entry.reason
                break
        
        embed = discord.Embed(colour=0x000000)
        embed.title = f'\N{CROSS MARK} **{user.name}#{user.discriminator}** was `banned`. ({user.id})'
        embed.description = f'*by* {banner if banner else "Unknown"}\n**Reason:** {reason if reason else "Unknown"}'
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'User Banned', icon_url=user.avatar_url_as(static_format='png'))
        chan = guild.get_channel(self.settings[guild.id].log_channel_id)
        if chan:
            await chan.send(embed=embed)


def setup(bot):
    bot.add_cog(Utilities(bot))