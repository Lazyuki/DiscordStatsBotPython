from typing import List
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
        message: discord.Message,
        bannees: List[discord.Member],
        reason=str,
        unmute_dismissed=False,
        delete_dismissed=False,
        wp=False,
        minimo=False,
    ):
        super().__init__()
        self.timeout = 300.0

        self.message = message
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
            for bannee in self.bannees:
                try:
                    await bannee.ban(
                        delete_message_days=1,
                        reason=f"Issued by: {banner.name} ({banner.id}). Reason: {self.reason}",
                    )
                    await self.message.channel.send(
                        f"\N{WHITE HEAVY CHECK MARK} {bannee} has been banned by {banner}"
                    )
                except:
                    await self.message.channel.send(
                        f"\N{CROSS MARK} {bannee} could not be banned."
                    )
            if len(self.message.embeds) > 0:
                embed = self.message.embeds[0]
                embed.set_footer(text=f"Banned by {banner.name}")
                await self.message.edit(content=self.message.content, embed=embed)
            self.stop()

    @ui.button(label="Dismiss", style=discord.ButtonStyle.secondary)
    async def dismiss(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        async with self._lock:
            if self.is_finished():
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
                            await self.message.channel.send(
                                f"\N{WHITE HEAVY CHECK MARK} Unmuted {bannee.name}"
                            )
                        except:
                            pass
            if self.delete_dismissed:
                await self.message.delete()
            elif len(self.message.embeds) > 0:
                embed = self.message.embeds[0].copy()
                if self.unmute_dismissed:
                    embed.set_footer(
                        text=f"False alarm. They have been unmuted. Dimissed by {interaction.user.name}"
                    )
                else:
                    embed.set_footer(
                        text=f"False alarm. Dimissed by {interaction.user.name}"
                    )
                await self.message.edit(content=self.message.content, embed=embed)
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

    async def on_timeout(self):
        embed = None
        if len(self.message.embeds):
            embed = self.message.embeds[0].copy()
            embed.set_footer(text=f"Timed out after 5 minutes")
        await self.message.edit(content=self.message.content, embed=embed, view=None)


async def add_ban_dismiss(message: discord.Message, view: ui.View):
    await message.edit(content=message.content, embeds=message.embeds, view=view)
