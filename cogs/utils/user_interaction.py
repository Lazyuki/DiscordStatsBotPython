import discord
import asyncio
from .resolver import has_any_role


MOD_ROLES = [189594666365091850, 543721608506900480]
MINIMO_ROLES = MOD_ROLES + [755269385094168576]
WP_ROLES = MINIMO_ROLES + [250907197075226625]


async def wait_for_reaction(
    client: discord.Client,
    message: discord.Message,
    reaction: str,
    user_id: int = None,
    timeout=300.0,
    triple_click=False,
    minimo=False,
    wp=False,
):
    """
    Wait for a specific reaction from user/roles

    client: Discord bot client
    message: Discord message object
    reaction: reaction resolvable
    user_id: wait for specific user

    @returns (user, return_false)
    """
    roles = WP_ROLES if wp else MINIMO_ROLES if minimo else MOD_ROLES
    clicked_once = []

    def check(rxn, user):
        if str(rxn.emoji) != reaction:
            return False

        if triple_click:
            if user.id not in clicked_once:
                clicked_once.append(user.id)
                return False

        if user_id:
            return user.id == user_id
        return has_any_role(user, roles)

    try:
        rxn, user = await client.wait_for("reaction_add", timeout=timeout, check=check)
        return (user, reaction)
    except asyncio.TimeoutError:
        return None
