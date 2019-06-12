from discord.ext import commands
import discord
import asyncio
import re
from .utils.resolver import has_role

INTRO = 395741560840519680
JHO = 189571157446492161
JP_CHAT = 189629338142900224
JP_BEGINNER = 208118574974238721
LANG_SWITCH = 376574779316109313
NF = 193966083886153729
NF_VOICE_TEXT = 390796551796293633
NF_VOICE = 196684007402897408
EWBF = 277384105245802497

LANG_ROLES = {
    196765998706196480: {
        'name': 'Native Japanese',
        'short': ['nj', 'jp']
    },
    270391106955509770: {
        'name': 'Fluent Japanese',
        'short': ['fj']
    },
    197100137665921024: {
        'name': 'Native English',
        'short': ['ne', 'en']
    },
    241997079168155649: {
        'name': 'Fluent English',
        'short': ['fe']
    },
    248982130246418433: {
        'name': 'Other Language',
        'short': ['ol']
    },
    249695630606336000: {
        'name': 'New User',
        'short': ['nu']
    },
}

LANGS = ['german', 'italian', 'french', 'spanish',
    'portuguese', 'korean', 'chinese', 'telugu', 'hindi', 'urdu', 'tamil', 'malay',
    'dutch', 'arabic', 'russian', 'turkish', 'mandarin', 'cantonese', 'polish', 'swedish',
    'tagalog', 'norwegian']

COUNTRIES = ['germany', 'italy', 'france', 'spain', 'portugal', 'brazil', 'korea', 'china',
    'india', 'malaysia', 'netherland', 'russia', 'poland', 'sweden', 'turkey', 'norwey']

NATIVE = re.compile(r'native(?: language)?(?: is)? (\S+)')
NATIVEJP = re.compile(r'母国?語.(.+?)語')
FROM = re.compile(r"i(?:'?m| am) from (?:the )?(?:united )?(\S+)")
IM = re.compile(r"i(?:'?m| am)(?: a)? (\S+)")
STUDY = re.compile(r'(?:learn|study|fluent in)(?:ing)? (?:japanese|english)')
STUDYJP = re.compile(r'(?:日本語|英語).?勉強')

JP_EMOJI = '<:japanese:439733745390583819>'
EN_EMOJI = '<:english:439733745591779328>'
OL_EMOJI = '<:other_lang:439733745491116032>'

# Helpers
async def can_tag(ctx):
    return ctx.author.guild_permissions.manage_roles


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
        return ctx.guild.id == 189571157446492161

    @commands.command()
    @commands.check(can_tag)
    async def tag(self, ctx, *, member: discord.Member = None):
        member = member or self.newbies[-1]
        pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.newbies.append(member.id)
        if len(self.newbies) > 3:
            self.newbies.pop(0)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if reaction.message.guild is None:
            return
        if self.bot.config.debugging:
            return
        if not user.guild_permissions.manage_roles:
            return
        emoji = str(reaction.emoji)
        tagged = None
        if emoji == JP_EMOJI:
            tagged = 196765998706196480
        elif emoji == EN_EMOJI:
            tagged = 197100137665921024
        elif emoji == OL_EMOJI:
            tagged = 248982130246418433
        else:
            return
    
        msg = reaction.message
        if not has_role(msg.author, 249695630606336000):
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
            msg.author.remove_roles(msg.guild.get_role(249695630606336000), reason=f'by {user.name}')
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
        if has_role(message.author, 249695630606336000):
            await guess_lang(message)
        
        


def setup(bot):
    bot.add_cog(EJLX(bot))