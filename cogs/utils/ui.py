from typing import List, Optional
from discord import ui
import discord
import asyncio
from .resolver import has_any_role


MOD_ROLES = [189594666365091850, 543721608506900480]
MINIMO_ROLES = MOD_ROLES + [755269385094168576]
WP_ROLES = MINIMO_ROLES + [250907197075226625]
CHAT_MUTE_ROLE = 259181555803619329


class BanDismissView(ui.View):
    def __init__(
        self,
        *,
        bannees: List[discord.Member],
        reason: str = "Unspecified",
        unmute_dismissed=False,
        delete_dismissed=False,
        wp=False,
        minimo=False,
    ):
        super().__init__()
        self.timeout = 300.0

        self.bannees = bannees
        self.reason = reason
        self.unmute_dismissed = unmute_dismissed
        self.delete_dismissed = delete_dismissed
        self.wp = wp
        self.minimo = minimo

        self._lock = asyncio.Lock()

    @ui.button(label="BAN", style=discord.ButtonStyle.danger)
    async def ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with self._lock:
            if self.is_finished():
                return
            await interaction.response.edit_message(view=None)
            banner = interaction.user
            message = interaction.message
            if not message:
                return
            for bannee in self.bannees:
                try:
                    await bannee.ban(
                        delete_message_days=1,
                        reason=f"By: {banner} ({banner.id}). Reason: {self.reason}",
                    )
                    await message.channel.send(
                        f"\N{WHITE HEAVY CHECK MARK} {bannee} has been banned by {banner}"
                    )
                except:
                    await message.channel.send(
                        f"\N{CROSS MARK} {bannee} could not be banned."
                    )
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                embed.set_footer(text=f"Banned by {banner}")
                await interaction.edit_original_message(embed=embed)
            self.stop()

    @ui.button(label="Dismiss", style=discord.ButtonStyle.secondary)
    async def dismiss(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        async with self._lock:
            if self.is_finished():
                return
            message = interaction.message
            if not message:
                return
            await interaction.response.edit_message(view=None)
            if self.unmute_dismissed:
                mute_role = self.bannees[0].guild.get_role(CHAT_MUTE_ROLE)
                if mute_role:
                    for bannee in self.bannees:
                        try:
                            await bannee.remove_roles(
                                mute_role,
                                reason=f"Auto mute dismissed",
                            )
                            await message.channel.send(
                                f"\N{WHITE HEAVY CHECK MARK} Unmuted {bannee.name}"
                            )
                        except:
                            pass
            if self.delete_dismissed:
                await interaction.delete_original_message()
            elif len(message.embeds) > 0:
                embed = message.embeds[0].copy()
                if self.unmute_dismissed:
                    embed.set_footer(
                        text=f"False alarm. They have been unmuted. Dimissed by {interaction.user}"
                    )
                else:
                    embed.set_footer(
                        text=f"False alarm. Dimissed by {interaction.user}"
                    )
                await interaction.edit_original_message(embed=embed)
            self.stop()

    async def interaction_check(self, interaction):
        roles = WP_ROLES if self.wp else MINIMO_ROLES if self.minimo else MOD_ROLES
        allowed = False
        if isinstance(interaction.user, discord.Member):
            allowed = has_any_role(interaction.user, roles)
            if interaction.user.guild_permissions.ban_members:
                allowed = True

        if not allowed:
            await interaction.response.send_message(
                "You do not have permission", ephemeral=True
            )

        return allowed


async def button_ban(
    channel: discord.TextChannel | discord.Thread,
    bannees: List[discord.Member],
    embed: discord.Embed,
    wp: bool = False,
    minimo: bool = False,
    unmute_dismissed: bool = False,
    delete_dismissed: bool = False,
    reason: str = "Unspecified",
    content: str = "",
    reply_message: discord.Message | None = None,
    mention_author: bool = False,
):
    view = BanDismissView(
        bannees=bannees,
        wp=wp,
        minimo=minimo,
        unmute_dismissed=unmute_dismissed,
        delete_dismissed=delete_dismissed,
        reason=reason,
    )
    message = None
    if reply_message:
        message = await reply_message.reply(
            content=content, embed=embed, mention_author=mention_author, view=view
        )
    else:
        message = await channel.send(content=content, embed=embed, view=view)
    timed_out = await view.wait()
    if message:
        if timed_out and len(message.embeds) > 0:
            embed = message.embeds[0].copy()
            embed.set_footer(text=f"Timed out after 5 minutes")
            await message.edit(content=message.content, embed=embed, view=None)
