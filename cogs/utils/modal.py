from typing import List, Optional
from discord import ui
import discord
import asyncio
from .resolver import has_any_role


class Questionnaire(ui.Modal):
    name = ui.TextInput(label="Name")
    answer = ui.TextInput(
        label="What do you think about EJLX?", style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Thanks for your response, {self.name}!", ephemeral=True
        )
        if interaction.channel and isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send(
                f"{self.name if self.name else 'Annonymous User'} answered:\n{self.answer if self.answer else 'No response'}"
            )


class ButtonView(ui.View):
    def __init__(self, *, modal: ui.Modal):
        super().__init__()
        self.timeout = 300.0
        self.modal = modal

    @ui.button(label="Answer Questionnaire", style=discord.ButtonStyle.primary)
    async def open_modal(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(self.modal)


async def send_modal(
    channel: discord.TextChannel | discord.Thread,
    content: str = "",
):
    modal = Questionnaire(title="EJLX Questionnaire", timeout=300.0)
    view = ButtonView(modal=modal)
    message = await channel.send(content=content, view=view)
    timed_out = await view.wait()
    if timed_out:
        await message.edit(content="timed out")
