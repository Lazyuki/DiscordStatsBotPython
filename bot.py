from discord.ext import commands
import discord
import datetime, re
import pytz
import logging
import traceback
import sys

import config
from cogs.utils.parser import parse_language

timezone = pytz.timezone("Europe/London")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.typing = False

description = """
Ciri but better...?
Written by @Geralt#0007
"""

log = logging.getLogger(__name__)

initial_extensions = (
    "cogs.settings",
    "cogs.ejlx",
    "cogs.owner",
    "cogs.statistics",
    "cogs.moderation",
    "cogs.utilities",
)


async def safe_message(message):
    pass


PREFIX_OVERRIDES_REGEX = re.compile(rf'^,({"|".join(config.ciri_overrides)})(?:\s|$)')


def dynamic_prefix(bot, message):
    if message.content.startswith(","):
        if PREFIX_OVERRIDES_REGEX.match(message.content):
            return ","
    return config.default_prefix


class Cirilla(commands.Bot):
    def __init__(self, pool):
        super().__init__(
            command_prefix=dynamic_prefix, description=description, intents=intents
        )
        self.owner_id = config.owner_id
        self.case_insensitive = True
        self.add_listener(safe_message)
        self.pool = pool

    async def setup_hook(self):
        app = await self.application_info()
        self.owner_id = app.owner.id
        self.client_id = app.id
        for extension in initial_extensions:
            try:
                await self.load_extension(extension)
            except Exception as e:
                log.error(f"Failed to load extension {extension}\n{e}.")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.DisabledCommand):
            await ctx.send("This command is currently disabled.")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                f"For this command, I need permissions: {error.missing_permissions}"
            )
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send(f"CommandInvokeError: {error.original}")
            log.error(f"In {ctx.command.qualified_name}:")
            traceback.print_tb(error.original.__traceback__)
            log.error(f"{error.original.__class__.__name__}: {error.original}")
        else:
            await ctx.send(f"Unexpected Error: {error.original}")
            print(
                datetime.datetime.now(tz=timezone).strftime(
                    "%Y-%m-%d %H:%M:%S Command Error"
                ),
                file=sys.stderr,
            )
            traceback.print_tb(error.original.__traceback__)
            print("", file=sys.stderr)

    async def on_error(self, event_method: str, *args, **kwargs):
        print(
            datetime.datetime.now(tz=timezone).strftime(
                f"%Y-%m-%d %H:%M:%S Event Error"
            ),
            file=sys.stderr,
        )
        await super().on_error(event_method, *args, **kwargs)
        print("", file=sys.stderr)
        return

    async def on_ready(self):
        if not hasattr(self, "uptime"):
            self.uptime = datetime.datetime.utcnow()
        if self.user:
            log.info(f"Ready: {self.user} (ID: {self.user.id})")
        for guild in self.guilds:
            await self.pool.execute(
                """
                INSERT INTO guilds (guild_id)
                VALUES ($1)
                ON CONFLICT DO NOTHING
            """,
                guild.id,
            )
        log.info(f"Servers: {len(self.guilds)}")
        log.info("========================================")
        await self.change_presence(activity=discord.CustomActivity(",,help"))

    async def on_resumed(self):
        log.info("resumed...")

    async def on_message(self, message):
        if message.author.bot:  # no bots
            return
        if message.guild is None:  # no PMs
            return
        lang, escaped, emojis = parse_language(message)
        self.dispatch(
            "safe_message", message, lang=lang, escaped=escaped, emojis=emojis
        )
        await self.process_commands(message)

    async def process_commands(self, message):
        if message.author.bot:
            return
        # TODO: check aliases
        ctx = await self.get_context(message)
        await self.invoke(ctx)

    async def post(self, channel, content=None, **kwargs):
        if self.config.debugging:
            log.info(f"Post to #{channel.name}: {content}")
            return
        await channel.send(content=content, **kwargs)

    async def close(self):
        log.info(f"closing...")
        await super().close()

    @property
    def config(self):
        return __import__("config")
