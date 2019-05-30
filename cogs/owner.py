from discord.ext import commands
import discord
import logging
import asyncio
import asyncpg
import subprocess
import re

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pool = bot.pool
        self.config = bot.config

    # This cog is bot owner only
    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)
    
    @commands.command()
    async def kill(self, ctx):
        await ctx.send('See you space cowboy...')
        await self.bot.close()

    @commands.command(aliases=['rl', 'rc'])
    async def reload(self, ctx, *, module):
        try:
            self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        except e:
            await ctx.send(str(e))
        else:
            await ctx.send('\N{OK HAND SIGN}')

    @commands.command(aliases=['gpl'])
    async def git_pull(self, ctx):
        async with ctx.typing():
            stdout, stderr = await self.run_process('git pull')
            await ctx.send(stdout)

    @commands.command(aliases=['db'])
    async def db_fetch(self, ctx, *, query):
        async with ctx.typing():
            res = await self.pool.fetch(query)
            if res:
                await ctx.send([tuple(r) for r in res])
            else:
                await ctx.send('No rows returned')

    @commands.command(aliases=['rs'])
    async def restart(self, ctx):
        await ctx.send('Restarting...')
        await asyncio.create_subprocess_exec('sleep 3 && . ~/.venv/ciri/bin/activate && python3 launcher.py', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await self.bot.close()

    @commands.command()
    async def update(self, ctx):
        async with ctx.typing():
            stdout, stderr = await self.run_process('git pull')
            if 'bot.py' in stdout:
                await self.restart(ctx)
            else:
                cogs = re.findall(r'cogs/(.+?)\.py', stdout)
                if not cogs:
                    await ctx.send('Nothing to update')
                    return
                try:
                    for cog in cogs:
                        self.bot.reload_extension(f'cogs.{cog}')
                except commands.ExtensionError as e:
                    await ctx.send(f'{e.__class__.__name__}: {e}')
                except e:
                    await ctx.send(str(e))
                else:
                    await ctx.send('\N{OK HAND SIGN} Updated cogs {}'.format(', '.join(cogs)))
                

    @commands.command(aliases=['sh'])
    async def shell(self, ctx, *, script):
        async with ctx.typing():
            stdout, stderr = await self.run_process(script)
            await ctx.send(stdout)
            if stderr:
                await ctx.send('Error:\n' + stderr)
    
    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]
            
def setup(bot):
    bot.add_cog(Stats(bot))