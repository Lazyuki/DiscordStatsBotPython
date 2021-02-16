from discord.ext import commands
from typing import List
import discord
import asyncio
import re
import logging
from collections import namedtuple

from .utils.resolver import has_role, has_any_role
from .utils.parser import guess_lang, JP_EMOJI, EN_EMOJI, OL_EMOJI, asking_vc, REGEX_DISCORD_OBJ
from .utils.user_interaction import wait_for_reaction
from datetime import datetime

EJLX_ID = 189571157446492161

CLUB_COLOR = 0xc780f2
BOOSTER_COLOR = 0xf47fff
BOOSTER_PINK_ROLE = 590163584856752143

# Channels
INTRO = 395741560840519680
JHO = 189571157446492161
JP_CHAT = 189629338142900224
JP_BEGINNER = 208118574974238721
LANG_SWITCH = 376574779316109313
BOT_CHANNEL = 225828894765350913
VOICE_BOT_CHANNEL = 765626780450422805
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
CHAT_MUTE_ROLE = 259181555803619329
ACTIVE_STAFF_ROLE = 240647591770062848

ROLES = [NJ_ROLE, FJ_ROLE, NE_ROLE, FE_ROLE, OL_ROLE, NU_ROLE]
ROLE_IDS = [r['id'] for r in ROLES]
LANG_ROLE_IDS = [r for r in ROLE_IDS if r != NU_ROLE['id']]

MUSIC_BOT_REGEX = re.compile(r'^[%=>][a-zA-Z]+')
N_WORD_REGEX = re.compile(r'n(i|1)gg(e|3|a)r?s?')

def get_role_by_short(short):
    for role in ROLES:
        if short in role['short']:
            return role
    return None

# Helpers
async def has_manage_roles(ctx):
    return ctx.author.guild_permissions.manage_roles

async def has_manage_guild(ctx):
    return ctx.author.guild_permissions.manage_guild

class ClubRole:
    def __init__(self, role):
        self.role = role # discord.Role or str

    @classmethod
    async def convert(cls, ctx, argument):
        argument = re.sub(r'[<>]', '', argument, 2)
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except:
            role = next(filter(lambda r: argument.lower() == r.name.lower(), ctx.guild.roles), None)
            if not role:
                role = next(filter(lambda r: argument.lower() in r.name.lower(), ctx.guild.roles), argument)

        return cls(role)

class RaidWatcher:
    def __init__(self):
        self._bucket = []

    def add(self, user_id: int):
        pass

