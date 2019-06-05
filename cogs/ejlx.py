from discord.ext import commands
import discord
import asyncio
import re
from .utils.resolver import has_role

JHO = 189571157446492161
INTRO = 395741560840519680
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

NATIVE = re.compile(r'native(?: language is)? (\S+)')
NATIVEJP = re.compile(r'母国?語.(.+?)語')
FROM = re.compile(r"i(?:'?m| am) from (?:the )?(?:united )?(\S+)")
IM = re.compile(r"i(?:'?m| am)(?: a)? (\S+)")
STUDY = re.compile(r'(?:learn|study|fluent in)(?:ing)? (?:japanese|english)')
STUDYJP = re.compile(r'(?:日本語|英語).勉強')

JP_ROLE = '<:japanese:439733745390583819>'
EN_ROLE = '<:english:439733745591779328>'
OL_ROLE = '<:other_lang:439733745491116032>'

async def can_tag(ctx):
    return ctx.author.guild_permissions.manage_roles

class EJLX(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.newbies = []

    async def cog_check(self, ctx):
        return ctx.guild.id == 189571157446492161

    @commands.command()
    @commands.check(can_tag)
    async def tag(self, ctx, *, member: discord.Member = None):
        member = member or self.newbies[-1]
        pass

    @commands.Cog.listener()
    @commands.check(can_tag)
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
        if not user.guild_permissions.manage_roles:
            return
        emoji = str(reaction.emoji)
        tagged = None
        if emoji == JP_ROLE:
            tagged = 196765998706196480
        elif emoji == EN_ROLE:
            tagged = 197100137665921024
        elif emoji == OL_ROLE:
            tagged = 248982130246418433
        else:
            return
        await reaction.message.author.add_roles(reaction.message.guild.get_role(tagged), reason=f'by {user.name}')
        await reaction.message.author.remove_roles(reaction.message.guild.get_role(249695630606336000), reason=f'by {user.name}')

        if reaction.message.channel.id != INTRO:
            await reaction.message.channel.send(f"**{reaction.message.author.name}**, you've been tagged as <@&{tagged}> by {user.name}!")
            await reaction.message.clear_reactions()
        else:
            await asyncio.gather(
                reaction.remove(),
                reaction.message.remove_reaction(JP_ROLE, self.bot.user),
                reaction.message.remove_reaction(EN_ROLE, self.bot.user),
                reaction.message.remove_reaction(OL_ROLE, self.bot.user)
            )
            

    @commands.Cog.listener()
    async def on_safe_message(self, message, **kwargs):
        if not has_role(message.author, 249695630606336000):
            return
        msg =  message.content.lower()
        m = NATIVE.search(msg)
        if m:
            nat = m.group(1)
            if nat == 'japanese':
                await message.add_reaction(JP_ROLE)
            elif nat == 'english':
                await message.add_reaction(EN_ROLE)
            else:
                await message.add_reaction(OL_ROLE)
            return
        m = NATIVEJP.search(msg)
        if m:
            nat = m.group(1)
            if nat == '日本':
                await message.add_reaction(JP_ROLE)
            elif nat == '英':
                await message.add_reaction(EN_ROLE)
            else:
                await message.add_reaction(OL_ROLE)
            return
        m = FROM.search(msg)
        if m:
            orig = m.group(1)
            if orig == 'japan':
                await message.add_reaction(JP_ROLE)
                return 
            elif orig in ['us', 'states', 'kingdom', 'uk', 'canada', 'australia']:
                await message.add_reaction(EN_ROLE)
                return
            elif orig in COUNTRIES:
                await message.add_reaction(OL_ROLE)
                return
        m = IM.search(msg)
        if m:
            orig = m.group(1)
            if orig == 'japanese':
                await message.add_reaction(JP_ROLE)
                return 
            elif orig in ['english', 'canadian', 'australian', 'british']:
                await message.add_reaction(EN_ROLE)
                return
            elif orig in LANGS:
                await message.add_reaction(OL_ROLE)
                return
        msg = STUDY.sub('', msg)
        msg = STUDYJP.sub('', msg)
        if 'japanese' in msg or '日本語' in msg or '日本人です' in msg:
            await message.add_reaction(JP_ROLE)
            return 
        elif 'english' in msg or '英語' in msg or 'アメリカ人' in msg or 'イギリス人' in msg or 'カナダ人' in msg or 'オーストラリア人' in msg:
            await message.add_reaction(EN_ROLE)
            return 

        for w in msg.split():
            if w in LANGS or w in COUNTRIES:
                await message.add_reaction(OL_ROLE)
                return
        
def setup(bot):
    bot.add_cog(EJLX(bot))