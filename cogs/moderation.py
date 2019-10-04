from discord.ext import commands
import discord
import logging
import asyncio
import asyncpg
import subprocess
import re

async def has_move_members(ctx):
    return ctx.author.guild_permissions.move_members

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool
        self.config = bot.config

    @commands.command(aliases=['del'])
    async def delete(self, ctx, *, id):
        if not ctx.author.guild_permissions.manage_server:
            return

    @commands.command(aliases=['vk'])
    @commands.check(has_move_members)
    async def voice_kick(self, ctx, *, member: commands.MemberConverter):
        vc = member.voice
        if vc is None:
            await ctx.send(f'{member.name} is not in VC')
            return
        await member.move_to(None)
        await ctx.send(f'Kicked {member.name} from {vc.channel}')
    
    @voice_kick.error
    async def voice_kick_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send('Failed to get a member')

            
def setup(bot):
    bot.add_cog(Moderation(bot))