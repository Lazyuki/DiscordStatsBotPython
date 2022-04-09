from typing import List
from discord import ui
import discord
import asyncio
from .resolver import has_any_role


MOD_ROLES = [189594666365091850, 543721608506900480]
MINIMO_ROLES = MOD_ROLES + [755269385094168576]
WP_ROLES = MINIMO_ROLES + [250907197075226625]
CHAT_MUTE_ROLE = 259181555803619329


def make_check_roles(wp=False, minimo=False):
    roles = WP_ROLES if wp else MINIMO_ROLES if minimo else MOD_ROLES

    async def check_roles(interaction: discord.Interaction):
        if isinstance(interaction.user, discord.Member):
            if interaction.user.guild_permissions.administrator:
                return True
            return has_any_role(interaction.user, roles)

        return False

    return check_roles


class BanButton(ui.Button):
    def __init__(self, ban):
        super().__init__()
        self.style = discord.ButtonStyle.danger
        self.custom_id = "BAN"
        self.label = "BAN"
        self.ban = ban

    async def callback(self, interaction: discord.Interaction):
        # Follow up?
        await interaction.response.edit_message(view=None)
        await self.ban(interaction.user)


class DismissButton(ui.Button):
    def __init__(self, dismiss):
        super().__init__()
        self.style = discord.ButtonStyle.secondary
        self.custom_id = "DISMISS"
        self.label = "Dismiss"
        self.dismiss = dismiss

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None)
        await self.dismiss(interaction.user)


class UnmuteButton(ui.Button):
    def __init__(self, unmute):
        super().__init__()
        self.style = discord.ButtonStyle.secondary
        self.custom_id = "UNMUTE"
        self.label = "Unmute"
        self.unmute = unmute

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None)
        await self.unmute(interaction.user)


class BanDismissView(ui.View):
    def __init__(
        self,
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
        self.unmute_dismissed = unmute_dismissed
        self.wp = wp
        self.minimo = minimo

        async def ban(banner: discord.Member):
            for bannee in bannees:
                try:
                    await bannee.ban(
                        delete_message_days=1,
                        reason=f"Issued by: {banner}. Reason: {reason}",
                    )
                    await message.channel.send(
                        f"\N{WHITE HEAVY CHECK MARK} {bannee} has been banned by {banner}"
                    )
                    await message.channel.send("BAN TEST SUCCESSFUL")
                except:
                    await message.channel.send(
                        f"\N{CROSS MARK} {bannee} could not be banned."
                    )
            if len(message.embeds) > 0:
                embed = message.embeds[0]
                embed.set_footer(text=f"Banned by {banner.name}")
                await message.edit(content=message.content, embed=embed)
            self.stop()

        async def unmute(unmuter: discord.Member | None):
            mute_role = bannees[0].guild.get_role(CHAT_MUTE_ROLE)
            for bannee in bannees:
                try:
                    if mute_role:
                        await bannee.remove_roles(
                            mute_role,
                            reason=f"Auto mute dismissed",
                        )
                        await message.channel.send(
                            f"\N{WHITE HEAVY CHECK MARK} Unmuted {bannee.name}"
                        )
                except:
                    pass
            if delete_dismissed:
                await message.delete()
            elif len(message.embeds) > 0:
                embed = message.embeds[0].copy()
                if unmuter:
                    embed.set_footer(
                        text=f"False alarm. They have been unmuted. Dimissed by {unmuter.name}"
                    )
                    await message.edit(content=message.content, embed=embed)
            self.stop()

        self.unmute = unmute

        async def dismiss(dismisser: discord.Member):
            if delete_dismissed:
                await message.delete()
            elif len(message.embeds) > 0:
                embed = message.embeds[0].copy()
                embed.set_footer(text=f"False alarm. Dimissed by {dismisser.name}")
                await message.edit(content=message.content, embed=embed)
            self.stop()

        self.add_item(BanButton(ban=ban))
        if unmute_dismissed:
            self.add_item(UnmuteButton(unmute=unmute))
        else:
            self.add_item(DismissButton(dismiss=dismiss))

    async def interaction_check(self, interaction):
        return make_check_roles(self.wp, self.minimo)(interaction)

    async def on_timeout(self):
        self.clear_items()
        embed = None
        if len(self.message.embeds):
            embed = self.message.embeds[0].copy()
            embed.set_footer(text=f"Timed out after 5 minutes")
        await self.unmute(None)
        await self.message.edit(content=self.message.content, embed=embed, view=None)


async def add_ban_dismiss(message: discord.Message, view: ui.View):
    await message.edit(content=message.content, embeds=message.embeds, view=view)
