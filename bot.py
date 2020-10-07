from discord.ext import commands
import discord
import datetime, re
import json, asyncio
import logging
import traceback
import sys

import config
import asyncpg
from cogs.utils.parser import parse_language

description = """
Ciri but better...?
Written by @Geralt#0007
"""

log = logging.getLogger(__name__)

initial_extensions = (
    'cogs.settings',
    'cogs.ejlx',
    'cogs.owner',
    'cogs.statistics',
    'cogs.moderation',
    'cogs.utilities'
)

async def safe_message(message): pass

PREFIX_OVERRIDES_REGEX = re.compile(fr'^,(?:help\s)?({"|".join(config.ciri_overrides)})(?:\s|$)')
def dynamic_prefix(bot, message): 
    if message.content.startswith(','):
        if PREFIX_OVERRIDES_REGEX.match(message.content):
            return ','
    return config.default_prefix

class Cirilla(commands.Bot):
    def __init__(self, pool):
        super().__init__(command_prefix=dynamic_prefix,
                         description=description )
        self.client_id = config.client_id
        self.owner_id = config.owner_id
        self.case_insensitive = True
        self.add_listener(safe_message)
        self.pool = pool

        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                log.error(f'Failed to load extension {extension}\n{e}.')

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.DisabledCommand):
            await ctx.send('This command is currently disabled.')
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f'For this command, I need permissions: {error.missing_perms}')
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send(f'CommandInvokeError: {error.original}')
            log.error(f'In {ctx.command.qualified_name}:')
            traceback.print_tb(error.original.__traceback__)
            log.error(f'{error.original.__class__.__name__}: {error.original}')


    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = datetime.datetime.utcnow()

        log.info(f'Ready: {self.user} (ID: {self.user.id})')
        log.info(f'Servers: {len(self.guilds)}')
        log.info('========================================')

    async def on_resumed(self):
        log.info('resumed...')

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
        log.info(f'Post to #{channel.name}: {content}')
        return
      await channel.send(content=content, **kwargs)

    async def close(self):
      log.info(f'closing...')
      await super().close()

    @property
    def config(self):
        return __import__('config')
