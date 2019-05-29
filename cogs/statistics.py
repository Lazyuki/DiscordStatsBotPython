from discord.ext import commands
import discord
from collections import Counter, defaultdict
import logging
import asyncio
import asyncpg
from datetime import datetime, date
from .utils.parser import REGEX_CUSTOM_EMOJIS, REGEX_BOT_COMMANDS

def is_vc(voice_state):
  return voice_state.channel and not voice_state.afk and not voice_state.self_deaf and not voice_state.deaf

class Stats(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.db = bot.db
    self.config = bot.config
    self.in_vc = defaultdict(dict)
    self._batch_lock = asyncio.Lock(loop=bot.loop)
    self._msg_lock = asyncio.Lock()
    self._emj_lock = asyncio.Lock()
    self._vc_lock = asyncio.Lock()
    self._temp_messages = defaultdict(int)
    self._temp_emojis = defaultdict(Counter)
    self._temp_voice = defaultdict(int)
    self._task = bot.loop.create_task(self.bulk_insert_loop())
    if bot.is_ready():
      print('cog loaded && bot is ready')
      for guild in bot.guilds:
        vc = self.in_vc[guild.id]
        for vcs in guild.voice_channels:
          for member in vcs.members:
            if is_vc(member.voice):
              vc[member.id] = datetime.utcnow()
  
  @commands.command(aliases=['u', 'uinfo'])
  async def user(self, ctx):
    user = ctx.author
    member = ctx.guild.get_member(user.id)

    emoji_data, voice, message_data = await asyncio.gather(
      self.db.fetch('''
        SELECT emoji, SUM(emoji_count) as count
        FROM emojis
        WHERE guild_id = $1 AND user_id = $2
        GROUP BY emoji
        ORDER BY count DESC
        LIMIT 3
        ''', ctx.guild.id, user.id),
      self.db.fetchval('''
        SELECT SUM(minute_count) as count
        FROM voice
        WHERE guild_id = $1 AND user_id = $2
        ''', ctx.guild.id, user.id),
      self.db.fetch('''
        WITH records AS (
            SELECT channel_id, lang, message_count, utc_date
            FROM messages
            WHERE guild_id = $1 AND user_id = $2
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
        ''', ctx.guild.id, user.id)
    )

    # Prepare embed
    embed = discord.Embed(colour=0x3A8EDB)
    nick = ''
    if member:
      if member.nick:
        nick = f' aka {member.nick}'
      embed.set_footer(text='Joined this server')
      embed.timestamp = member.joined_at
    else:
      embed.set_footer(text='Already left the server')

    embed.set_author(name=f'Stats for {user}{nick}', icon_url=user.avatar_url)

    # NO records
    if len(message_data) == 0:
      embed.description = "Hasn't said anything in the past 30 days"
      await ctx.send(embed=embed)
      return

    # Message total
    month_total = message_data[0]['count']
    week_total = message_data[-1]['count'] if message_data[-1]['channel_id'] is None else 0

    # Lang usage
    langs = { r['lang'] : r['count'] for r in message_data[1:4] if r['lang'] }
    is_jp = member and self.config.guilds[ctx.guild.id].get(['jp_role'], None) in member.roles
    EN = langs.get('EN', 0)
    JP = langs.get('JP', 0)
    BOTH = EN + JP
    if is_jp:
      usage_name = 'English usage'
      usage = EN / (BOTH) * 100 if BOTH > 0 else 0
    else:
      usage_name = 'Japanese usage'
      usage = JP / (BOTH) * 100 if BOTH > 0 else 0

    # Voice usage
    voice = 0 if voice is None else voice
    hrs = voice // 60
    mns = voice % 60
    voice_str = (f'{hrs}hr ' if hrs else '') + f'{mns}min'
    
    # Channel usage
    channels = Counter({ r['channel_id'] : r['count'] for r in message_data[2:] if r['channel_id']}).most_common(3)
    channel_str = ''
    for ch_id, count in channels:
      perc = count / month_total * 100
      channel = ctx.guild.get_channel(ch_id)
      if channel is None:
        channel = { 'name': 'deleted-channel' }
      channel_str += f'**#{channel.name}**: {round(perc, 1)}%\n'

    # Emoji usage
    emojis = { r['emoji'] : r['count'] for r in emoji_data }
    emoji_str = '\n'.join([f'{e} {count} times' for e, count in emojis.items()])

    # Build embed    
    embed.add_field(name='Messages Month | Week', value=f'{month_total} | {week_total}')
    embed.add_field(name=usage_name, value=f'{round(usage, 2)}%')
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
  async def leaderboard(self, ctx):
    user_id = ctx.author.id
    lb = await self.db.fetch('''
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
          SELECT * FROM ranked LIMIT 25
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

    embed = self.build_leaderboard(records, user_record=user_record)
    await ctx.send(embed=embed)

  @commands.command(aliases=['chlb', 'cl'])
  async def channel_leaderboard(self, ctx):
    user_id = ctx.author.id
    channel_id = ctx.channel.id
    channel_ids = [ channel_id ]
    chlb = await self.db.fetch('''
        WITH  ranked AS (
          SELECT *, RANK() OVER (ORDER BY count DESC)
            FROM (
              SELECT user_id, SUM(message_count) as count
              FROM messages
              WHERE guild_id = $1 AND channel_id = ANY ($2)
              GROUP BY user_id
              ORDER BY count DESC
            ) AS cl
          )
        (
          SELECT * FROM ranked LIMIT 25
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

    embed = self.build_leaderboard(records, title=title[:256], user_record=user_record)
    await ctx.send(embed=embed)

  @commands.command(aliases=['jplb', 'jpl'])
  async def japanese_leaderboard(self, ctx):
    pass

  @commands.command(aliases=['enlb', 'enl'])
  async def english_leaderboard(self, ctx):
    pass
  
  @commands.command(aliases=['vclb', 'vl', 'v'])
  async def voice_leaderboard(self, ctx):
    user_id = ctx.author.id
    vl = await self.db.fetch('''
        WITH  ranked AS (
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
          SELECT * FROM ranked LIMIT 25
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

    embed = self.build_leaderboard(records, title='Voice Leaderboard', user_record=user_record)
    await ctx.send(embed=embed)

  @commands.command(aliases=['ac', 'uac'])
  async def user_activity(self, ctx):
    user = ctx.author
    ac = await self.db.fetch('''
        SELECT SUM(message_count) as count, utc_date
        FROM messages
        WHERE guild_id = $1 AND user_id = $2
        GROUP BY utc_date
        ORDER BY utc_date ASC
        ''', ctx.guild.id, user.id)
    s = f'Server activity for **{user}**\n```\n'
    for record in ac:
      date = record['utc_date']
      count = record['count']
      s += date.strftime(f'%b %d(%a): {count}\n')
    s += '```'
    await ctx.send(s)

  @commands.command(aliases=['cac', 'chac'])
  async def channel_activity(self, ctx):
    pass

  @commands.command(aliases=['sac'])
  async def server_activity(self, ctx):
    pass

  @commands.Cog.listener()
  async def on_safe_message(self, m, **kwargs):
    lang =  kwargs['lang']
    if REGEX_BOT_COMMANDS.match(m.content):
      lang = 'OL'
    custom_emoji_matches = REGEX_CUSTOM_EMOJIS.findall(m.content)
    emojis = custom_emoji_matches + kwargs['emojis']
    async with self._msg_lock:
      self._temp_messages[(m.guild.id, m.channel.id, m.author.id, lang, m.created_at.date())] += 1
    if emojis:
      async with self._emj_lock:
          self._temp_emojis[(m.guild.id, m.author.id, m.created_at)] += Counter(emojis)

  @commands.Cog.listener()
  async def on_voice_state_update(self, member, before, after):
    async with self._vc_lock:
      vc = self.in_vc[member.guild.id]
      if not is_vc(before) and is_vc(after):
        vc[member.id] = datetime.utcnow()
        # TODO: Unmute people who are in the unmute queue?
      elif is_vc(before) and not is_vc(after):
        if member.id in vc:
          await self.add_to_temp_vc(member.id, member.guild.id, vc)

  @commands.Cog.listener()
  async def on_member_remove(self, member):
    async with self._vc_lock:
      vc = self.in_vc[member.guild.id]
      if member.id in vc:
        await self.add_to_temp_vc(member.id, member.guild.id, vc)
    
  @commands.Cog.listener()
  async def on_reaction_add(self, reaction, user):
    if user.bot:
      return
    if reaction.message.guild is None:
      return
    emoji = str(reaction.emoji)
    today = datetime.utcnow().date()
    async with self._emj_lock:
      self._temp_emojis[(reaction.message.guild.id, user.id, today)][emoji] += 1

  # Add current members in VC
  @commands.Cog.listener()
  async def on_ready(self):
    print('statistics on_ready')
    async with self._vc_lock:
      for guild in self.bot.guilds:
        vc = self.in_vc[guild.id]
        for vcs in guild.voice_channels:
          for member in vcs.members:
            if is_vc(member.voice):
              vc[member.id] = datetime.utcnow()

  @commands.Cog.listener()
  async def on_disconnect(self):
    # flush people in VC now
    print('statistics on_disconnect')
    async with self._vc_lock:
      for guild_id, vc in list(self.in_vc.items()):
        for mem_id in vc:
          await self.add_to_temp_vc(mem_id, guild_id, vc)

  async def add_to_temp_vc(self, member_id, guild_id, vc):
    now = datetime.utcnow()
    elapsed_mins = (now - vc[member_id]).total_seconds() / 60
    del vc[member_id]
    async with self._vc_lock:
      self._temp_voice[(guild_id, member_id, now.date())] += elapsed_mins 

  # Build leaderboard
  # Records must contain user_id, count, and rank fields
  def build_leaderboard(self, records, *, title='Leaderboard', user_record, count_to_string=lambda x: x):
    embed = discord.Embed(colour=0x3A8EDB)
    embed.title = title
    embed.description = 'For the last 30 days (UTC)'

    for record in records:
      ru_id = record['user_id']
      rank = record['rank']
      ru = self.bot.get_user(ru_id)
      if ru is None:
        name = f'{rank}) @deleted-user({ru_id})'
      else:
        name = f'{rank}) {ru.name}'
      embed.add_field(name=name, value=count_to_string(record['count']))
    if user_record and user_record['user_id'] is not None:
      user_id = user_record['user_id']
      user = self.bot.get_user(user_id)
      if user is None:
        username = f'@deleted-user({user_id})'
      else:
        username = user.name
      embed.set_footer (text='{}) {}: {}'.format(user_record['rank'], username, count_to_string(user_record['count'])))
    return embed


  def cog_unload(self):
    print('statistics unloading')
    # cancel the task we have looping
    self._task.cancel()

    # flush people in VC
    for guild_id, vc in list(self.in_vc.items()):
      for mem_id in vc:
        self.bot.loop.create_task(self.add_to_temp_vc(mem_id, guild_id, vc))

    # flush the temporary data
    self.bot.loop.create_task(self.bulk_insert())
        

  async def bulk_insert(self):
    if self._temp_messages.items():
      messages = []
      async with self._msg_lock:
        for (guild_id, channel_id, user_id, lang, date), count in self._temp_messages.items():
          messages.append({
            'guild_id': guild_id,
            'channel_id': channel_id,
            'user_id': user_id,
            'lang': lang,
            'utc_date': date,
            'message_count': count
            })
        self._temp_messages.clear()
      await self.db.add_messages(messages)
      

    if self._temp_emojis.items():
      emojis = []
      async with self._emj_lock:
        for (guild_id, user_id, date), emoji_counter in self._temp_emojis.items():
          for emoji, emoji_count in emoji_counter.items():
            emojis.append({
              'guild_id': guild_id,
              'user_id': user_id,
              'emoji': emoji,
              'utc_date': date,
              'emoji_count': emoji_count
            })
        self._temp_emojis.clear()
      await self.db.add_emojis(emojis)
      
    
    if self._temp_voice.items():
      voices = []
      async with self._vc_lock:
        for (guild_id, user_id, date), minutes in self._temp_voice.items():
          voices.append({
            'guild_id': guild_id,
            'user_id': user_id,
            'utc_date': date,
            'minute_count': minutes
          })
        self._temp_voice.clear()
      await self.db.add_voice(voices)

  async def bulk_insert_loop(self):
    try:
      while not self.bot.is_closed():
        await self.bulk_insert()  
        await asyncio.sleep(10)
      else:
        print('Bot is closed. Terminating bulk_insert_loop...')
    except asyncio.CancelledError:
      pass
    except (OSError, asyncpg.PostgresConnectionError):
      self._task.cancel()
      self._task = self.bot.loop.create_task(self.bulk_insert_loop())

      
def setup(bot):
  bot.add_cog(Stats(bot))