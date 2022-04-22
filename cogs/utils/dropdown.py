from typing import List, Optional
from discord import ui
import discord
import asyncio
from .resolver import has_any_role

NJ_ID = 196765998706196480
FJ_ID = 270391106955509770
NE_ID = 197100137665921024
FE_ID = 241997079168155649
OL_ID = 248982130246418433

options = [
    discord.SelectOption(label="Native Japanese Speaker", value=str(NJ_ID), emoji="🇯🇵"),
    discord.SelectOption(label="Native English Speaker", value=str(NE_ID), emoji="🇬🇧"),
    discord.SelectOption(
        label="Other Language",
        value=str(OL_ID),
        description="this is what description looks like",
        emoji="🧡",
    ),
]


class DropdownView(ui.View):
    def __init__(self):
        super().__init__()

    @ui.select(placeholder="Language Role", options=options)
    async def select(self, interaction: discord.Interaction, menu: discord.ui.Select):
        await interaction.response.send_message(
            f"You have chosen <@&{menu.values[0]}>", ephemeral=True
        )

    async def interaction_check(self, interaction):
        allowed = False
        if isinstance(interaction.user, discord.Member):
            if interaction.user.guild_permissions.manage_roles:
                allowed = True

        if not allowed:
            await interaction.response.send_message(
                "You do not have permission", ephemeral=True
            )

        return allowed


async def send_dropdown(
    channel: discord.TextChannel | discord.Thread,
    content: str = "",
):
    view = DropdownView()
    message = await channel.send(content=content, view=view)
    timed_out = await view.wait()
    if message:
        if timed_out and len(message.embeds) > 0:
            embed = message.embeds[0].copy()
            embed.set_footer(text=f"Timed out after 5 minutes")
            await message.edit(content=message.content, embed=embed, view=None)
