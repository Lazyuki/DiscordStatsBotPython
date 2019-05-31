import discord

# Can access members with dots
def Map(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

def has_role(member, role_id):
    if not member:
        return False
    return discord.utils.find(lambda r: r.id == role_id, member.roles) is not None

def get_minimum_channel(ctx, channel_id):
    channel = ctx.guild.get_channel(channel_id)
    if channel is None:
        channel = Map.__init__({ 
            'name': f'#deleted-channel({channel_id})',
            'id': channel_id
        })
    return channel

def get_config(guild_id, config_name, default=None):
    pass