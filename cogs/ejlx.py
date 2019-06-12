from discord.ext import commands
import discord
import asyncio
import re
from .utils.resolver import has_role

EJLX_ID = 189571157446492161

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

# Languages
LANGS = ['german', 'italian', 'french', 'spanish',
    'portuguese', 'korean', 'chinese', 'telugu', 'hindi', 'urdu', 'tamil', 'malay',
    'dutch', 'arabic', 'russian', 'turkish', 'mandarin', 'cantonese', 'polish', 'swedish',
    'tagalog', 'norwegian']

COUNTRIES = ['germany', 'italy', 'france', 'spain', 'portugal', 'brazil', 'korea', 'china',
    'taiwan', 'india', 'malaysia', 'netherland', 'russia', 'poland', 'sweden', 'turkey', 'norway']

NATIVE = re.compile(r'native(?: language)?(?: is)? (\S+)')
NATIVEJP = re.compile(r'母国?語.(.+?)語')
FROM = re.compile(r"i(?:'?m| am) from (?:the )?(?:united )?(\S+)")
IM = re.compile(r"i(?:'?m| am)(?: a)? (\S+)")
STUDY = re.compile(r'(?:learn|study|fluent in)(?:ing)? (?:japanese|english)')
STUDYJP = re.compile(r'(?:日本語|英語).?勉強')

# Emojis
JP_EMOJI = '<:japanese:439733745390583819>'
EN_EMOJI = '<:english:439733745591779328>'
OL_EMOJI = '<:other_lang:439733745491116032>'

# Helpers
async def has_manage_roles(ctx):
    return ctx.author.guild_permissions.manage_roles

async def jp_only(message):
    pass

async def check_kanji(message):
    pass

async def check_lang_switch(message):
    pass

async def guess_lang(message):
    msg =  message.content.lower()
    m = NATIVE.search(msg)
    if m:
        nat = m.group(1)
        if nat == 'japanese':
            await message.add_reaction(JP_EMOJI)
        elif nat == 'english':
            await message.add_reaction(EN_EMOJI)
        else:
            await message.add_reaction(OL_EMOJI)
        return
    m = NATIVEJP.search(msg)
    if m:
        nat = m.group(1)
        if nat == '日本':
            await message.add_reaction(JP_EMOJI)
        elif nat == '英':
            await message.add_reaction(EN_EMOJI)
        else:
            await message.add_reaction(OL_EMOJI)
        return
    m = FROM.search(msg)
    if m:
        orig = m.group(1)
        if orig == 'japan':
            await message.add_reaction(JP_EMOJI)
            return 
        elif orig in ['us', 'states', 'kingdom', 'uk', 'canada', 'australia']:
            await message.add_reaction(EN_EMOJI)
            return
        elif orig in COUNTRIES:
            await message.add_reaction(OL_EMOJI)
            return
    m = IM.search(msg)
    if m:
        orig = m.group(1)
        if orig == 'japanese':
            await message.add_reaction(JP_EMOJI)
            return 
        elif orig in ['english', 'canadian', 'australian', 'british']:
            await message.add_reaction(EN_EMOJI)
            return
        elif orig in LANGS:
            await message.add_reaction(OL_EMOJI)
            return
    if '日本人です' in msg:
        await message.add_reaction(JP_EMOJI)
        return 
    elif 'アメリカ人' in msg or 'イギリス人' in msg or 'カナダ人' in msg or 'オーストラリア人' in msg:
        await message.add_reaction(EN_EMOJI)
        return 
    for w in msg.split():
        if w in LANGS or w in COUNTRIES:
            await message.add_reaction(OL_EMOJI)
            return
    msg = STUDY.sub('', msg)
    msg = STUDYJP.sub('', msg)   
    if 'japanese' in msg or '日本語' in msg:
        await message.add_reaction(JP_EMOJI)
        return 
    if 'english' in msg or '英語' in msg:
        await message.add_reaction(EN_EMOJI)
        return 
        

class EJLX(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
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
            
        await asyncio.gather(
            msg.author.add_roles(msg.guild.get_role(tagged), reason=f'by {user.name}'),
            msg.author.remove_roles(msg.guild.get_role(NU_ROLE['id']), reason=f'by {user.name}')
        )

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


def setup(bot):
    bot.add_cog(EJLX(bot))