CREATE TYPE langtype AS ENUM ('OL', 'JP', 'EN');

CREATE TABLE IF NOT EXISTS guilds(
  guild_id BIGINT UNIQUE PRIMARY KEY,
  mod_channels BIGINT[],
  watched_users BIGINT[],

--   prefix CHAR(5),
--   ignored_channels BIGINT[],
--   ignored_users BIGINT[],
--   ignored_prefixes TEXT [],
--   log_channel BIGINT,
--   mod_log_channel BIGINT,
--   mod_roles BIGINT[],
--   jp_role BIGINT,
--   hc_role BIGINT,
--   hc_ignored_channels BIGINT[],
--   emoji_role_custom_message TEXT,
--   emoji_role_message_id TEXT, -- CHANNEL_ID-MESSAGE_ID
--   clock_category BIGINT,
--   clock_format TEXT,
--   enabled_modules TEXT[]
);

CREATE TABLE IF NOT EXISTS messages(
  guild_id BIGINT NOT NULL REFERENCES guilds(guild_id),
  channel_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  lang LANGTYPE NOT NULL, -- 0 = ol, 1 = jp, 2 = en
  utc_date DATE NOT NULL,
  message_count INT NOT NULL,
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


CREATE TABLE IF NOT EXISTS emoji_roles(
  guild_id BIGINT NOT NULL REFERENCES guilds(guild_id),
  emoji TEXT NOT NULL,
  role_id BIGINT NOT NULL,
  PRIMARY KEY(guild_id, emoji)
);

CREATE TABLE IF NOT EXISTS line_notifiers(
  user_id BIGINT NOT NULL,
  line_token TEXT NOT NULL,
  mention_id BIGINT NOT NULL, -- role or user ID
  only_offline BOOLEAN NOT NULL,
  PRIMARY KEY(user_id, mention_id)
);

CREATE TABLE IF NOT EXISTS command_aliases(
  guild_id BIGINT NOT NULL REFERENCES guilds(guild_id),
  alias TEXT NOT NULL,
  command TEXT NOT NULL
);
ALTER TABLE command_aliases ADD CONSTRAINT alias_pk PRIMARY KEY (guild_id, alias);


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
