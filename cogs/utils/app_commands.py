from discord.ext import commands
from discord import app_commands
import discord
from .resolver import has_any_role

EJLX_ID = 189571157446492161
MOD_ROLES = [189594666365091850, 543721608506900480]
MINIMO_ROLES = MOD_ROLES + [755269385094168576]
WP_ROLES = MINIMO_ROLES + [250907197075226625]


async def check_wp(interaction: discord.Interaction):
    allowed = False
    if isinstance(interaction.user, discord.Member):
        allowed = has_any_role(interaction.user, WP_ROLES)
        if interaction.user.guild_permissions.administrator:
            allowed = True

    if not allowed:
        await interaction.response.send_message(
            "You do not have permission", ephemeral=True
        )
    return allowed


async def tag(interaction: discord.Interaction, msg: discord.Message, role_id: int):
    if not isinstance(msg.author, discord.Member):
        return False
    if msg.guild is None:
        return False
    role = msg.guild.get_role(role_id)
    nu = msg.guild.get_role(249695630606336000)
    if not role or not nu:
        return False
    await msg.author.add_roles(
        role,
        reason=f"Context menu tagged by {interaction.user.name} ({interaction.user.id})",
    )
    try:
        await msg.author.remove_roles(
            nu,
            reason=f"Context menu tagged by {interaction.user.name} ({interaction.user.id})",
        )
    except:
        pass
    await interaction.response.send_message(
        f"{msg.author} has been tagged as <@&{role_id}>",
        ephemeral=True,
    )
    return True


@app_commands.context_menu(name="Tag NJ")
@app_commands.check(check_wp)
async def tag_nj(interaction: discord.Interaction, message: discord.Message):
    res = await tag(interaction, message, 196765998706196480)
    if not res:
        await interaction.response.send_message(f"Failed to tag", ephemeral=True)


@app_commands.context_menu(name="Tag NE")
@app_commands.check(check_wp)
async def tag_ne(interaction: discord.Interaction, message: discord.Message):
    res = await tag(interaction, message, 197100137665921024)
    if not res:
        await interaction.response.send_message(f"Failed to tag", ephemeral=True)


@app_commands.context_menu(name="Tag OL")
@app_commands.check(check_wp)
async def tag_ol(interaction: discord.Interaction, message: discord.Message):
    res = await tag(interaction, message, 248982130246418433)
    if not res:
        await interaction.response.send_message(f"Failed to tag", ephemeral=True)


async def init_ejlx_commands(bot: commands.Bot):
    tree = bot.tree
    ejlx = bot.get_guild(EJLX_ID)

    tree.add_command(tag_nj, guild=ejlx)
    tree.add_command(tag_ne, guild=ejlx)
    tree.add_command(tag_ol, guild=ejlx)
    await tree.sync(guild=ejlx)


async def delete_ejlx_commands(bot: commands.Bot):
    tree = bot.tree
    ejlx = bot.get_guild(EJLX_ID)
    tree.remove_command("Tag NJ", guild=ejlx, type=discord.AppCommandType.message)
    tree.remove_command("Tag NE", guild=ejlx, type=discord.AppCommandType.message)
    tree.remove_command("Tag OL", guild=ejlx, type=discord.AppCommandType.message)
    await tree.sync(guild=ejlx)
