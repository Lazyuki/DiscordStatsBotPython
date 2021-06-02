from discord.ext import commands
from datetime import datetime
import discord
import logging
import asyncio 
import re

log = logging.getLogger(__name__)

BOOSTER_COLOR = 0xf47fff

async def has_manage_guild(ctx):
    return ctx.author.guild_permissions.manage_guild

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings

    @commands.command()
    async def boosters(self, ctx):
        """Show Nitro Boosters"""
        embed = discord.Embed(colour=BOOSTER_COLOR)
        embed.title = f'Nitro Boosters: {len(ctx.guild.premium_subscribers)} members'
        embed.description = '\n'.join([f'**{sub}** - ' + sub.premium_since.strftime('%Y/%m/%d') for sub in sorted(ctx.guild.premium_subscribers, key=lambda m: m.premium_since)])
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'Nitro Boosts: {ctx.guild.premium_subscription_count} (Tier {ctx.guild.premium_tier})')
        await ctx.send(embed=embed)

    @commands.group(name='bookmark', aliases=['bm'], invoke_without_command=True)
    async def bookmark(self, ctx):
        """
        React with the bookmark emoji to send a copy of the reacted message into your DM
        You must enable "Allow direct messages from server members" for this server in Privacy Settings.
        """
        bookmark_emoji = self.settings[ctx.guild.id].bookmark_emoji
        await ctx.send(f'''
        React with {bookmark_emoji} to any message to send a copy into your DM.
You must enable `Allow direct messages from server members` for this server in Privacy Settings. 
        ''')

    @bookmark.command(name='set')
    @commands.check(has_manage_guild)
    async def bookmark_set(self, ctx, *, emoji: discord.Emoji):
        """
        React with the bookmark emoji to send any message into your DM
        ,bookmark set <emoji> to change emoji
        """
        self.settings.update_settings(ctx.guild, bookmark_emoji=str(emoji))
        await ctx.send(f'\N{WHITE HEAVY CHECK MARK} Bookmark emoji has been set to {emoji}')

    @commands.command(aliases=['vp'])
    async def voiceping(self, ctx, *, message=''):
        """
        Ping everyone in your VC room
        """
        voice = ctx.author.voice
        if not voice or not voice.channel:
            await ctx.send("You need to be in VC to do this")
            return
        s = f'{ctx.author.mention} pinged #{voice.channel.name}\n'
        members = [m.mention for m in voice.channel.members if m != ctx.author]
        if len(members) == 0:
            ctx.send('Nobody else seems to be in your VC')
            return
        s += ' '.join(members)
        await ctx.send(s)

    @commands.command()
    async def poll(self, ctx, *, arg = None):
        """
        Adds poll reactions
        Usage: 
        `,,poll` will add reactions to the message above the command that invoked this.
        `,,poll 1233345555567` to specify a message with an ID
        `,,poll Should I sleep?` will start a new poll with the message
        """
        if arg:
            if re.match(r'^[0-9]{17,22}$', arg):
                message = await ctx.fetch_message(arg)
            else:
                message = await ctx.send(arg)
        else:
            message = await ctx.history(limit=2).find(lambda m: m.id != ctx.message.id)

        await ctx.message.delete()
        if not message:
            await ctx.send('Failed to find the message')
            return
        await message.add_reaction(f'\N{THUMBS UP SIGN}') 
        await message.add_reaction(f'\N{THUMBS DOWN SIGN}') 
        await message.add_reaction(f'\N{NEGATIVE SQUARED AB}') 


    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        """Notify ban"""
        # Fetch audit log to get who banned them
        banner = None
        reason = None
        await asyncio.sleep(1)
        log.info(f'Member banned {user.name}')
        async for entry in guild.audit_logs(action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                banner = entry.user
                reason = entry.reason
                break
        log.info(f'Banned by {banner.name if banner else "Unknown"}')
        embed = discord.Embed(colour=0x000000)
        embed.description = f'\N{CROSS MARK} **{user.name}#{user.discriminator}** was `banned`. ({user.id})\n\n*by* {banner.mention if banner else "Unknown"}\n**Reason:** {reason if reason else "Unknown"}'
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'User Banned', icon_url=user.avatar_url_as(static_format='png'))
        chan = guild.get_channel(self.settings[guild.id].log_channel_id)
        if chan:
            await chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        """Notify unban"""
        # Fetch audit log to get who banned them
        banner = None
        await asyncio.sleep(1)
        async for entry in guild.audit_logs(action=discord.AuditLogAction.unban):
            if entry.target.id == user.id:
                banner = entry.user
                break
        unbanner = banner.name if banner else "Unknown"
        embed = discord.Embed(colour=0xeeeeee)
        embed.description = f'\N{WHITE EXCLAMATION MARK ORNAMENT} **{user.name}#{user.discriminator}** was `unbanned`. ({user.id})\n\n*by* {banner.mention if banner else "Unknown"}'
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'User Unbanned by {unbanner}', icon_url=user.avatar_url_as(static_format='png'))
        chan = guild.get_channel(self.settings[guild.id].log_channel_id)
        if chan:
            await chan.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Notify kick"""
        # Fetch audit log to get who banned them
        kicker = None
        reason = None
        guild = member.guild
        await asyncio.sleep(1)
        now = datetime.now()
        async for entry in guild.audit_logs(action=discord.AuditLogAction.kick):
            if entry.target.id == member.id and (now - entry.created_at).total_seconds() < 10:
                kicker = entry.user
                reason = entry.reason
                break
        else:
            return
        log.info(f'Kicked by {kicker.name if kicker else "Unknown"}')
        embed = discord.Embed(colour=0x000000)
        embed.description = f'\N{CROSS MARK} **{member.name}#{member.discriminator}** was `kicked`. ({member.id})\n\n*by* {kicker.mention if kicker else "Unknown"}\n**Reason:** {reason if reason else "Unknown"}'
        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f'User Kicked', icon_url=member.avatar_url_as(static_format='png'))
        chan = guild.get_channel(self.settings[guild.id].log_channel_id)
        if chan:
            await chan.send(embed=embed)

    async def handle_reaction(self, reaction, user):
        if user.id == self.bot.user.id:
            return
        
        if reaction.message.guild:
            # Is a guild event
            if str(reaction.emoji) == self.settings[reaction.message.guild.id].bookmark_emoji:
                message = reaction.message

                too_long = len(message.content) > 2048
                shortened_content = message.content[:2040] + ' (...)' if too_long else message.content

                embed = discord.Embed(colour=0x03befc)
                embed.description = shortened_content or '*Empty*'
                embed.add_field(name=f'--------------', value=f'([Go to message]({message.jump_url}))', inline=True)
                embed.set_author(name=message.author.name, icon_url=message.author.avatar_url_as(static_format='png'))
                embed.set_footer(text=f'#{message.channel.name}\nReact with \N{CROSS MARK} to delete this bookmark')
                try:
                    await user.send(embed=embed)
                    if too_long:
                        embed_cont = embed.copy()
                        embed_cont.description = message.content[2040:]
                        embed_cont.title = '(continued)'
                        await user.send(embed=embed_cont)

                except:
                    log.info(f'{user} tried to bookmark but could not send the message')
        else:
            if str(reaction.emoji) == '\N{CROSS MARK}':
                message = await user.fetch_message(reaction.message.id)
                await message.delete()
            return

    async def handle_raw_reaction(self, payload, is_add):
        message_id = payload.message_id
        user_id = payload.user_id
        channel_id = payload.channel_id
        guild_id = payload.guild_id
        emoji = payload.emoji

        if user_id == self.bot.user.id:
            return

        cached = discord.utils.find(lambda m: m.id == message_id, self.bot.cached_messages)
        if cached:
            return

        if not guild_id:
            # Inside DM
            if str(emoji) == '\N{CROSS MARK}':
                user = await self.bot.fetch_user(user_id)
                message = await user.fetch_message(message_id)
                await message.delete()
            return
             
        
        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id)
        member = guild.get_member(user_id)
        message = await channel.fetch_message(message_id)

        if is_add:
            reaction = discord.utils.find(lambda r: str(r.emoji) == str(emoji), message.reactions)
            if not reaction:
                return
            await self.handle_reaction(reaction, member)
        else:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.handle_raw_reaction(payload, True)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        await self.handle_reaction(reaction, user)

def setup(bot):
    bot.add_cog(Utilities(bot))