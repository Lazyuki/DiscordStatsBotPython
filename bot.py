from discord.ext import commands
import discord
import datetime, re
import json, asyncio
import logging
import traceback
import sys

import config
import asyncpg
from cogs.utils.db import Database
from cogs.utils.parser import parse_language

description = """
Written by @Geralt#0007
"""

logging.basicConfig(level=logging.INFO)

default_extensions = (
    'cogs.owner',
    'cogs.statistics',
)

async def safe_message(message): pass

class Ciri(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=config.default_prefix,
                         fetch_offline_members=True)
        self.client_id = config.client_id
        self.owner_id = config.owner_id
        self.case_insensitive = True
        self.add_listener(safe_message)
        self.db = Database(self.config.db)

        for extension in default_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f'Failed to load extension {extension}.', file=sys.stderr)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.DisabledCommand):
            await ctx.author.send('Sorry. This command is disabled and cannot be used.')
        elif isinstance(error, commands.CommandInvokeError):
            print(f'In {ctx.command.qualified_name}:', file=sys.stderr)
            traceback.print_tb(error.original.__traceback__)
            print(f'{error.original.__class__.__name__}: {error.original}', file=sys.stderr)

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()
        await self.db.create_pool()
        guild_configs = await self.db.fetch('''
        SELECT * FROM guilds
        ''')
        self.config.guilds = { c['guild_id'] : c for c in guild_configs }
        for guild in self.guilds:
          if guild.id not in self.config.guilds:
            await self.db.fetch('''
              INSERT INTO guilds (guild_id) VALUES ($1)
            ''', guild.id)

        print(f'Ready: {self.user} (ID: {self.user.id})')
        print(f'Servers: {len(self.guilds)}')
        print('========================================')

    async def on_resumed(self):
        print('resumed...')

    async def on_guild_join(self, guild):
        await self.db.execute('''
          INSERT INTO guilds (guild_id) VALUES ($1)
        ''', guild.id)


    async def on_message(self, message):
        if message.author.bot: # no bots
            return
        if message.guild is None: # no PMs
            return
        lang, escaped, emojis = parse_language(message)
        self.dispatch('safe_message', message, lang=lang, escaped=escaped, emojis=emojis)
        await self.process_commands(message)

    async def process_commands(self, message):
        if message.author.bot:
            return
        # TODO: check aliases 
        ctx = await self.get_context(message)
        await self.invoke(ctx)
    
    async def post(self, channel, content=None, **kwargs):
      if self.config.debugging:
        print(f'Post to #{channel.name}: {content}')
        return
      await channel.send(content=content, **kwargs)

    async def close(self):
      await super().close()
      await self.db.close()

    @property
    def config(self):
        return __import__('config')

ciri = Ciri()
ciri.run(config.token)