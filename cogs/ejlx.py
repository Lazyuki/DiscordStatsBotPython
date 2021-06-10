from discord.ext import commands
from typing import List
import discord
import asyncio
import re
import logging
from collections import namedtuple

from .utils.resolver import has_role, has_any_role
from .utils.parser import guess_lang, JP_EMOJI, EN_EMOJI, OL_EMOJI, asking_vc, REGEX_DISCORD_OBJ, REGEX_URL
from .utils.user_interaction import wait_for_reaction
from datetime import datetime, timezone

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
STAGE_QUARANTINE = 852380454546964490

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
BOOSTER_ROLE = 585540075769823235
WP_ROLE = 250907197075226625
MINIMO_ROLE = 250907197075226625
STAFF_ROLE = 543721608506900480
ADMIN_ROLE = 189594666365091850
ACTIVE_STAFF_ROLE = 240647591770062848
STAGE_VISITOR_ROLE = 645021058184773643

ROLES = [NJ_ROLE, FJ_ROLE, NE_ROLE, FE_ROLE, OL_ROLE, NU_ROLE]
ROLE_IDS = [r['id'] for r in ROLES]
LANG_ROLE_IDS = [r for r in ROLE_IDS if r != NU_ROLE['id']]

MUSIC_BOT_REGEX = re.compile(r'^[%=>][a-zA-Z]+')
ARABIC_REGEX = re.compile(r'^[\u0600-\u06FF\u200f\u200e0-9]+$')
HEBREW_REGEX = re.compile(r'^[\u0590-\u05FF\u200f\u200e]+$')
HANGUL_REGEX = re.compile(r'^[\u3131-\uD79D]+$')
CYRILLIC_REGEX = re.compile(r'^[\u0400-\u04FF]+$')
N_WORD_REGEX = re.compile(r'n(i|1)gg(e|3)r?s?')
BAD_WORDS_REGEX = re.compile(r'(fags?|faggots?|chinks?|ch[iao]ng|hiroshima|nagasaki|nanking|japs?|niggas?)')
BAD_JP_WORDS_REGEX = re.compile(r'(ニガー|セックス|[チマ]ンコ(?!.(?<=[ガパカ]チンコ))|ちんちん|死ね|[ちまう]んこ)')
INVITES_REGEX = re.compile(r'(https?://)?(www.)?(discord.(gg|io|me|li)|discord(app)?.com/invite)/.+[a-z]')

BAN_EMOJI = '<:ban:423687199385452545>' # EJLX BAN emoji
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

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

async def has_ban(ctx):
    return ctx.author.guild_permissions.ban_members

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

def joined_to_relative_time(user):
    if not user or not user.joined_at:
        return 'already left'
    now = datetime.now()
    seconds = (now - user.joined_at).total_seconds()
    if seconds < 60 * 60:
        return f'joined {seconds // 60} mins ago'
    if seconds < 60 * 60 * 72:
        return f'joined {seconds // 3600} hours ago'
    if seconds < 60 * 60 * 24 * 30:
        return f'joined {seconds // 86400} days ago'
    return f'joined {seconds // 2592000} months ago'

def time_since_join(user, unit='day'):
    if not user or not user.joined_at:
        return -1
    now = datetime.now()
    seconds = (now - user.joined_at).total_seconds()
    
    return seconds // (60 * 60 * 24) if unit == 'day' else seconds // 60 * 60 if unit == 'hour' else seconds // 60

def clean_and_truncate(content):
    clean_content = content.replace('\n', ' ')
    if not clean_content:
        return ''
    clean_content = f"`{clean_content[:10] + ('...' if len(clean_content) > 10 else '')}`"
    return clean_content

async def postBotLog(bot: discord.Client, message: str):
    my_s = discord.utils.find(lambda g: g.id == 293787390710120449, bot.guilds)
    bot_log = my_s.get_channel(325532503567761408)
    await bot_log.send(message)

