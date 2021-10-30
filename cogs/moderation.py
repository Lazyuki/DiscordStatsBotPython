from discord.ext import commands
import discord
import logging
import asyncio
import asyncpg
import subprocess
import re

from discord.ext.commands.context import Context
from discord.permissions import PermissionOverwrite, Permissions

async def has_move_members(ctx):
    return ctx.author.guild_permissions.move_members

async def has_manage_messages(ctx):
    return ctx.author.guild_permissions.manage_messages

async def has_admin(ctx: Context):
    return ctx.author.guild_permissions.administrator

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings
        self.pool = bot.pool
        self.config = bot.config

    # @commands.command(aliases=['del'])
    # @commands.check(has_manage_messages)
    # async def delete(self, ctx, *, id):
    #     pass

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
    
    @commands.command(aliases=['chrp'])
    @commands.check(has_admin)
    async def channel_role_permissions(self, ctx: Context, role: commands.RoleConverter, *, permissions: str):
        """
        See https://discordpy.readthedocs.io/en/master/api.html#discord.Permissions for permission names.
        None is the default, False explicitly disables it, True explicitly allows it.
        Usage: ,,chrp role permission1=True, permission2=None, permission3=False... 
        Do not specify permissions if you want to remove permission overwrites from all channels.
        """
        if not role:
            await ctx.send(f'Usage: `,,chrp role permission1=True, permission2=None, permission3=False...`')
            return

        all_channels = [ch for ch in ctx.guild.text_channels if ch.category_id != 360570306131132417]
        
        if not permissions:
            # delete permission overwrites
            for ch in all_channels:
                if role in ch.overwrites:
                    await ch.set_permissions(role, overwrite=None)
            await ctx.send(f'Deleted permission overwrites for {str(role)}')
            return 

        permission_list = permissions.split(',')
        overwrite = PermissionOverwrite()
        for permission in permission_list:
            permission_key, permission_val = permission.split('=')
            permission_key = permission_key.strip()
            permission_val = permission_val.strip().title()
            if permission_val not in ['None', 'True', 'False']:
                await ctx.send(f'{permission_val} is not a valid permission value. Use True, False, or None')
                continue
            if permission_key in Permissions:
                overwrite[permission_key] = eval(permission_val)
            else:
                await ctx.send(f'{permission_key} is not a valid permission')
                continue

        for ch in all_channels:
            if role in ch.overwrites:
                if ch.overwrites_for(role) == overwrite:
                    continue
            await ch.set_permissions(role, overwrite=overwrite)
        
        await ctx.send("Finished applying role permissions")


            



        


            
def setup(bot):
    bot.add_cog(Moderation(bot))