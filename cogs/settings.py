from discord.ext import commands, tasks
from typing import DefaultDict, List, Dict, Optional
import discord
import logging
import asyncio
import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from .utils.resolver import get_text_channel_id


@dataclass
class Server:
    """
    Server settings class
    """

    guild_id: int
    prefix: str = ",,"
    log_channel_id: Optional[int] = None
    category_clock_id: Optional[int] = None
    category_clock_format: Optional[str] = None
    jp_role_id: Optional[int] = None
    hc_role_id: Optional[int] = None
    hc_ignored_channel_ids: List[int] = field(default_factory=list)
    ignored_channel_ids: List[int] = field(default_factory=list)
    ignored_prefixes: List[str] = field(default_factory=list)
    emoji_role_message_id: Optional[int] = None
    emoji_roles: Dict[int, str] = field(default_factory=dict)
    clubs: List[int] = field(default_factory=list)
    bookmark_emoji: str = "\N{BOOKMARK}"

    # hidden fields
    _mod_log_channel_id: Optional[int] = None
    _mod_channel_ids: List[int] = field(default_factory=list)
    _watched_user_ids: List[int] = field(default_factory=list)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        object.__setattr__(self, key, value)


async def has_manage_server(ctx):
    return ctx.author.guild_permissions.manage_guild


class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings: Dict[int, Server] = {}
        self.bot.settings = self
        self._lock = asyncio.Lock()
        self.backup.start()

        if bot.is_ready():
            self.load()

    def __getitem__(self, key):
        if key in self.settings:
            return self.settings[key]
        else:
            logging.error(f"Tried to get settings of a non-existent guild {key}")
            return None

    def load(self):
        for guild in self.bot.guilds:
            filename = f"{guild.id}-settings.json"
            try:
                with open(filename, "r") as data:
                    server_settings = json.load(data)
                    self.settings[guild.id] = Server(**server_settings)
                    logging.info(f"Successfully loaded {filename}")
            except FileNotFoundError:
                self.settings[guild.id] = Server(guild_id=guild.id)
                logging.info(f"{filename} not found. Using initial settings.")

    def restore(self, guild, date):
        date_str = date.strftime("%Y-%m-%d")
        filename = f"backups/{guild.id}-settings-{date_str}.json"
        try:
            with open(filename, "r") as data:
                server_settings = json.load(data)
                self.settings[guild.id] = Server(**server_settings)
        except FileNotFoundError:
            logging.error(f"{filename} not found")

    def save(self, guild):
        with open(f"{guild.id}-settings.json", "w+") as output:
            json.dump(asdict(self.settings[guild.id]), output, indent=4)

    @commands.command(aliases=["settings"])
    @commands.check(has_manage_server)
    async def config(self, ctx):
        """Show server settings."""
        shown_settings = asdict(self.settings[ctx.guild.id])
        if get_text_channel_id(ctx.channel) not in shown_settings["_mod_channel_ids"]:
            for key in [k for k in shown_settings.keys() if k.startswith("_")]:
                del shown_settings[key]

        settings = json.dumps(shown_settings, indent=4)
        await ctx.send(f"```{settings}```")

    @commands.command(aliases=["setjp"])
    @commands.check(has_manage_server)
    async def set_jp_role(self, ctx, jp_role_id: int):
        old_id = self.settings[ctx.guild.id].jp_role_id
        self.update_settings(ctx.guild, jp_role_id=jp_role_id)
        if old_id is None:
            await ctx.send(
                f"This server's Japanese Role has been set to <@&{jp_role_id}>"
            )
        else:
            await ctx.send(
                f"This server's Japanese Role has been changed from <@&{old_id}>  to <@&{jp_role_id}>"
            )

    @commands.command()
    @commands.check(has_manage_server)
    async def set_mod_channels(
        self, ctx, channels: commands.Greedy[discord.TextChannel]
    ):
        channel_ids = [c.id for c in channels]
        self.update_settings(ctx.guild, _mod_channel_ids=channel_ids)
        await ctx.send(
            f"\N{WHITE HEAVY CHECK MARK} Mod channels have been set to {', '.join([c.mention for c in channels])}"
        )

    @commands.command(aliases=["ignore"])
    @commands.check(has_manage_server)
    async def set_ignore_channels(
        self, ctx, channels: commands.Greedy[discord.TextChannel]
    ):
        channel_ids = [c.id for c in channels]
        self.update_settings(ctx.guild, ignored_channel_ids=channel_ids)
        await ctx.send(
            f"\N{WHITE HEAVY CHECK MARK} Ignored channels have been set to {', '.join([c.mention for c in channels])}"
        )

    @commands.command(aliases=["setlog"])
    @commands.check(has_manage_server)
    async def set_log_channel(self, ctx, *, channel: discord.TextChannel):
        self.update_settings(ctx.guild, log_channel_id=get_text_channel_id(channel))
        await ctx.send(
            f"\N{WHITE HEAVY CHECK MARK} Log channel has been set to {channel}"
        )

    @commands.Cog.listener()
    async def on_ready(self):
        self.load()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.settings[guild.id] = Server(guild_id=guild.id)

    @tasks.loop(hours=24)
    async def backup(self):
        today = datetime.now().strftime("%Y-%m-%d")
        for guild in self.bot.guilds:
            await self.run_process(
                f"cp {guild.id}-settings.json backups/{guild.id}-settings-{today}.json"
            )

    def update_settings(self, guild, **kwargs):
        for key, value in kwargs.items():
            self.settings[guild.id][key] = value
        self.save(guild)

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]


async def setup(bot):
    await bot.add_cog(Settings(bot))
