
import discord
import asyncio
from .resolver import has_any_role


MOD_ROLES = [189594666365091850, 543721608506900480]
MINIMO_ROLES = MOD_ROLES + [755269385094168576]

async def wait_for_reaction(client: discord.client, message: discord.Message, reaction: str, user_id: int, timeout=300.0, triple_click=False):
    """
    client: Discord bot client
    message: Discord message object
    reaction: reaction resolvable
    user_id: wait for specific user
    """
    def check(reaction, user):
        if user_id:
            return user.id == user_id and str(reaction.emoji) == reaction
        return has_any_role(user, MOD_ROLES) and str(reaction.emoji) == reaction

    try:
        reaction, user = await client.wait_for('reaction_add', timeout=timeout, check=check)
        return user
    except asyncio.TimeoutError:
        return None
