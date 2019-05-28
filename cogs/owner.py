from discord.ext import commands
import discord
from collections import Counter, defaultdict
import logging
import asyncio
import asyncpg
from datetime import datetime, date

class Stats(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.db = bot.db
    self.config = bot.config
  
  @commands.command()
  async def kill(self, ctx):
    await ctx.send('See you space cowboy...')
    await self.bot.close()

  @commands.command()
  async def reload(self, ctx, *, module):
    try:
      self.bot.reload_extension(module)
    except commands.ExtensionError as e:
      await ctx.send(f'{e.__class__.__name__}: {e}')
    else:
      await ctx.send('\N{OK HAND SIGN}')


  async def cog_check(self, ctx):
    return await self.bot.is_owner(ctx.author)
      
def setup(bot):
  bot.add_cog(Stats(bot))