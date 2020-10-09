from discord.ext import commands, tasks
import discord
from collections import Counter, defaultdict
import logging
import asyncio
import asyncpg
import re
from datetime import datetime, date, timedelta
from .utils.parser import REGEX_CUSTOM_EMOJIS, REGEX_BOT_COMMANDS
from .utils.resolver import resolve_minimum_channel, resolve_user_id, has_role, resolve_role
from .utils.leaderboard import PaginatedLeaderboard
from .ejlx import JP_EMOJI, EN_EMOJI, OL_EMOJI, NJ_ROLE

log = logging.getLogger(__name__)

def is_vc(voice_state):
    return voice_state.channel and not voice_state.afk and not voice_state.self_deaf and not voice_state.deaf

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings
        self.pool = bot.pool
        self.config = bot.config
        self.in_vc = defaultdict(dict)
        self._temp_messages = defaultdict(int)
        self._temp_emojis = defaultdict(Counter)
        self._temp_voice = defaultdict(int)
        self._batch_lock = asyncio.Lock(loop=bot.loop)
        self.batch_update.add_exception_type(asyncpg.PostgresConnectionError)
        self.batch_update.add_exception_type(asyncpg.CardinalityViolationError) # why
        self.batch_update.start()
        self.clear_old_records.start()

        if bot.is_ready():
            log.info('cog reloaded && bot is ready')
            for guild in bot.guilds:
                vc = self.in_vc[guild.id]
                for vcs in guild.voice_channels:
                    for member in vcs.members:
                        if is_vc(member.voice):
                            vc[member.id] = datetime.utcnow()

    @commands.command(aliases=['u', 'uinfo'])
    async def user(self, ctx, *, arg = None):
        user_id = ctx.author.id
        if arg:
            user_id = resolve_user_id(ctx, arg)
            if user_id is None:
                await ctx.message.add_reaction('\N{BLACK QUESTION MARK ORNAMENT}')
                return
        member = ctx.guild.get_member(user_id)

        mod_channels = self.settings[ctx.guild.id]._mod_channel_ids
        if ctx.channel.id in mod_channels:
             mod_channels = []
        
        emoji_data, voice, message_data = await asyncio.gather(
            self.pool.fetch('''
                SELECT emoji, SUM(emoji_count) as count
                FROM emojis
                WHERE guild_id = $1 AND user_id = $2
                GROUP BY emoji
                ORDER BY count DESC
                LIMIT 3
                ''', ctx.guild.id, user_id),
            self.pool.fetchval('''
                SELECT SUM(minute_count) as count
                FROM voice
                WHERE guild_id = $1 AND user_id = $2
                ''', ctx.guild.id, user_id),
            self.pool.fetch('''
                WITH records AS (
                    SELECT channel_id, lang, message_count, utc_date
                    FROM messages
                    WHERE guild_id = $1 AND user_id = $2 AND channel_id != ALL ($3::BIGINT[])
                )
                    (
                        SELECT NULL::BIGINT AS channel_id, NULL::LANGTYPE AS lang, SUM(message_count) AS count
                        FROM records
                    ) UNION ALL
                    (
                        SELECT NULL, lang, SUM(message_count) AS count
                        FROM records
                        GROUP BY lang
                    ) UNION ALL
                    (
                        SELECT channel_id, NULL, SUM(message_count) AS count
                        FROM records
                        GROUP BY channel_id
                    ) UNION ALL 
                    (
                        SELECT NULL, NULL, SUM(message_count) as count
                        FROM records
                        WHERE utc_date > (current_date - '7 days'::interval)
                    )
                ''', ctx.guild.id, user_id, mod_channels)
        )

        # Prepare embed
        embed = discord.Embed(colour=0x3A8EDB)
        if member:
            nick = ''
            if member.nick:
                nick = f' aka {member.nick}'
            embed.set_footer(text='Joined this server')
            embed.timestamp = member.joined_at
            embed.set_author(name=f'Stats for {member.name}#{member.discriminator}{nick}', icon_url=member.avatar_url)
        else:
            embed.set_author(name=f'Stats for {user_id}')
            embed.set_footer(text='Already left the server')

        # NO records
        if not message_data and not emoji_data and voice is None:
            embed.description = "Has no record in the past 30 days"
            await ctx.send(embed=embed)
            return

        # If true, it will at least have 3 rows
        if message_data:
            # Message total.
            month_total = message_data[0].get('count', 0)
            week_total = message_data[-1].get('count', 0) if message_data[-1]['channel_id'] is None else 0
            embed.add_field(name='Messages Month | Week', value=f'{month_total} | {week_total}')

            # Lang usage
            langs = { r['lang'] : r['count'] for r in message_data[1:4] if r['lang'] }
            jp_role = self.settings[ctx.guild.id].jp_role_id
            is_jp = member and discord.utils.find(lambda r: r.id == jp_role, member.roles)
            EN = langs.get('EN', 0)
            JP = langs.get('JP', 0)
            BOTH = EN + JP
            if is_jp:
                usage_name = 'English usage'
                usage = EN / (BOTH) * 100 if BOTH > 0 else 0
            else:
                usage_name = 'Japanese usage'
                usage = JP / (BOTH) * 100 if BOTH > 0 else 0
            embed.add_field(name=usage_name, value=f'{round(usage, 2)}%')

            # Channel usage
            channels = Counter({ r['channel_id'] : r['count'] for r in message_data[2:] if r['channel_id']}).most_common(3)
            channel_str = ''
            for ch_id, count in channels:
                perc = count / month_total * 100
                channel = ctx.guild.get_channel(ch_id)
                if channel is None:
                    channel = { 'name': 'deleted-channel' }
                channel_str += f'**#{channel.name}**: {round(perc, 1)}%\n'
        else:
            embed.add_field(name='Messages', value=0)

        # Voice usage
        voice = 0 if voice is None else voice
        hrs = voice // 60
        mns = voice % 60
        voice_str = (f'{hrs}hr ' if hrs else '') + f'{mns}min'
        
        # Emoji usage
        emojis = { r['emoji'] : r['count'] for r in emoji_data }
        emoji_str = '\n'.join([f'{e} {count} times' for e, count in emojis.items()])

        # Add optionals
        if voice_str:
            embed.add_field(name='Time spent in VC', value=voice_str)
        if channel_str:
            embed.add_field(name='Most active channels', value=channel_str)
        if emoji_str:
            embed.add_field(name='Most used emojis', value=emoji_str)

        await ctx.send(embed=embed)


    @commands.command(aliases=['ch', 'cinfo'])
    async def channel(self, ctx):
        pass


    @commands.command(aliases=['s', 'sinfo'])
    async def server(self, ctx):
        pass


    @commands.command(aliases=['l', 'lb'])
    async def leaderboard(self, ctx, *, role=None):
        user_id = ctx.author.id
        if role:
            role = resolve_role(ctx, role)
            if not role:
                await ctx.send('Invalid role name')
                return

        lb = await self.pool.fetch('''
            WITH ranked AS (
                SELECT *, RANK() OVER(ORDER BY count DESC)
                FROM (
                    SELECT user_id, SUM(message_count) AS count
                    FROM messages
                    WHERE guild_id = $1
                    GROUP BY user_id
                ) AS lb
            )
                (
                    SELECT * FROM ranked
                ) UNION ALL
                (
                    SELECT * FROM ranked WHERE user_id = $2
                )
            ''', ctx.guild.id, user_id)

        # No messages in the server
        if not lb:
            await ctx.send('No messages found')
            return

        if lb[-1]['user_id'] != user_id:
            records = lb 
            user_record = None
        else:
            records = lb[:-1]
            user_record = lb[-1] 
        
        title = 'Leaderboard'

        if role:
            title += f' with role: {role.name}'
            def hasRole(uid):
                member = ctx.guild.get_member(uid)
                if not member:
                    return False
                return any([r == role for r in member.roles])
            records = [r for r in records if hasRole(r['user_id'])]
        
        leaderboard = PaginatedLeaderboard(ctx, records=records, title=title, description='Number of messages in the past 30 days (UTC)', find_record=user_record)
        await leaderboard.build()

    @commands.command(aliases=['chlb', 'cl'])
    async def channel_leaderboard(self, ctx, *, role=''):
        user_id = ctx.author.id
        channel_ids = [ c.id for c in ctx.message.channel_mentions ]
        role = re.sub(r'<#[0-9]+>', '', role).strip()
        if role:
            role = resolve_role(ctx, role)
            if not role:
                await ctx.send('Invalid role name')
                return

        if not channel_ids:
            channel_ids = [ ctx.channel.id ]
        chlb = await self.pool.fetch('''
            WITH ranked AS (
                SELECT *, RANK() OVER (ORDER BY count DESC)
                FROM (
                    SELECT user_id, SUM(message_count) as count
                    FROM messages
                    WHERE guild_id = $1 AND channel_id = ANY ($2::BIGINT[])
                    GROUP BY user_id
                    ORDER BY count DESC
                ) AS cl
            )
                (
                    SELECT * FROM ranked
                ) UNION ALL
                (
                    SELECT * FROM ranked WHERE user_id = $3
                )
            ''', ctx.guild.id, channel_ids, user_id)
        if not chlb:
            await ctx.send('No messages found')
            return

        title = 'Channel Leaderboard for '
        channel_names = []
        for ch_id in channel_ids:
            channel = ctx.guild.get_channel(ch_id)
            if channel is None:
                ch_name = f'#deleted-channel({ch_id})'
            else:
                ch_name = f'#{channel.name}'
            channel_names.append(ch_name)
        title += ','.join(channel_names)

        if chlb[-1]['user_id'] != user_id:
            records = chlb 
            user_record = None
        else:
            records = chlb[:-1]
            user_record = chlb[-1] 

        if role:
            title += f' with role: {role.name}'
            def hasRole(uid):
                member = ctx.guild.get_member(uid)
                if not member:
                    return False
                return any([r == role for r in member.roles])
            records = [r for r in records if hasRole(r['user_id'])]

        leaderboard = PaginatedLeaderboard(ctx, records=records, title=title[:256], description='Number of messages in the past 30 days (UTC)', find_record=user_record)
        await leaderboard.build()


    @commands.command(aliases=['jplb', 'jpl'])
    async def japanese_leaderboard(self, ctx, *, limit=''):
        try:
            limit = int(limit)
        except:
            limit = 500

        records = await self.pool.fetch('''
            WITH lang_usage AS (
                SELECT user_id, COALESCE(SUM(CASE WHEN lang = 'JP' THEN message_count END),0) as jp_count, SUM(message_count) as total
                FROM messages
                WHERE guild_id = $1 AND lang IN ('EN', 'JP')
                GROUP BY user_id
                HAVING SUM(message_count) > $2
            )
                (
                    SELECT user_id, 100.0 * jp_count / total AS jp_ratio
                    FROM lang_usage
                    ORDER BY jp_ratio DESC
                )
            ''', ctx.guild.id, limit)

        rank = 1
        jplb = []
        for record in records:
            user_id = record.get('user_id')
            member = ctx.guild.get_member(user_id)
            is_author = '\N{ROUND PUSHPIN}' if user_id == ctx.author.id else ''
            if member is None or has_role(member, NJ_ROLE['id']):
                continue
            name = f'{is_author}{rank}) {member.name}'
            jplb.append({
                'rank': rank,
                'field_name': name,
                'count': record.get('jp_ratio')
            })
            rank += 1
        
        if not jplb:
            await ctx.send(f'No user found with more than {limit} messages')
            return
        
        leaderboard = PaginatedLeaderboard(
            ctx,
            records=jplb,
            title='Japanese Usage Leaderboard',
            description=f'Japanese usage in the past 30 days for people with more than {limit} messages',
            rank_for='field_name',
            field_name_resolver=lambda x, y: y,
            count_to_string=lambda x: f'{x:.2f}%'
            )
        await leaderboard.build()

    @commands.command(aliases=['enlb', 'enl'])
    async def english_leaderboard(self, ctx, *, limit=''):
        try:
            limit = int(limit)
        except:
            limit = 300

        records = await self.pool.fetch('''
            WITH lang_usage AS (
                SELECT user_id, COALESCE(SUM(CASE WHEN lang = 'EN' THEN message_count END),0) as en_count, SUM(message_count) as total
                FROM messages
                WHERE guild_id = $1 AND lang IN ('EN', 'JP')
                GROUP BY user_id
                HAVING SUM(message_count) > $2
            )
                (
                    SELECT user_id, 100.0 * en_count / total AS en_ratio
                    FROM lang_usage
                    ORDER BY en_ratio DESC
                )
            ''', ctx.guild.id, limit)
        

        rank = 1
        enlb = []
        for record in records:
            user_id = record.get('user_id')
            member = ctx.guild.get_member(user_id)
            is_author = '\N{ROUND PUSHPIN}' if user_id == ctx.author.id else ''
            if member is None or not has_role(member, NJ_ROLE['id']):
                continue
            name = f'{is_author}{rank}) {member.name}'
            enlb.append({
                'rank': rank,
                'field_name': name,
                'count': record.get('en_ratio')
            })
            rank += 1

        if not enlb:
            await ctx.send(f'No user found with more than {limit} messages')
            return
        
        leaderboard = PaginatedLeaderboard(
            ctx,
            records=enlb,
            title='English Usage Leaderboard',
            description=f'English usage in the past 30 days for people with more than {limit} messages',
            rank_for='field_name',
            field_name_resolver=lambda x, y: y,
            count_to_string=lambda x: f'{x:.2f}%'
            )
        await leaderboard.build()

    @commands.command(aliases=['emlb', 'eml', 'emoji'])
    async def emoji_leaderboard(self, ctx, *, option=''):
        if option and option != 's' and option != 'server':
            await self.emoji_usage_leaderboard(ctx, option)
            return
        records = await self.pool.fetch('''
            SELECT *, RANK() OVER (ORDER BY count DESC)
            FROM (
                SELECT emoji, SUM(emoji_count) as count
                FROM emojis
                WHERE guild_id = $1
                GROUP BY emoji
                ORDER BY count DESC
            ) AS el
            ''', ctx.guild.id)

        if not records:
            await ctx.send('No emoji data found')
            return

        def emoji_resolver(rank, emoji):
            return f'{rank}) {emoji}'

        
        if option == 's' or option == 'server':
            guild_emojis = [str(emoji) for emoji in ctx.guild.emojis]
            records = [r for r in records if r['emoji'] in guild_emojis]
            description = 'Server emoji usage in the past 30 days (UTC)'
        else:
            description = 'Emoji usage in the past 30 days (UTC)'

        leaderboard = PaginatedLeaderboard(ctx, records=records, title='Emoji Leaderboard', description=description, rank_for='emoji', field_name_resolver=emoji_resolver)
        await leaderboard.build()


    async def emoji_usage_leaderboard(self, ctx, emoji):
        records = await self.pool.fetch('''
            WITH ranked AS (
                SELECT *, RANK() OVER (ORDER BY count DESC)
                FROM (
                    SELECT user_id, SUM(emoji_count) as count
                    FROM emojis
                    WHERE guild_id = $1 AND emoji = $2 
                    GROUP BY user_id
                    ORDER BY count DESC
                ) AS el
            )
                (
                    SELECT * FROM ranked
                ) UNION ALL
                (
                    SELECT * FROM ranked WHERE user_id = $3
                )
            ''', ctx.guild.id, emoji, ctx.author.id)

        if not records:
            await ctx.send('No emoji data found')
            return

        description = f'Emoji leaderboard for {emoji} in the past 30 days (UTC)'

        if records[-1]['user_id'] == ctx.author.id:
            records = records[:-1]
            user_record = records[-1] 
        else:
            user_record = None

        leaderboard = PaginatedLeaderboard(ctx, records=records, title='Emoji Usage Leaderboard', description=description, find_record=user_record)
        await leaderboard.build()

    @commands.command(aliases=['vclb', 'vl', 'v'])
    async def voice_leaderboard(self, ctx, *, role=''):
        user_id = ctx.author.id
        if role:
            role = resolve_role(ctx, role)
            if not role:
                await ctx.send('Invalid role name')
                return
        vl = await self.pool.fetch('''
            WITH ranked AS (
                SELECT *, RANK() OVER (ORDER BY count DESC)
                FROM (
                    SELECT user_id, SUM(minute_count) as count
                    FROM voice
                    WHERE guild_id = $1
                    GROUP BY user_id
                    ORDER BY count DESC
                ) AS vl
            )
                (
                    SELECT * FROM ranked
                ) UNION ALL
                (
                    SELECT * FROM ranked WHERE user_id = $2
                )
            ''', ctx.guild.id, user_id)

        if not vl:
            await ctx.send('No voice usage data found')
            return
        
        if vl[-1]['user_id'] != user_id:
            records = vl 
            user_record = None
        else:
            records = vl[:-1]
            user_record = vl[-1] 

        def count_to_string(c):
            hrs = c // 60
            mns = c % 60
            return (f'{hrs}hr ' if hrs else '') + f'{mns}min'

        title = 'Voice Leaderboard'
        if role:
            title += f' with role: {role.name}'
            def hasRole(uid):
                member = ctx.guild.get_member(uid)
                if not member:
                    return False
                return any([r == role for r in member.roles])
            records = [r for r in records if hasRole(r['user_id'])] 

        leaderboard = PaginatedLeaderboard(ctx, records=records, title=title, description='Time spent in VC in the past 30 days (UTC)', find_record=user_record, count_to_string=count_to_string)
        await leaderboard.build()

    @commands.command(aliases=['ac', 'uac'])
    async def user_activity(self, ctx, *, arg=''):
        user = ctx.author
        use_numbers = '-n' in arg
        ac = await self.pool.fetch('''
            SELECT SUM(message_count) as count, utc_date
            FROM messages
            WHERE guild_id = $1 AND user_id = $2
            GROUP BY utc_date
            ORDER BY utc_date ASC
            ''', ctx.guild.id, user.id)
        s = f'Server activity for **{user}**\n```\n'
        if use_numbers:
            prev_date = datetime.now().date() - timedelta(days=30)
            for record in ac:
                date = record['utc_date']
                if date < prev_date:
                    continue
                while (date > prev_date):
                    s += prev_date.strftime(f'%b %d(%a): 0\n')
                    prev_date += timedelta(days=1)
                prev_date += timedelta(days=1)
                count = record['count']
                s += date.strftime(f'%b %d(%a): {count}\n')
        else:
            max_num = max(ac, key=lambda r: r['count'])['count']
            s += f'Unit: {max_num // 15} messages\n'
            prev_date = datetime.now().date() - timedelta(days=30)
            for record in ac:
                date = record['utc_date']
                if date < prev_date:
                    continue
                while (date > prev_date):
                    s += prev_date.strftime(f'%b %d(%a):\n')
                    prev_date += timedelta(days=1)
                prev_date += timedelta(days=1)
                count = record['count']
                ticks = 15 * count // max_num
                bar = '-' * ticks
                s += date.strftime(f'%b %d(%a): {bar}\n')

        s += '```'
        await ctx.send(s)


    @commands.command(aliases=['cac', 'chac'])
    async def channel_activity(self, ctx, *, arg=''):
        channel_ids = [ c.id for c in ctx.message.channel_mentions ] 
        use_numbers = '-n' in arg
        if not channel_ids:
            channel_ids = [ ctx.channel.id ]
        ac = await self.pool.fetch('''
            SELECT SUM(message_count) as count, utc_date
            FROM messages
            WHERE guild_id = $1 AND channel_id = ANY ($2::BIGINT[])
            GROUP BY utc_date
            ORDER BY utc_date ASC
            ''', ctx.guild.id, channel_ids)
        channels = [ctx.guild.get_channel(cid).name for cid in channel_ids]
        s = f'Server activity for {channels}\n```\n'
        if use_numbers:
            prev_date = datetime.now().date() - timedelta(days=30)
            for record in ac:
                date = record['utc_date']
                if date < prev_date:
                    continue
                while (date > prev_date):
                    s += prev_date.strftime(f'%b %d(%a): 0\n')
                    prev_date += timedelta(days=1)
                prev_date += timedelta(days=1)
                count = record['count']
                s += date.strftime(f'%b %d(%a): {count}\n')
        else:
            max_num = max(ac, key=lambda r: r['count'])['count']
            s += f'Unit: {max_num // 15} messages\n'
            prev_date = datetime.now().date() - timedelta(days=30)
            for record in ac:
                date = record['utc_date']
                if date < prev_date:
                    continue
                while (date > prev_date):
                    s += prev_date.strftime(f'%b %d(%a):\n')
                    prev_date += timedelta(days=1)
                prev_date += timedelta(days=1)
                count = record['count']
                ticks = 15 * count // max_num
                bar = '-' * ticks
                s += date.strftime(f'%b %d(%a): {bar}\n')

        s += '```'
        await ctx.send(s)


    @commands.command(aliases=['sac'])
    async def server_activity(self, ctx, *, arg=''):
        use_numbers = '-n' in arg
        ac = await self.pool.fetch('''
            SELECT SUM(message_count) as count, utc_date
            FROM messages
            WHERE guild_id = $1
            GROUP BY utc_date
            ORDER BY utc_date ASC
            ''', ctx.guild.id)
        s = f'Server activity\n```\n'
        if use_numbers:
            prev_date = datetime.now().date() - timedelta(days=30)
            for record in ac:
                date = record['utc_date']
                if date < prev_date:
                    continue
                while (date > prev_date):
                    s += prev_date.strftime(f'%b %d(%a): 0\n')
                    prev_date += timedelta(days=1)
                prev_date += timedelta(days=1)
                count = record['count']
                s += date.strftime(f'%b %d(%a): {count}\n')
        else:
            max_num = max(ac, key=lambda r: r['count'])['count']
            s += f'Unit: {max_num // 15} messages\n'
            prev_date = datetime.now().date() - timedelta(days=30)
            for record in ac:
                date = record['utc_date']
                if date < prev_date:
                    continue
                while (date > prev_date):
                    s += prev_date.strftime(f'%b %d(%a):\n')
                    prev_date += timedelta(days=1)
                prev_date += timedelta(days=1)
                count = record['count']
                ticks = 15 * count // max_num
                bar = '-' * ticks
                s += date.strftime(f'%b %d(%a): {bar}\n')

        s += '```'
        await ctx.send(s)

    @commands.Cog.listener()
    async def on_safe_message(self, m, **kwargs):
        lang = kwargs['lang']
        if REGEX_BOT_COMMANDS.match(m.content):
            lang = 'OL'
        custom_emoji_matches = REGEX_CUSTOM_EMOJIS.findall(m.content)
        emojis = custom_emoji_matches + kwargs['emojis']

        async with self._batch_lock:
            self._temp_messages[(m.guild.id, m.channel.id, m.author.id, lang, m.created_at.date())] += 1
            if emojis:
                self._temp_emojis[(m.guild.id, m.author.id, m.created_at.date())] += Counter(emojis)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        async with self._batch_lock:
            vc = self.in_vc[member.guild.id]
            if not is_vc(before) and is_vc(after):
                vc[member.id] = datetime.utcnow()
                # TODO: Unmute people who are in the unmute queue?
            elif is_vc(before) and not is_vc(after):
                    if member.id in vc:
                        self.add_to_temp_vc(member.id, member.guild.id, vc)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        async with self._batch_lock:
            vc = self.in_vc[member.guild.id]
            if member.id in vc:
                self.add_to_temp_vc(member.id, member.guild.id, vc)
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        # No bot navigation reactions
        if reaction.message.author.bot:
            return
        if reaction.message.guild is None:
            return
        emoji = str(reaction.emoji)
        if emoji in [JP_EMOJI, EN_EMOJI, OL_EMOJI]:
            return
        today = datetime.utcnow().date()
        async with self._batch_lock:
            self._temp_emojis[(reaction.message.guild.id, user.id, today)][emoji] += 1

    # Add current members in VC
    @commands.Cog.listener()
    async def on_ready(self):
        log.info('statistics on_ready')
        async with self._batch_lock:
            for guild in self.bot.guilds:
                vc = self.in_vc[guild.id]
                for vcs in guild.voice_channels:
                    for member in vcs.members:
                        if is_vc(member.voice):
                            vc[member.id] = datetime.utcnow()

    @commands.Cog.listener()
    async def on_disconnect(self):
        # flush people in VC now
        log.info('statistics on_disconnect')
        async with self._batch_lock:
            for guild_id, vc in self.in_vc.items():
                for mem_id in vc:
                    self.add_to_temp_vc(mem_id, guild_id, vc, delete=False)
            self.in_vc.clear()

    def cog_unload(self):
        log.info('statistics unloading')
        self.batch_update.cancel()

    # Needs to have _batch_lock
    def add_to_temp_vc(self, member_id, guild_id, vc, *, delete=True):
        now = datetime.utcnow()
        elapsed_mins = (now - vc[member_id]).total_seconds() / 60
        if delete:
            del vc[member_id]
        self._temp_voice[(guild_id, member_id, now.date())] += elapsed_mins

    
    # Needs to have _batch_lock
    def do_batch(self):
        messages = []
        for (guild_id, channel_id, user_id, lang, date), count in self._temp_messages.items():
            messages.append({
                'guild_id': guild_id,
                'channel_id': channel_id,
                'user_id': user_id,
                'lang': lang,
                'utc_date': date,
                'message_count': count
            })
        emojis = []
        for (guild_id, user_id, date), emoji_counter in self._temp_emojis.items():
            for emoji, emoji_count in emoji_counter.items():
                emojis.append({
                'guild_id': guild_id,
                'user_id': user_id,
                'emoji': emoji,
                'utc_date': date,
                'emoji_count': emoji_count
                })
        voices = []
        for (guild_id, user_id, date), minutes in self._temp_voice.items():
            voices.append({
                'guild_id': guild_id,
                'user_id': user_id,
                'utc_date': date,
                'minute_count': minutes
            })
        self._temp_messages.clear()
        self._temp_emojis.clear()
        self._temp_voice.clear()
        return messages, emojis, voices

    

    @tasks.loop(seconds=20.0)
    async def batch_update(self):
        async with self._batch_lock:
            messages, emojis, voices = self.do_batch()
        await self.bulk_insert(messages, emojis, voices)

    @batch_update.before_loop
    async def before_batch_update(self):
         log.info('bath_update starting...')

    @batch_update.after_loop
    async def on_batch_update_cancel(self):
        log.info('bath_update canecelling...')

        if self.batch_update.is_being_cancelled():
            for guild_id, vc in self.in_vc.items():
                for mem_id in vc:
                    self.add_to_temp_vc(mem_id, guild_id, vc, delete=False)
            self.in_vc.clear()
            messages, emojis, voices = self.do_batch()
            await self.bulk_insert(messages, emojis, voices)


    async def bulk_insert(self, messages, emojis, voices):
        await asyncio.gather(
            self.pool.execute('''
                INSERT INTO messages (guild_id, channel_id, user_id, lang, utc_date, message_count)
                SELECT m.guild_id, m.channel_id, m.user_id, m.lang, m.utc_date, m.message_count
                FROM UNNEST($1::messages[]) AS m
                ON CONFLICT ON CONSTRAINT messages_pk DO UPDATE
                SET message_count = messages.message_count + EXCLUDED.message_count
                ''', messages),
            self.pool.execute('''
                INSERT INTO emojis (guild_id, user_id, emoji, utc_date, emoji_count)
                SELECT e.guild_id, e.user_id, e.emoji, e.utc_date, e.emoji_count
                FROM UNNEST($1::emojis[]) AS e
                ON CONFLICT ON CONSTRAINT emojis_pk DO UPDATE
                SET emoji_count = emojis.emoji_count + EXCLUDED.emoji_count
                ''', emojis),
            self.pool.execute('''
                INSERT INTO voice (guild_id, user_id, utc_date, minute_count)
                SELECT v.guild_id, v.user_id, v.utc_date, v.minute_count
                FROM UNNEST($1::voice[]) AS v
                ON CONFLICT ON CONSTRAINT voice_pk DO UPDATE
                SET minute_count = voice.minute_count + EXCLUDED.minute_count
                ''', voices)
        )


    @tasks.loop(hours=24)
    async def clear_old_records(self):
        async with self._batch_lock:
            await self.pool.execute('''
                DELETE FROM messages WHERE utc_date < NOW() - INTERVAL '30 days';
                DELETE FROM emojis WHERE utc_date < NOW() - INTERVAL '30 days';
                DELETE FROM voice WHERE utc_date < NOW() - INTERVAL '30 days';
                ''')
    
def setup(bot):
    bot.add_cog(Stats(bot))