import asyncpg
import asyncio
import logging
from collections import Counter
import config 

class Database:
  def __init__(self, config):
    self.config = config

  async def create_pool(self):
    if not hasattr(self, 'pool'):
      self.pool = await asyncpg.create_pool(**self.config)

  async def add_messages(self, messages):
    await self.pool.execute('''
      INSERT INTO messages (guild_id, channel_id, user_id, lang, utc_date, message_count)
      SELECT m.guild_id, m.channel_id, m.user_id, m.lang, m.utc_date, m.message_count
      FROM UNNEST($1::messages[]) AS m
      ON CONFLICT ON CONSTRAINT messages_pk DO UPDATE
      SET message_count = messages.message_count + EXCLUDED.message_count
    ''', messages)

  async def add_emojis(self, emojis):    
    await self.pool.execute('''
      INSERT INTO emojis (guild_id, user_id, emoji, utc_date, emoji_count)
      SELECT e.guild_id, e.user_id, e.emoji, e.utc_date, e.emoji_count
      FROM UNNEST($1::emojis[]) AS e
      ON CONFLICT ON CONSTRAINT emojis_pk DO UPDATE
      SET emoji_count = emojis.emoji_count + EXCLUDED.emoji_count
    ''', emojis)
  
  async def remove_emoji(self, guild_id, user_id, date, emoji):
    await self.pool.execute('''
      UPDATE emojis
      SET emoji_count = emoji_count - 1
      WHERE guild_id=$1 AND user_id=$2 AND emoji=$3 AND utc_date=$4
    ''', guild_id, user_id, emoji, date)

  async def add_voice(self, voices):
    await self.pool.execute('''
      INSERT INTO voice (guild_id, user_id, utc_date, minute_count)
      SELECT v.guild_id, v.user_id, v.utc_date, v.minute_count
      FROM UNNEST($1::voice[]) AS v
      ON CONFLICT ON CONSTRAINT voice_pk DO UPDATE
      SET minute_count = voice.minute_count + EXCLUDED.minute_count
    ''', voices)
  
  
  async def execute(self, query, *args):
    await self.pool.execute(query, *args)

  async def fetch(self, query, *args):
    return await self.pool.fetch(query, *args)

  async def fetchval(self, query, *args, **kwargs):
    return await self.pool.fetchval(query, *args, **kwargs)

  async def fetchrow(self, query):
    return await self.pool.fetchrow(query)

  async def close(self):
    await self.pool.close()