async def send_music_bot_notif(message):
    await message.channel.send(f'{message.author.mention} All music bot commands should be in <#{VOICE_BOT_CHANNEL}> now.')

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
        self.troll_msgs = []
        self.raidwatcher = RaidWatcher()

    async def cog_check(self, ctx):
        return ctx.guild.id == EJLX_ID

    # @commands.command()
    # @commands.check(has_manage_roles)
    # async def tag(self, ctx, *, member: discord.Member = None):
    #     member = member or self.newbies[-1]
    #     pass

    @commands.group(name='clubs', aliases=['club'], invoke_without_command=True)
    async def clubs(self, ctx):
        """
        List clubs
        """
        clubs: List[int] = self.settings[ctx.guild.id].clubs

        if not clubs:
            await ctx.send(f'There are no clubs set in this server. Set up clubs by using `{ctx.prefix}clubs add <Role> <Name>`')
            return
        
        Club = namedtuple('Club', 'name members mentionable joined')

        club_list = []
        invalid_roles = []
        guild = ctx.guild
        for role_id in clubs:
            role = guild.get_role(role_id)
            if not role:
                invalid_roles.append(role_id)
                continue
            club_list.append(Club(role.name, len(role.members), role.mentionable, role in ctx.author.roles))

        if len(invalid_roles):
            self.settings[guild.id].clubs = [c for c in clubs if c not in invalid_roles]
            self.settings.save(ctx.guild)
        club_list_str = '\n'.join([f'**{club.name}**{" (P)" if club.mentionable else ""}: {club.members} members{" (joined)" if club.joined else ""}' for club in sorted(club_list, key=lambda c: c.name)])

        embed = discord.Embed(colour=CLUB_COLOR)
        embed.title = f'List of Clubs'
        embed.description = f'To join a club, simply type `{ctx.prefix}join <club name>`\n(P) indicates roles that **can be pinged** by anyone\n\n{club_list_str}'
        await ctx.send(embed=embed)
        
    @clubs.command(name='add', aliases=['create'])
    @commands.check(has_manage_guild)
    async def club_add(self, ctx, *, clubRole: ClubRole):
        """
        Create a new club
        Example: `,club add Among Us`
        This uses an existing role or will create a new **mentionable** role `Among Us` which members can freely join.
        """
        created_role = False
        role = clubRole.role
        if isinstance(role, str):
            role = await ctx.guild.create_role(reason=f'Create Club Role issued by {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id})', name=role, mentionable=True)
            created_role = True
        
        if role >= ctx.author.top_role:
            await ctx.send(f'"{role.name}" is higher in hierarchy than your highest role')
            return

        role_id = role.id
        clubs = self.settings[ctx.guild.id].clubs
        if role_id in clubs:
            await ctx.send(f'"{role.name}" already is a club')
            return
        self.settings[ctx.guild.id].clubs.append(role_id)
        self.settings.save(ctx.guild)
        await ctx.send(f'\N{WHITE HEAVY CHECK MARK} Club "{role.name}" {"created with a new role" if created_role else "added"}')
        

    @clubs.command(name='delete', aliases=['remove', 'del', 'rem'])
    @commands.check(has_manage_guild)
    async def club_delete(self, ctx, *, clubRole: ClubRole):
        """
        Deletes the club
        Example: `,club delete Among Us`
        This will not delete the role itself for safety, so you need to delete it yourself.
        """
        role = clubRole.role
        if isinstance(role, str):
            await ctx.send(f'Club "{role}" does not exist')
            return
        
        role_id = role.id
        clubs = self.settings[ctx.guild.id].clubs
        if not role_id in clubs:
            await ctx.send(f'"{role.name}" is not a club')
            return
        self.settings[ctx.guild.id].clubs.remove(role_id)
        self.settings.save(ctx.guild)
        await ctx.send(f'\N{WHITE HEAVY CHECK MARK} Club "{role.name}" deleted. The role itself was not deleted, so if you need to, delete it yourself.') 

    @commands.command()
    async def join(self, ctx, *, clubRole: ClubRole):
        """
        Join a club
        Example: `,join among us`
        Club names are case insensitive, and can be partial
        """
        role = clubRole.role
        if isinstance(role, str):
            await ctx.send(f'Club "{role}" does not exist', delete_after=10)
            return

        clubs = self.settings[ctx.guild.id].clubs 
        if not role.id in clubs:
            await ctx.send(f'"{role.name}" is not a club')
            return
        if role in ctx.author.roles:
            await ctx.send(f'You are already in the club "{role.name}"')
            return
        try:
            await ctx.author.add_roles(role, reason=f'Self Assigning the Club Role')
            await ctx.send('\n'.join(filter(None, [f'\N{WHITE HEAVY CHECK MARK} Joined the club "{role.name}"', role.mentionable and 'Note that this role **can be pinged** by anyone in the server'])))
        except:
            await ctx.send(f'Failed to add the role {role.name}')

    @commands.command()
    async def leave(self, ctx, *, clubRole: ClubRole):
        """
        Leave a club
        Example: `,leave among us`
        Club names are case insensitive, and can be partial
        """

        role = clubRole.role
        if isinstance(role, str):
            await ctx.send(f'Club "{role}" does not exist', delete_after=10)
            return
        
        clubs = self.settings[ctx.guild.id].clubs 
        if not role.id in clubs:
            await ctx.send(f'"{role.name}" is not a club')
            return
        if not role in ctx.author.roles:
            await ctx.send(f'You are not in the club "{role.name}"', delete_after=10)
            return
        try:
            await ctx.author.remove_roles(role, reason=f'Self Assigning the Club Role')
            await ctx.send(f'\N{WHITE HEAVY CHECK MARK} Left the club "{role.name}"')
        except:
            await ctx.send(f'Failed to remove the role {role.name}')

    async def check_role_mentions(self, message):
        clubs = self.settings[message.guild.id].clubs
        for role in message.role_mentions:
            if role.id in clubs:
                embed = discord.Embed(colour=CLUB_COLOR)
                embed.title = f'Club "{role.name}" Pinged'
                embed.description = f'If you want to leave this club, type `,leave {role.name}`'
                embed.set_footer(text=f'pinged by {message.author.name}#{message.author.discriminator}')
                await message.channel.send(embed=embed)
            elif role.id == ACTIVE_STAFF_ROLE:
                self.staff_ping(message)


    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != EJLX_ID:
            return
        self.newbies.append(member.id)
        if len(self.newbies) > 3:
            self.newbies.pop(0)
        self.raidwatcher.add(member.id)


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
            ewbf = before.guild.get_channel(EWBF)
            embed = discord.Embed(colour=BOOSTER_COLOR)
            if before.premium_since is None:
                embed.title = f'{before} just boosted the server!'
            else:
                embed.title = f'{before}\'s boost was removed/expired...'
                await before.remove_roles(before.guild.get_role(BOOSTER_PINK_ROLE))
            embed.timestamp = datetime.utcnow()
            embed.set_footer(text=f'Nitro Boosts: {before.guild.premium_subscription_count} (Tier {before.guild.premium_tier})')
            await ewbf.send(embed=embed)
            
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

    async def handleRawReaction(self, payload, is_add):
        message_id = payload.message_id
        user_id = payload.user_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id
        emoji = payload.emoji

        cached = discord.utils.find(lambda m: m.id == message_id, self.bot.cached_messages)
        if cached:
            return

        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id)
        member = guild.get_member(user_id)
        message = await channel.fetch_message(message_id)

        if is_add:
            reaction = discord.utils.find(lambda r: ('name' in r.emoji) and (r.emoji.name == emoji.name), message.reactions)
            if not reaction:
                logging.warn(f'Reaction could not be found {emoji.name}, in message {message_id} in channel {channel_id}, reactions size: {len(message.reactions)}')
                return
            await self.reaction_language(reaction, member)
        else:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.handleRawReaction(payload, False)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.handleRawReaction(payload, True)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        await self.reaction_language(reaction, user)

    async def reaction_language(self, reaction, user):
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
        if has_any_role(msg.author, LANG_ROLE_IDS):
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
            self._recently_tagged = msg.author.id
            
        await msg.author.add_roles(msg.guild.get_role(tagged), reason=f'by {user.name}')
        try:
            await msg.author.remove_roles(msg.guild.get_role(NU_ROLE['id']), reason=f'by {user.name}')
        except:
            pass

        if msg.author.id == self._recently_tagged:
            self._recently_tagged = None

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

    async def mention_spam(self, message):
        if len(message.role_mentions) > 3:
            # role mention spam
            await message.author.add_roles(CHAT_MUTE_ROLE, reason='Role mention spam')
            embed = discord.Embed(colour=0xff0000)
            embed.title = f'FOR THOSE WHO GOT PINGED'
            embed.description = f'{message.author} pinged roles: {", ".join(message.role_mentions)}\n\nWhile this message was most likely a spam, all of these roles are **self-assignable** in <#189585230972190720> and you probably assigned the roles yourself without reading the rules. Head over there to and unreact to remove the pingable roles.'
            embed.timestamp = datetime.utcnow()
            embed.set_footer(text=f'{message.author.name} has been muted. Mods can react with ❌ to ban them.')
            ciri_message = await message.channel.send(f'<@&{ACTIVE_STAFF_ROLE}>', embed=embed)
            await ciri_message.add_reaction('\N{CROSS MARK}')
            banner = await wait_for_reaction(self.bot, message, '\N{CROSS MARK}')
            await ciri_message.clear_reaction('\N{CROSS MARK}')
            if banner is not None:
                try:
                    await message.author.ban(delete_message_days=0, reason=f'Issued by: {banner.name}. Role mention spam')
                    await message.channel.send(f'\N{WHITE HEAVY CHECK MARK} {message.author} has been banned.')
                except:
                    await message.channel.send(f'\N{CROSS MARK} {message.author} could not be banned.')
        elif len(message.user_mentions) > 7:
            pass


    async def troll_check(self, message):
        pass

    async def new_user_troll_check(self, message):
        author = message.author
        content = message.clean_content
        timestamp = discord.utils.snowflake_time(message.id)
        if N_WORD_REGEX.match(message.content.lower().replace(" ", "")):
            await author.ban(delete_message_days=1, reason="Auto-banned for a new user using the N-word")
            await message.channel.send(f'{author.mention} has been banned automatically')
            return

        for nu in self.troll_msgs:
            if nu['id'] == author.id:
                if nu['content'] == content or nu['content'] + nu['content'] == content:
                    nu['count'] += 1
                    if nu['count'] >= 3:
                        if (timestamp - nu['timestamp']).total_seconds() <= 10:
                            # ban is too harsh?
                            # await author.ban(delete_message_days=1, resason="Troll detected. The user has sent the same message 3 times in a row within 10 seconds")
                            # await message.channel.send(f'{author.mention} has been banned automatically due to spamming same messages')
                            # await message.guild.get_channel(self.settings[message.guild.id].log_channel_id).send(f'{author.mention} repeatedly sent:\n{content}')
                            await author.add_roles(CHAT_MUTE_ROLE, resason="Possible spam detected. The user has sent the same message 3 times in a row") 
                            await message.channel.send(f'<@&{ACTIVE_STAFF_ROLE}> {author.mention} has been muted automatically due to spamming the same message 3 times in a row.')
                        nu['count'] = 1
                        nu['timestamp'] = timestamp

                elif len(content) >= 5:
                    nu['content'] = content
                    nu['count'] = 1
                    nu['timestamp'] = timestamp
                break
        elif len(content) >= 5:
            self.troll_msgs.append({
                "id": author.id,
                "content": content,
                "count": 1,
                "timestamp": timestamp
            })
        
        if len(self.troll_msgs) > 10:
            self.troll_msgs.pop(0)

    async def staff_ping(self, message):
        msg_content = re.sub(REGEX_DISCORD_OBJ, '', message.content)
        if has_any_role(message.author, LANG_ROLE_IDS) and len(msg_content) < 20:
            messages = await message.channel.history(limit=20).flatten()
            new_users = {}
            for m in messages:
                author = m.author
                if N_WORD_REGEX.match(m.content.lower().replace(" ", "")):
                    await author.ban(delete_message_days=1, reason="Auto-banned for using the N-word")
                    await message.channel.send(f'{author.mention} has been banned automatically')
                    continue
                if author.joined and not has_any_role(author, LANG_ROLE_IDS):
                    if '死ね' in m.content:
                        await author.ban(delete_message_days=1, reason="Auto-banned a new user for saying 死ね")
                        await message.channel.send(f'{author.mention} has been banned automatically')
                        continue

                    if author.id not in new_users:
                        new_users[author.id] = author
                    
            if len(new_users) > 1:
                now = datetime.now()
                ciri_message = await message.channel.send(f'Found {len(new_users)} new users:\n{[f"{new_users[n].mention}: {new_users[n].name} joined {(now - new_users[n].joined).total_seconds() / 60}mins ago\n" for n in new_users]}\n\nMods can react with ❌ to BAN them')
                await ciri_message.add_reaction('\N{CROSS MARK}')
                banner = await wait_for_reaction(self.bot, message, '\N{CROSS MARK}', timeout=100)
                await ciri_message.clear_reaction('\N{CROSS MARK}')
                if banner is not None:
                    for mem_id in new_users:
                        member = new_users[mem_id]
                        try:
                            await member.ban(delete_message_days=1, reason=f'Issued by: {banner.name}. Role mention spam')
                            await message.channel.send(f'\N{WHITE HEAVY CHECK MARK} {member} has been banned.')
                        except:
                            await message.channel.send(f'\N{CROSS MARK} {member} could not be banned.') 




    @commands.Cog.listener()
    async def on_safe_message(self, message, **kwargs):
        if self.bot.config.debugging:
            return
        if message.guild.id != EJLX_ID:
            return
        if not has_any_role(message.author, LANG_ROLE_IDS):
            await guess_lang(message)
            await asking_vc(message)
            await self.new_user_troll_check(message)
        await self.troll_check(message)
        await self.mention_spam(message)
        if message.channel.id == JP_CHAT:
            await jp_only(message) # kwargs has lang info
        elif message.channel.id == JP_BEGINNER:
            await check_kanji(message)
        elif message.channel.id == LANG_SWITCH:
            await check_lang_switch(message)
        if len(message.role_mentions) > 0:
            await self.check_role_mentions(message)
        if message.channel.id == BOT_CHANNEL:
            if MUSIC_BOT_REGEX.match(message.content):
                await send_music_bot_notif(message)


    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild.id != EJLX_ID:
            return
        if message.author.bot:
            return
        if message.content.startswith(';report'):
            my_s = discord.utils.find(lambda g: g.id == 293787390710120449, self.bot.guilds)
            bot_log = my_s.get_channel(325532503567761408)
            await bot_log.send(f'{message.author} made a report in {message.channel}')

def setup(bot):
    bot.add_cog(EJLX(bot))