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
REGEX_BOT_COMMANDS = re.compile(r'^(?:[trkhHm]?q?!|[,.&+>$%;=\]-])')

# Languages
LANGS = ['german', 'italian', 'french', 'spanish',
         'portuguese', 'korean', 'chinese', 'telugu', 'hindi', 'urdu', 'tamil', 'malay',
         'dutch', 'arabic', 'russian', 'turkish', 'mandarin', 'cantonese', 'polish', 'swedish',
         'tagalog', 'norwegian', 'vietnamese', 'filipino', 'fillipino', 'thai', 'indonesian', 'hebrew']

COUNTRIES = ['germany', 'italy', 'france', 'spain', 'portugal', 'brazil', 'korea', 'china',
             'taiwan', 'india', 'malaysia', 'netherland', 'russia', 'poland', 'sweden', 'turkey', 'norway',
             'vietnam', 'philippines', 'indonesia', 'saudi', 'netherlands', 'thailand']

NATIVE = re.compile(r'native(?: language)?(?: is)? (\w+)')
NATIVE2 = re.compile(r'(\w+) (is my )?native')
NATIVEJP = re.compile(r'母国?語.(.+?)語')
FLUENT_EN = re.compile(r'fluet (in )? english')
FROM = re.compile(r"i(?:'?m| am) from (?:the )?(?:united )?(\w+)")
IM = re.compile(r"i(?:'?m| am)(?: a)? (\w+)")
STUDY = re.compile(
    r'(?:learn|study|studied|in|at|to|beginner|taking|took|speak|my)(?:ing| some| the| more)? (japanese|english)(?: and (english|japanese))?')
JP_STUDY = re.compile(r'(日本語|英語).?(?:勉強|学練習|話した)')

# Emojis
JP_EMOJI = '<:japanese:439733745390583819>'
EN_EMOJI = '<:english:439733745591779328>'
OL_EMOJI = '<:other_lang:815698119810875453>'


async def guess_lang(message):
    msg = message.content.lower()
    m = NATIVE.search(msg)
    if m:
        nat = m.group(1)
        m2 = NATIVE2.search(msg)
        if nat == 'japanese' or m2 and m2.group(1) == 'japanese':
            await message.add_reaction(JP_EMOJI)
        elif nat == 'english' or m2 and m2.group(1) == 'english':
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
        elif orig in ['english', 'canadian', 'australian', 'british', 'american']:
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
        w = re.sub(r'\W', '', w)
        if w in LANGS or w in COUNTRIES:
            await message.add_reaction(OL_EMOJI)
            return
    m = STUDY.search(msg)
    not_jp = False
    not_en = False
    if m:
        msg = STUDY.sub('', msg)
        lang = m.group(1)
        if lang == 'japanese':
            not_jp = True
        elif lang == 'english':
            not_en = True
    m = JP_STUDY.search(msg)
    if m:
        msg = JP_STUDY.sub('', msg)
        lang = m.group(1)
        if lang == '日本語':
            not_jp = True
        else:
            not_en = True

    if not not_jp and ('japanese' in msg or '日本語' in msg):
        await message.add_reaction(JP_EMOJI)
        return
    if not not_en and ('english' in msg or '英語' in msg):
        await message.add_reaction(EN_EMOJI)
        return
    msg = re.sub(r'(母国?|言)語', '', msg)
    if '語' in msg:
        await message.add_reaction(OL_EMOJI)
        return


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
        lang = 'OL'  # unknown
    elif jp_count < 3 and en_count < 3 and ol_count > 0:
        lang = 'OL'  # probably an emoticon e.g. ¯\_(ツ)_/¯
    elif jp_count * JP_RATIO > en_count:
        lang = 'JP'
    else:
        lang = 'EN'
    return (lang, escaped, emojis)


QUESTION = ['how', 'why', 'y', "can't", 'can', 'cant']
VERB = ['access', 'join', 'use', 'unlock', 'enter']
VC = ['vc', 'vcs', 'voice', 'call', 'room', 'calls']
LOCK = ['locked', 'lock']


async def asking_vc(message):
    # introductions
    if message.channel.id == 395741560840519680:
        return
    msg = message.content.lower()
    vc = False
    asking = False
    for w in msg.split():
        w = re.sub(r'\W', '', w)
        if w in VC:
            vc = True
        elif w in QUESTION or w in VERB or w in LOCK:
            asking = True
    if vc and asking:
        await message.reply(f'As mentioned in <#189585230972190720>, you need a language role to join voice chat. Please say what your native language is {"here" if message.channel.id == 189571157446492161 else "in <#189571157446492161>"}', mention_author=True)

def format_timedelta(timedelta):
    seconds = int(timedelta.total_seconds())
    periods = [
        ('year',        60*60*24*365),
        ('month',       60*60*24*30),
        ('day',         60*60*24),
        ('hour',        60*60),
        ('minute',      60),
        ('second',      1)
    ]

    strings=[]
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value , seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))

    return ", ".join(strings)