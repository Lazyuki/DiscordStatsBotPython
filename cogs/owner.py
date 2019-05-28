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
    self.db = bot.db
    self.config = bot.config
  
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
      stdout = subprocess.check_output(['git', 'pull'])
      await ctx.send(str(stdout, 'utf-8'))

  @commands.command(aliases=['rs'])
  async def restart(self, ctx):
    await ctx.send('Restarting...')
    subprocess.call('sleep 3 && . ~/.venv/ciri/bin/activate && nohup python3 bot.py &', shell=True)
    await self.bot.close()

  @commands.command()
  async def update(self, ctx):
    async with ctx.typing():
      stdout = str(subprocess.check_output(['git', 'pull']), 'utf-8')
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
      try:
        stdout = subprocess.check_output(script, shell=True)
        await ctx.send(str(stdout, 'utf-8'))
      except Exception as e:
        await ctx.send(str(e))

  async def cog_check(self, ctx):
    return await self.bot.is_owner(ctx.author)
      
def setup(bot):
  bot.add_cog(Stats(bot))