class EJLX(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.settings = bot.settings
        self.newbies = []
        self._role_lock = asyncio.Lock()
        self._recently_tagged = None
        self.troll_msgs = []
        self.nu_troll_msgs = []
        self._message_cooldown = commands.CooldownMapping.from_cooldown(1, 120, commands.BucketType.channel)
        self.invites: dict[str, int] = dict()
        self.vanity_uses: int = 0 
        self._new_invites_cache: list[discord.Invite] = []
        self._vanity_cache: discord.Invite = None
        self._invite_lock = asyncio.Lock()
        self._recent_invite: datetime = None
        self._newbie_queue: list[int] = []
        self._multi_queue: list[discord.Member] = []
        

    async def cog_check(self, ctx):
        return ctx.guild.id == EJLX_ID

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            if guild.id == EJLX_ID:
                invites = await guild.invites()
                vanity = await guild.vanity_invite()
                self._recent_invite = datetime.now()
                self.invites = { invite.id: invite.uses for invite in invites }
                self._new_invites_cache = invites
                self.vanity_uses = vanity.uses
                self._vanity_cache = vanity

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
            role = await ctx.guild.create_role(reason=f'Create Club Role issued by {ctx.author} ({ctx.author.id})', name=role, mentionable=True)
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
                embed.set_footer(text=f'pinged by {message.author}')
                await message.channel.send(embed=embed)
            elif role.id == ACTIVE_STAFF_ROLE:
                if 'role' in message.content or 'fluent' in message.content or 'native' in message.content or 'language' in message.content:
                    # probably asking for a role
                    await message.reply('If you need help with roles, ping `@Welcoming Party` instead or message <@713245294657273856>. Active Staff is only for emergencies such as trolls.', mention_author=True)
                    continue
                await self.staff_ping(message)


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != EJLX_ID:
            return
        if member.voice:
            # stage channel
            self.newbies.append({ "member": member, "discovery": True })
            # await member.add_roles(member.guild.get_role(STAGE_VISITOR_ROLE)) 
            await postBotLog(self.bot, f'Detected voice state upon joining {member}' )
            if len(self.newbies) > 20:
                self.newbies.pop(0)
            return
        self._newbie_queue.append(member.id)
        asyncio.sleep(0.5) 
        async with self._invite_lock:
            if (datetime.now() - self._recent_invite).total_seconds() < 0.5:
                new_invites = self._new_invites_cache
                vanity = self._vanity_cache
            else:
                new_invites = await member.guild.invites()
                vanity = await member.guild.vanity_invite()
                self._new_invites_cache = new_invites
                self._vanity_cache = vanity
                self._recent_invite = datetime.now()
        
        potential_invites: list[discord.Invite] = []
        for invite in new_invites:
            new_usage = invite.uses
            if invite.id in self.invites:
                old_usage = self.invites[invite.id]
            else:
                old_usage = 0
            if new_usage != old_usage:
                potential_invites.append(invite)
        if vanity.uses != self.vanity_uses:
            potential_invites.append(vanity)
        
        aws = []
        if len(potential_invites) == 0:
            # Server discovery or one use invite?
            self.newbies.append({ "member": member, "discovery": True })
            # aws.append(member.add_roles(member.guild.get_role(STAGE_VISITOR_ROLE)))
            aws.append(postBotLog(self.bot, f'Discovery join {member}'))
        elif len(potential_invites) == 1:
            # Found one
            invite = potential_invites[0]
            self.newbies.append({ "member": member, "invite": invite })
            aws.append(postBotLog(self.bot, f'{member} joined with {invite.id} from {invite.inviter if invite.id != "japanese" else "vanity"}' ))
            if invite.id == 'japanese':
                self.vanity_uses += 1
            else:
                self.invites[invite.id] += 1
        else:
            # Failed to get invites for some people OR multi-join
            self._multi_queue.append(member)
            aws.append(postBotLog(self.bot, f'{member} found {len(potential_invites)} invites' ))

        self._newbie_queue.remove(member.id)
        if len(self._newbie_queue) == 0:
            self.invites = { invite.id: invite.uses for invite in new_invites }
            self.vanity_uses = vanity.uses
            for multi in self._multi_queue:
                self.newbies.append({ "member": multi, "invites": potential_invites })
            if self._multi_queue:
                aws.append(postBotLog(self.bot, f'{", ".join([str(m) for m in self._multi_queue])} joined with {", ".join([i.id for i in potential_invites])} (multi)' ))
            self._multi_queue = []
        if len(self.newbies) > 20:
            self.newbies.pop(0)

        await asyncio.wait(aws)


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
            ewbf = before.guild.get_channel(EWBF)
            embed = discord.Embed(colour=BOOSTER_COLOR)
            if before.premium_since is None:
                embed.title = f'{before} just boosted the server!'
                await before.add_roles(before.guild.get_role(BOOSTER_PINK_ROLE)) 
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
        def emoji_name(e):
            return e if type(e) is str else e.name

        if is_add:
            reaction = discord.utils.find(lambda r: emoji_name(r.emoji) == emoji_name(emoji), message.reactions)
            if not reaction:
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

    async def reaction_ban(self, message, bannees, reason='Unspecified', minimo=True, wp=False, delete_dismissed=False, unmute_dismissed=False):
        """
        React with ban emoji to ban
        """
        await message.add_reaction(BAN_EMOJI)
        await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
        ban = wait_for_reaction(self.bot, message=message, reaction=BAN_EMOJI, minimo=minimo, wp=wp,  triple_click=True)
        dismiss = wait_for_reaction(self.bot, message, '\N{WHITE HEAVY CHECK MARK}', minimo=minimo, wp=wp, return_false=True)
        done, pending = await asyncio.wait([ban, dismiss], return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
        await message.clear_reactions()
        banner = done.pop().result()
        if banner is not None:
            if banner is False:
                if unmute_dismissed:
                    for bannee in bannees:
                        try:
                            await bannee.remove_roles(message.guild.get_role(CHAT_MUTE_ROLE), reason=f'Auto mute dismissed')
                            await message.channel.send(f'\N{WHITE HEAVY CHECK MARK} Unmuted {bannee.name}')
                        except:
                            pass
                if delete_dismissed:
                    await message.delete()
                elif len(message.embeds) > 0:
                    embed = message.embeds[0].copy()
                    embed.set_footer(text=f'False alarm. They have been unmuted')
                    await message.edit(content=message.content, embed=embed)

            else:
                for bannee in bannees:
                    try:
                        await bannee.ban(delete_message_days=1, reason=f'Issued by: {banner}. Reason: {reason}')
                        await message.channel.send(f'\N{WHITE HEAVY CHECK MARK} {bannee} has been banned by {banner}')
                    except:
                        await message.channel.send(f'\N{CROSS MARK} {bannee} could not be banned.')
                if len(message.embeds) > 0:
                    embed = message.embeds[0]
                    embed.set_footer(text=f'Banned by {banner.name}')
                    await message.edit(content=message.content, embed=embed)
        elif len(message.embeds) > 0:
            embed = message.embeds[0]
            embed.set_footer(text=f'Timed out after 5 minutes')
            await message.edit(content=message.content, embed=embed)

        return True


    async def reaction_ban_multiple(self, message, bannees, reason='Unspecified', minimo=True, wp=False, delete_dismissed=False, unmute_dismissed=False):
        """
        Ban multiple members
        """
        individual_bans = []
        async def _individual_ban(bannee, emoji):
            banner = await wait_for_reaction(self.bot, message=message, reaction=emoji, minimo=minimo, wp=wp, triple_click=True)
            if banner is not None:
                try:
                    await bannee.ban(delete_message_days=1, reason=f'Issued by: {banner}. Reason: {reason}')
                    await message.channel.send(f'\N{WHITE HEAVY CHECK MARK} {bannee} has been banned by {banner}.')
                except:
                    await message.channel.send(f'\N{CROSS MARK} {bannee} could not be banned.')
            return False

        for i, bannee in enumerate(bannees):
            if i == 10:
                break
            emoji = NUMBER_EMOJIS[i] 
            await message.add_reaction(emoji)
            individual_bans.append(asyncio.create_task(_individual_ban(bannee, emoji)))
        
        finished = False
        banned_count = 0
        ban_all_or_dismiss = asyncio.create_task(self.reaction_ban(message, bannees, reason, minimo, wp, delete_dismissed, unmute_dismissed))
        
        for coro in asyncio.as_completed(individual_bans + [ban_all_or_dismiss]):
            try:
                next_result = await coro
                # ban_all_or_dismiss returns True upon completion
                if next_result:
                    for t in individual_bans:
                        t.cancel()
                elif next_result is not None:
                    banned_count += 1
                    if banned_count == len(bannees) or banned_count == 10:
                        # individually banned all
                        await message.clear_reactions()
                        ban_all_or_dismiss.cancel()
                        if len(message.embeds) > 0:
                            embed = message.embeds[0]
                            embed.set_footer(text=f'Done')
                            await message.edit(content=message.content, embed=embed)
                    
            except:
                pass

    async def mention_spam(self, message):
        if len(message.role_mentions) > 3:
            # role mention spam
            await message.author.add_roles(message.guild.get_role(CHAT_MUTE_ROLE), reason='Role mention spam')
            embed = discord.Embed(colour=0xff0000)
            embed.title = f'FOR THOSE WHO GOT PINGED'
            embed.description = f'{message.author} has been **muted** for pinging multiple roles: {", ".join(message.role_mentions)}\n\nWhile this message was most likely a spam, all of these roles are **self-assignable**. Head over to <#189585230972190720> and unreact to remove the pingable roles or type `,leave club_name` for roles not in that channel.'
            embed.set_footer(text=f'Minimos can click the BAN emoji 3 times to ban them or ✅ to dismiss this message and unmute them')
            ciri_message = await message.reply(f'<@&{ACTIVE_STAFF_ROLE}>', embed=embed, mention_author=False)
            await self.reaction_ban(ciri_message, [message.author], reason='Role mention spam', unmute_dismissed=True)
        elif len(message.mentions) > 10:
            if message.channel.id == VOICE_BOT_CHANNEL:
                return
            await message.author.add_roles(message.guild.get_role(CHAT_MUTE_ROLE), reason='User mention spam')
            embed = discord.Embed(colour=0xff0000)
            embed.title = f'Possible User Mention Spam'
            embed.description = f'{message.author} pinged {len(message.mentions)} people and has been **automatically muted**.'
            embed.set_footer(text=f'Minimos can click the BAN emoji 3 times to ban them or ✅ to dismiss this message and unmute them')
            ciri_message = await message.reply(f'<@&{ACTIVE_STAFF_ROLE}>', embed=embed, mention_author=False)
            await self.reaction_ban(ciri_message, [message.author], reason='User mention spam', unmute_dismissed=True)


    async def troll_check(self, message):
        if message.channel.id in [BOT_CHANNEL, VOICE_BOT_CHANNEL]:
            return
        author = message.author
        content = message.clean_content
        timestamp = message.created_at 
        msg_len = len(re.sub(REGEX_DISCORD_OBJ, '', message.content))

        for nu in self.troll_msgs:
            if nu['id'] == author.id:
                if nu['content'] == content or nu['content'] + nu['content'] == content:
                    nu['count'] += 1
                    if nu['count'] >= 5:
                        if (timestamp - nu['timestamp']).total_seconds() <= 30:
                            await author.add_roles(message.guild.get_role(CHAT_MUTE_ROLE), reason="Possible spam detected. The user has sent the same message 5 times in a row")
                            embed = discord.Embed(colour=0xff0000)
                            embed.description = f'{author.mention} has been **muted automatically** due to spamming the same message 5 times in a row.\n> {content[:100] + "..." if len(content) > 100 else content}'
                            embed.set_footer(text=f'Minimos can click the BAN emoji 3 times to ban them or ✅ to dismiss this message and unmute them.')
                            prompt = await message.reply(f'<@&{ACTIVE_STAFF_ROLE}>', embed=embed, mention_author=False)
                            await self.reaction_ban(prompt, [author], reason='Spamming the same message 5 times in a row', unmute_dismissed=True) 
                        nu['count'] = 1
                        nu['timestamp'] = timestamp

                elif msg_len >= 12:
                    nu['content'] = content
                    nu['count'] = 1
                    nu['timestamp'] = timestamp
                break
        else:
            if msg_len >= 12:
                self.troll_msgs.append({
                    "id": author.id,
                    "content": content,
                    "count": 1,
                    "timestamp": timestamp
                })
        if len(self.troll_msgs) > 30:
            self.troll_msgs.pop(0)

    async def new_user_troll_check(self, message):
        if message.channel.id in [BOT_CHANNEL, VOICE_BOT_CHANNEL]:
            return
        author = message.author
        content = message.clean_content
        timestamp = discord.utils.snowflake_time(message.id)
        msg_len = len(re.sub(REGEX_DISCORD_OBJ, '', message.content))

        if N_WORD_REGEX.match(message.content.lower().replace(" ", "")):
            await author.ban(delete_message_days=1, reason="Auto-banned. New user using the N-word")
            await message.channel.send(f'{author.mention} has been banned automatically')
            return
        if '@everyone' in message.content:
            if len(message.content.split('@everyone')) > 3:
                await author.ban(delete_message_days=1, reason="Auto-banned. New user @everyone spam")
                await message.channel.send(f'{author.mention} has been banned automatically')
                return
            await author.add_roles(message.guild.get_role(CHAT_MUTE_ROLE), reason="Possible spam detected. This new user tried to ping everyone") 
            embed = discord.Embed(colour=0xff0000)
            embed.description = f'**New User** {author.mention} has been **muted automatically** for trying to ping everyone.\n> {content[:100] + "..." if len(content) > 100 else content}'
            embed.set_footer(text=f'WPs can click the BAN emoji 3 times to ban them or ✅ to dismiss this message and unmute them.')
            prompt = await message.reply(f'<@&{ACTIVE_STAFF_ROLE}><@&{WP_ROLE}>', embed=embed, mention_author=False)
            await self.reaction_ban(prompt, [author], reason='New user trying to ping everyone', wp=True, unmute_dismissed=True) 
            return


        for nu in self.nu_troll_msgs:
            if nu['id'] == author.id:
                if nu['content'] == content or nu['content'] + nu['content'] == content:
                    nu['count'] += 1
                    if nu['count'] >= 3:
                        if (timestamp - nu['timestamp']).total_seconds() <= 30:
                            await author.add_roles(message.guild.get_role(CHAT_MUTE_ROLE), reason="Possible spam detected. This new user has sent the same message 3 times in a row") 
                            embed = discord.Embed(colour=0xff0000)
                            embed.description = f'**New User** {author.mention} has been **muted automatically** due to spamming the same message 3 times in a row.\n> {content[:100] + "..." if len(content) > 100 else content}'
                            embed.set_footer(text=f'WPs can click the BAN emoji 3 times to ban them or ✅ to dismiss this message and unmute them.')
                            prompt = await message.reply(f'<@&{ACTIVE_STAFF_ROLE}><@&{WP_ROLE}>', embed=embed, mention_author=False)
                            await self.reaction_ban(prompt, [author], reason='New user spamming the same message 3 times in a row', wp=True, unmute_dismissed=True) 
                        nu['count'] = 1
                        nu['timestamp'] = timestamp

                elif msg_len >= 7:
                    nu['content'] = content
                    nu['count'] = 1
                    nu['timestamp'] = timestamp
                break
        else:
            if msg_len >= 7:
                self.nu_troll_msgs.append({
                    "id": author.id,
                    "content": content,
                    "count": 1,
                    "timestamp": timestamp
                })
        
        if len(self.nu_troll_msgs) > 20:
            self.nu_troll_msgs.pop(0)

    @commands.command(aliases=['autobahn', 'ab'])
    @commands.check(has_ban)
    async def autoban(self, ctx):
        """
        Open up the ban wizard to easily ban trolls
        """
        detected = await self.staff_ping(ctx.message, title="Auto Ban Menu", delete_dismissed=False)
        if detected == 0:
            await ctx.send(f"\N{CROSS MARK} Could not find potential trolls")

    async def staff_ping(self, message, title="Active Staff Ping Ban Menu", delete_dismissed=True):
        msg_content = re.sub(REGEX_DISCORD_OBJ, '', message.content)

        # new users shouldn't trigger ban detections
        if has_any_role(message.author, LANG_ROLE_IDS) and time_since_join(message.author) >= 3:
            embed = discord.Embed(colour=0xfc3838)
            embed.title = title

            # if staff ping is replying to a message
            if message.reference:
                if message.reference.cached_message:
                    bannee = message.reference.cached_message.author
                    embed.description = f'{bannee} {joined_to_relative_time(bannee)}'
                    embed.set_footer(text=f'Minimos can click the BAN emoji 3 times to ban them or ✅ to dismiss this message')
                    ciri_message = await message.channel.send(embed=embed)
                    await self.reaction_ban(ciri_message, [bannee], reason='Active Staff ping auto detection', delete_dismissed=delete_dismissed)
                return

            messages = await message.channel.history(limit=50).flatten()
            user_set = set([m.author for m in messages if not m.author.bot])
            user_dict = { u.id: { 'user': u, 'count': 0 } for u in user_set }
            stats = self.bot.get_cog('Stats')
            user_records = await stats.get_messages_for_users(message.guild.id, user_dict.keys())
            for record in user_records:
                user_dict[record['user_id']]['count'] = record['count']

            # if staff ping is from an active user 
            if has_any_role(message.author, [BOOSTER_ROLE, WP_ROLE, MINIMO_ROLE, STAFF_ROLE, ADMIN_ROLE]) or user_dict[message.author.id]['count'] > 100:
                # if staff ping contains mentions
                if message.mentions:
                    embed.description = '\n'.join([f'{NUMBER_EMOJIS[i]}: {m} {joined_to_relative_time(m)}' for i, m in enumerate(message.mentions[:10])])
                    embed.set_footer(text=f'Minimos can click each number 3 times to ban them individually, BAN emoji 3 times to ban all of them, or ✅ to dismiss this message')
                    ciri_message = await message.channel.send(embed=embed)
                    await self.reaction_ban_multiple(ciri_message, message.mentions, reason='Active Staff ping auto detection', delete_dismissed=delete_dismissed)
                    return

                # check raid if last 4 people joined within 2 minutes
                members_by_joined_date = sorted(message.guild.members, key=lambda m: m.joined_at)
                last_4_in = (members_by_joined_date[-1].joined_at - members_by_joined_date[-4].joined_at).total_seconds()
                if last_4_in < 120:
                    # possible raid so just add new users who's said anything
                    new_users = dict()
                    for m in messages:
                        joined_minutes_ago = time_since_join(m.author, unit='minute')
                        if joined_minutes_ago < 15:
                            clean_content = clean_and_truncate(m.clean_content)
                            if m.author.id in new_users:
                                clean_content = new_users[m.author.id]["contents"] + ', ' + (clean_content or '*file*')
                            new_users[m.author.id] = { "contents": clean_content, "user": m.author }

                    bannees = [n["user"] for n in new_users.values()]
                    if not bannees:
                        return
                    embed.description = '\n'.join(f'{NUMBER_EMOJIS[i]}: {b} {joined_to_relative_time(b)}. Messages: {new_users[b.id]["contents"]}' for i, b in enumerate(bannees[:10])) 
                    embed.set_footer(text=f'Minimos can click each number 3 times to ban them individually, BAN emoji 3 times to ban all of them, or ✅ to dismiss this message')
                    ciri_message = await message.channel.send(embed=embed)
                    await self.reaction_ban_multiple(ciri_message, bannees, reason='Active Staff ping auto detection', delete_dismissed=delete_dismissed)
                    return

                # read history to determine trolls
                user_points = dict()
                for m in messages:
                    author = m.author
                    if author.bot or has_any_role(author, [BOOSTER_ROLE, WP_ROLE, MINIMO_ROLE, STAFF_ROLE, ADMIN_ROLE]) or user_dict[author.id]['count'] > 100:
                        continue
                    if author.id not in user_points:
                        joined_hours_ago = time_since_join(author, unit='hour')
                        user_points[author.id] = {
                            "points": 0,
                            "reasons": [],
                            "user": author
                        }
                        if joined_hours_ago < 1:
                            user_points[author.id]["points"] = 5
                        elif joined_hours_ago < 24:
                            user_points[author.id]["points"] = 3
                        elif joined_hours_ago < 24 * 7:
                            user_points[author.id]["points"] = 1

                    clean_content = re.sub(REGEX_DISCORD_OBJ, '', m.content)
                    lower_content = clean_content.lower().replace(" ", "").replace("\n", "")
                    if N_WORD_REGEX.match(lower_content):
                        user_points[author.id]["points"] += 100
                        user_points[author.id]["reasons"].append("Hard R N-word")
                    if ARABIC_REGEX.match(lower_content) or HEBREW_REGEX.match(lower_content) or HANGUL_REGEX.match(lower_content) or CYRILLIC_REGEX.match(lower_content):
                        user_points[author.id]["points"] += 10
                        user_points[author.id]["reasons"].append(clean_and_truncate(m.content))
                    if  REGEX_URL.match(m.content) and 'discord.gg/japanese' not in m.content:
                        if INVITES_REGEX.match(m.content):
                            user_points[author.id]["points"] += 5
                            user_points[author.id]["reasons"].append(clean_and_truncate(INVITES_REGEX.match(m.content)[1]))
                        else:
                            user_points[author.id]["points"] += 3
                            user_points[author.id]["reasons"].append(clean_and_truncate(REGEX_URL.match(m.content)[1]))
                    if BAD_JP_WORDS_REGEX.match(m.content):
                        match = BAD_JP_WORDS_REGEX.match(m.content)[1]
                        user_points[author.id]["points"] += 4
                        user_points[author.id]["reasons"].append(clean_and_truncate(match))
                    words = m.content.lower().split()
                    for w in words:
                        match = BAD_WORDS_REGEX.match(w)
                        if match:
                            user_points[author.id]["points"] += 4
                            user_points[author.id]["reasons"].append(clean_and_truncate(match[1]))
                    if m.attachments:
                        user_points[author.id]["points"] += 2
                        user_points[author.id]["reasons"].append("FileUpload")
                    if re.match(r'^[A-Z0-9 ?!\']$', clean_content):
                        user_points[author.id]["points"] += 2
                        user_points[author.id]["reasons"].append(clean_and_truncate(clean_content))
                    elif not has_any_role(author, LANG_ROLE_IDS): 
                        user_points[author.id]["points"] += 1
                        user_points[author.id]["reasons"].append(clean_and_truncate(clean_content))


                sorted_users = sorted(user_points.values(), key=lambda u: u["points"], reverse=True)
                filtered_users = list(filter(lambda u: u["points"] > 5, sorted_users))[:10]
                bannees = [b["user"] for b in filtered_users]
                if not bannees:
                    return 0
                if len(bannees) == 1:
                    b = bannees[0]
                    embed.description = f'{b["user"].mention} {joined_to_relative_time(b["user"])}.\n__Reasons__: {",".join(b["reasons"])}'
                    embed.set_footer(text=f'Minimos can click the BAN emoji 3 times to ban them, or ✅ to dismiss this message')
                    ciri_message = await message.channel.send(embed=embed)
                    await self.reaction_ban(ciri_message, bannees, reason='Active Staff ping auto detection', delete_dismissed=delete_dismissed)
                    return 1

                embed.description = '\n'.join(f'{NUMBER_EMOJIS[i]} {b["user"].mention} {joined_to_relative_time(b["user"])}. __Reasons__: {",".join(b["reasons"])}' for i, b in enumerate(filtered_users)) 
                embed.set_footer(text=f'Minimos can click each number 3 times to ban them individually, BAN emoji 3 times to ban all of them, or ✅ to dismiss this message')
                ciri_message = await message.channel.send(embed=embed)
                await self.reaction_ban_multiple(ciri_message, bannees, reason='Active Staff ping auto detection', delete_dismissed=delete_dismissed)
                return len(bannees)

    async def check_jap(self, message):
        if message.content and message.content[0] in [',', '.', ';']:
            return
        sanitized = re.sub(r'["`]japs?["`]', '', message.content.lower())
        words = re.split(r'\W+', sanitized)
        bucket = self._message_cooldown.get_bucket(message)
        for word in words:
            if word == 'jap' or word == 'japs':
                current = message.created_at.replace(tzinfo=timezone.utc).timestamp()
                retry_after = bucket.update_rate_limit(current) 
                if not retry_after:
                    embed = discord.Embed(colour=0xFF5500)
                    embed.description = """
                    We avoid "jap" on this server due to its historical use as a racial slur. We prefer "jp", "jpn", or "Japanese". Thanks for understanding.\n[[Some picture examples](https://imgur.com/a/lPVBo2y)][[Read more here](https://gist.github.com/ScoreUnder/e08b37a8af3c257107fc55fc7a8fcad6)]
                    """
                    await message.reply(embed=embed, mention_author=True)
                return

    async def moderate_stage(self, message):
        pass

    @commands.Cog.listener()
    async def on_safe_message(self, message, **kwargs):
        if self.bot.config.debugging:
            return
        if not message.guild or message.guild.id != EJLX_ID:
            return
        if not has_any_role(message.author, LANG_ROLE_IDS):
            if message.channel.id != STAGE_QUARANTINE:
                await guess_lang(message)
                await asking_vc(message)
            await self.new_user_troll_check(message)
        else:
            if time_since_join(message.author) == 0:
                await self.new_user_troll_check(message)
            else:
                await self.troll_check(message)
        await self.mention_spam(message)
        if message.channel.id == JP_CHAT:
            await jp_only(message)
        elif message.channel.id == JP_BEGINNER:
            await check_kanji(message)
        elif message.channel.id == LANG_SWITCH:
            await check_lang_switch(message)
        if len(message.role_mentions) > 0:
            await self.check_role_mentions(message)
        if message.channel.id == BOT_CHANNEL:
            if MUSIC_BOT_REGEX.match(message.content):
                await send_music_bot_notif(message)
        await self.check_jap(message)
        if message.channel.id == STAGE_QUARANTINE:
            await self.moderate_stage(message)


    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if not message.guild or message.guild.id != EJLX_ID:
            return
        if message.author.bot:
            return
        if message.content.startswith(';report'):
            await postBotLog(self.bot, f'{message.author} made a report in {message.channel}')

def setup(bot):
    bot.add_cog(EJLX(bot))