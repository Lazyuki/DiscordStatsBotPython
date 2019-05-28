import re
import emoji
import regex

REGEX_JPN = re.compile(r'[\u3040-\u30FF]|[\uFF66-\uFF9D]|[\u4E00-\u9FAF]')
REGEX_ENG = re.compile(r'[a-vx-zA-VX-Z]|[ａ-ｖｘ-ｚＡ-ＶＸ-Ｚ]')
REGEX_URL = re.compile(r'https?:\/\/(www\.)?\S{2,256}\.[a-z]{2,6}\S*')

REGEX_CUSTOM_EMOJIS = re.compile(r'(<a?:\S+?:\d+>)')
REGEX_USER = re.compile(r'<@!?\d+>')
REGEX_CHAN = re.compile(r'<#\d+>')
REGEX_ROLE = re.compile(r'<@&\d+>')
REGEX_DISCORD_OBJ = re.compile(r'<(?:@!?|#|@&|a?:\S+?:)\d+>')
REGEX_RAW_ID = re.compile(r'(\d{17,21})')
REGEX_BOT_COMMANDS = re.compile(r'^(?:[trkhHm]?q?!|[,.&+>$%;=\]])')

def extract_unicode_emojis(text):
  # https://stackoverflow.com/a/49242754
  emoji_list = []
  data = regex.findall(r'\X', text)
  for word in data:
      if any(char in emoji.UNICODE_EMOJI for char in word):
          emoji_list.append(word)
  return emoji_list

JP_RATIO = 1.7

def parse_language(message):
  jp_count = en_count = ol_count = 0
  escaped = False
  lang = ''
  content = REGEX_DISCORD_OBJ.sub('', message.content)
  content = REGEX_URL.sub('', content)
  emojis = extract_unicode_emojis(content)
  for emoji in emojis:
    content = content.replace(emoji, '')
  for c in content:
    if c == '*' or c == '＊':
      escaped = True
    elif REGEX_ENG.match(c):
      en_count += 1
    elif REGEX_JPN.match(c):
      jp_count += 1
    elif not re.match(r'[\swWｗＷ]', c):
      ol_count += 1
  if jp_count == 0 and en_count == 0:
    lang = 'OL' # unknown
  elif jp_count < 3 and en_count < 3 and ol_count > 0:
    lang = 'OL' # probably an emoticon e.g. ¯\_(ツ)_/¯
  elif jp_count * JP_RATIO > en_count:
    lang = 'JP'
  else:
    lang = 'EN'
  return (lang, escaped, emojis)
