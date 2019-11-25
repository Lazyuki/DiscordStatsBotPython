from discord.ext import commands
import discord
import asyncio
import re
import logging

from .utils.resolver import has_role
from .utils.parser import guess_lang, JP_EMOJI, EN_EMOJI, OL_EMOJI
from datetime import datetime

EJLX_ID = 189571157446492161

BOOSTER_COLOR = 0xf47fff

# Channels
INTRO = 395741560840519680
JHO = 189571157446492161
JP_CHAT = 189629338142900224
JP_BEGINNER = 208118574974238721
LANG_SWITCH = 376574779316109313
NF_CHANNEL = 193966083886153729
NF_VOICE_TEXT = 390796551796293633
NF_VOICE = 196684007402897408
EWBF = 277384105245802497

# Roles
NJ_ROLE = {
    'id': 196765998706196480,
    'short': ['nj', 'jp'],
}
FJ_ROLE = {
    'id': 270391106955509770,
    'short': ['fj'],
}
NE_ROLE = {
    'id': 197100137665921024,
    'short': ['ne', 'en'],
}
FE_ROLE = {
    'id': 241997079168155649,
    'short': ['fe'],
}
OL_ROLE = {
    'id': 248982130246418433,
    'short': ['ol'],
}
NU_ROLE = {
    'id': 249695630606336000,
    'short': ['nu'],
}
NF_ROLE = 196106229813215234
NF_ONLY_ROLE = 378668720417013760

ROLES = [NJ_ROLE, FJ_ROLE, NE_ROLE, FE_ROLE, OL_ROLE, NU_ROLE]
ROLE_IDS = [r['id'] for r in ROLES]

def get_role_by_short(short):
    for role in ROLES:
        if short in role['short']:
            return role
    return None

# Helpers
async def has_manage_roles(ctx):
    return ctx.author.guild_permissions.manage_roles

async def jp_only(message):
    pass

async def check_kanji(message):
    pass

async def check_lang_switch(message):
    pass
        
def is_in_ejlx():
    async def predicate(ctx):
        return ctx.guild and ctx.guild.id == EJLX_ID
    return commands.check(predicate)

class EJLX(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings
        self.newbies = []
        self._role_lock = asyncio.Lock()
        self._recently_tagged = None

    async def cog_check(self, ctx):
        return ctx.guild.id == EJLX_ID

    @commands.command()
    @commands.check(has_manage_roles)
    async def tag(self, ctx, *, member: discord.Member = None):
        member = member or self.newbies[-1]
        pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != EJLX_ID:
            return
        self.newbies.append(member.id)
        if len(self.newbies) > 3:
            self.newbies.pop(0)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild.id != EJLX_ID:
            return
        if member.premium_since is not None:
            ewbf = member.guild.get_channel(EWBF)
            embed = discord.Embed(colour=BOOSTER_COLOR)
            embed.title = f"{member}'s boost is now gone..."
            embed.timestamp = datetime.utcnow()
            embed.set_footer(text=f'Nitro Boosts: {member.guild.premium_subscription_count} (Tier {member.guild.premium_tier})')
            await ewbf.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if after.guild.id != EJLX_ID:
            return
        # Boost change
        if before.premium_since != after.premium_since:
            logging.info(f'boost by {before} {before.premium_since} {after.premium_since}')
            ewbf = after.guild.get_channel(EWBF)
            logging.info(f'{ewbf.name} fetched')
            embed = discord.Embed(colour=BOOSTER_COLOR)
            logging.info(f'embed created')
            embed.timestamp = datetime.utcnow()
            logging.info(f'timestamp set')
            embed.set_footer(text=f'Nitro Boosts: {after.guild.premium_subscription_count} (Tier {after.guild.premium_tier})')
            logging.info(f'footer set')
            if before.premium_since is None:
                embed.title = f'{after.user} just boosted the server!'
                logging.info(f'add boost title set')
            else:
                embed.title = f'{after.user}\'s boost was removed/expired...'
                logging.info(f'remove boost title set')
            logging.info(f'sending boost embed...')
            await ewbf.send(embed=embed)
            logging.info(f'embed sent?')
            
        # Nickname change
        # if before.nick != after.nick:
        #     ewbf = before.guild.get_channel(EWBF)
        #     embed = discord.Embed(colour=0x4286f4)
        #     embed.timestamp = datetime.utcnow()
        #     embed.set_footer(text=f'{before.name} ({before.id})', icon_url=before.avatar_url)
        #     if before.nick is None:
        #         embed.description = f'**{before.name}**\'s nickname was set to **${after.nick}**'
        #     elif after.nick is None:
        #         embed.description = f'**{before.nick}**\'s nickname was removed'
        #     else:
        #         embed.description = f'**{before.nick}**\'s nickname was changed to **{after.nick}**'
        #     await ewbf.send(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if self.bot.config.debugging:
            return
        if user.bot:
            return
        if user.guild is None:
            return
        if user.guild.id != EJLX_ID:
            return
        if not user.guild_permissions.manage_roles:
            return
        emoji = str(reaction.emoji)
        tagged = None
        if emoji == JP_EMOJI:
            tagged = NJ_ROLE['id']
        elif emoji == EN_EMOJI:
            tagged = NE_ROLE['id']
        elif emoji == OL_EMOJI:
            tagged = OL_ROLE['id']
        else:
            return
    
        msg = reaction.message
        if not has_role(msg.author, NU_ROLE['id']):
            if msg.channel.id == INTRO:
                await asyncio.gather(
                    reaction.remove(user),
                    reaction.remove(self.bot.user),
                )
            else:
                await msg.clear_reactions()
            return

        async with self._role_lock:
            if msg.author.id == self._recently_tagged:
                await reaction.remove(user)
                return
            self._recently_tagged == msg.author.id
            
        await msg.author.add_roles(msg.guild.get_role(tagged), reason=f'by {user.name}')
        await msg.author.remove_roles(msg.guild.get_role(NU_ROLE['id']), reason=f'by {user.name}')

        if msg.channel.id == INTRO:
            await asyncio.gather(
                reaction.remove(user),
                reaction.remove(self.bot.user)
            )
        else:
            await asyncio.gather(
                msg.clear_reactions(),
                msg.channel.send(f"**{msg.author.name}**, you've been tagged as <@&{tagged}> by {user.name}!")
            )

    @commands.Cog.listener()
    async def on_safe_message(self, message, **kwargs):
        if self.bot.config.debugging:
            return
        if message.guild.id != EJLX_ID:
            return
        if has_role(message.author, NU_ROLE['id']):
            await guess_lang(message)
        if message.channel.id == JP_CHAT:
            await jp_only(message) # kwargs has lang info
        elif message.channel.id == JP_BEGINNER:
            await check_kanji(message)
        elif message.channel.id == LANG_SWITCH:
            await check_lang_switch(message)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild.id != EJLX_ID:
            return
        if message.author.bot:
            return
        if message.content.startswith(';report'):
            my_s = discord.utils.find(lambda g: g.id == 293787390710120449, self.bot.guilds)
            bot_log = my_s.get_channel(325532503567761408)
            await bot_log.send(f'{message.author} made a report in {message.author.channel}')

def setup(bot):
    bot.add_cog(EJLX(bot))