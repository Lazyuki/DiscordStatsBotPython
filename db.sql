DROP TYPE IF EXISTS langtype;
CREATE TYPE langtype AS ENUM ('OL', 'JP', 'EN');

CREATE TABLE IF NOT EXISTS guilds(
  guild_id BIGINT UNIQUE PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS messages(
  guild_id BIGINT NOT NULL REFERENCES guilds(guild_id),
  channel_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  lang LANGTYPE NOT NULL, -- 0 = ol, 1 = jp, 2 = en
  utc_date DATE NOT NULL,
  message_count INT NOT NULL
);
ALTER TABLE messages ADD CONSTRAINT messages_pk PRIMARY KEY (guild_id, channel_id, user_id, lang, utc_date);


CREATE TABLE IF NOT EXISTS emojis(
  guild_id BIGINT NOT NULL REFERENCES guilds(guild_id),
  user_id BIGINT NOT NULL,
  emoji TEXT NOT NULL,
  utc_date DATE NOT NULL,
  emoji_count INT NOT NULL
);
ALTER TABLE emojis ADD CONSTRAINT emojis_pk PRIMARY KEY (guild_id, user_id, emoji, utc_date);

CREATE TABLE IF NOT EXISTS voice(
  guild_id BIGINT NOT NULL REFERENCES guilds(guild_id),
  user_id BIGINT NOT NULL,
  utc_date DATE NOT NULL,
  minute_count INT NOT NULL
);
ALTER TABLE voice ADD CONSTRAINT voice_pk PRIMARY KEY (guild_id, user_id, utc_date);

CREATE TABLE IF NOT EXISTS deletes(
    guild_id BIGINT NOT NULL REFERENCES guilds(guild_id),
    user_id BIGINT NOT NULL,
    utc_date DATE NOT NULL,
    delete_count INT NOT NULL
);
ALTER TABLE deletes ADD CONSTRAINT delete_pk PRIMARY KEY (guild_id, user_id, utc_date);


-- ,u
CREATE INDEX IF NOT EXISTS message_guild_user_id_idx ON messages(guild_id, user_id);
CREATE INDEX IF NOT EXISTS emoji_guild_user_id_idx ON emojis(guild_id, user_id);
CREATE INDEX IF NOT EXISTS voice_guild_user_id_idx ON voice(guild_id, user_id);

-- ,channel-leaderboard
CREATE INDEX IF NOT EXISTS message_channel_idx ON messages(channel_id);

-- For deleting old ones
CREATE INDEX IF NOT EXISTS message_date_idx ON messages(utc_date); 
CREATE INDEX IF NOT EXISTS emoji_date_idx ON emojis(utc_date);
CREATE INDEX IF NOT EXISTS voice_date_idx ON voice(utc_date);
