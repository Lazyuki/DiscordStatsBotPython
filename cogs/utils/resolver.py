import discord
import re
import shlex

ID_REGEX = re.compile(r'([0-9]{15,21})>?\b')

# Can access members with dots
def Map(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def has_role(member, role_id):
    if not member or not member.roles:
        return False
    return discord.utils.find(lambda r: r.id == role_id, member.roles) is not None

def has_any_role(member, role_ids):
    if not member or not member.roles:
        return False
    return discord.utils.find(lambda r: r.id in role_ids, member.roles) is not None


def resolve_minimum_channel(ctx, channel_id):
    channel = ctx.guild.get_channel(channel_id)
    if channel is None:
        channel = Map.__init__({ 
            'name': f'#deleted-channel({channel_id})',
            'id': channel_id
        })
    return channel

def resolve_user_id(ctx, arg):
    id_match = ID_REGEX.match(arg)
    guild = ctx.guild
    user_id = None
    if id_match is None:
        arg = arg.lower()
        arg_len = len(arg)
        username_exact = None
        potential_matches = {}
        partial_matches = {}
        members = guild.members
        for member in members:
            username = member.name.lower()
            usertag = f'{username}#{member.discriminator}'.lower()
            nick = member.nick.lower() if member.nick else ''
            member_id = member.id
            # In order of priority
            if usertag == arg:
                return member_id
            if username == arg:
                username_exact = member_id
            elif nick == arg:
                potential_matches[0] = member_id
            elif username.startswith(arg):
                potential_matches[len(username) - arg_len] = member_id
            elif nick.startswith(arg):
                potential_matches[len(nick) - arg_len] = member_id
            elif arg in username:
                partial_matches[len(username) - arg_len] = member_id
            elif arg in usertag:
                partial_matches[len(usertag) - arg_len] = member_id
            elif arg in nick:
                partial_matches[len(nick) - arg_len] = member_id

        if username_exact:
            return username_exact
        if potential_matches:
            closest = min(potential_matches.keys())
            return potential_matches[closest]
        if partial_matches:
            closest = min(partial_matches.keys())
            return partial_matches[closest]
    else:
        user_id = int(id_match.group(1))
    return user_id
        
def resolve_role(ctx, role):
    roles = ctx.guild.roles
    role = role.lower()
    starts = []
    contains = []
    for r in roles:
        name = r.name.lower()
        if name == role:
            return r
        if name.startswith(role):
            starts.append(r)
        if role in name:
            contains.append(r)
    if starts:
        return starts[0]
    if contains:
        return contains[0]
    return None

    

def resolve_options(content: str, accepted_options: dict) -> tuple[str, dict[str, str]]:
    """
    accepted_options: {
        name: {
            abbrev: str;
            boolean: bool;
        }
    }
    """
    if (not content) or (not accepted_options):
        return (content, {})
    resolved = {}
    rest_content = []
    names = accepted_options.keys()
    abbrevs = { opt['abbrev']: key for key, opt in accepted_options.items() }
    words = shlex.split(content)
    word_iter = iter(words)
    try:
        while True:
            word = next(word_iter)
            if word.startswith('--'):
                name = word[2:]
                if name in names:
                    opt = accepted_options[name]
                    boolean = opt['boolean']
                    if boolean:
                        resolved[name] = True
                    else:
                        resolved[name] = next(word_iter)
            elif word.startswith('-'):
                abbrev = word[1:]
                if abbrev in abbrevs:
                    name = abbrevs[abbrev]
                    opt = accepted_options[name]
                    boolean = opt['boolean']
                    if boolean:
                        resolved[name] = True
                    else:
                        resolved[name] = next(word_iter)
            else:
                rest_content.append(word)
    except StopIteration:
        pass

    return (' '.join(rest_content), resolved)
    
