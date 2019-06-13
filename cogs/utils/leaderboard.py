import asyncio
import discord

class PaginatedLeaderboard:
    def __init__(self, ctx, *, 
        records=[],
        title='Leaderboard',
        description='For the last 30 days (UTC)',
        user_record=None,
        count_to_string=lambda x: x,
        per_page=25):

        self.ctx = ctx             
        self.bot = ctx.bot
        self.records = records
        self.user_record = user_record
        self.count_to_string = count_to_string
        self.message = ctx.message
        self.author = ctx.author
        self.per_page = per_page
        total, left_over = divmod(len(self.records), per_page)
        if left_over:
            total += 1

        self.total_pages = total
        self.current_page = None
        if user_record and 'rank' in user_record:
            self.user_record_page = user_record['rank'] // per_page
        else:
            self.user_record_page = None

        self.title = title
        self.description = description

        self.paginating = len(records) > per_page
        self.reaction_emojis = [
            ('\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}', self.first_page),
            ('\N{BLACK LEFT-POINTING TRIANGLE}', self.previous_page),
            ('\N{BLACK RIGHT-POINTING TRIANGLE}', self.next_page),
            ('\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}', self.last_page),
            ('\N{ROUND PUSHPIN}', self.user_page)
        ]

        self.message = None
    
    async def show_page(self, page):
        if page < 0 or page == self.total_pages or page == self.current_page:
            return
        self.current_page = page
        start = page * self.per_page
        end = start + self.per_page
        embed = discord.Embed(colour=0x3A8EDB)
        embed.title = self.title
        embed.description = self.description

        for record in self.records[start:end]:
            ru_id = record['user_id']
            rank = record['rank']
            ru = self.bot.get_user(ru_id)
            is_user = '\N{ROUND PUSHPIN}' if ru_id == self.author.id else ''
            if ru is None:
                name = f'{rank}) @deleted-user({ru_id})'
            else:
                name = f'{is_user}{rank}) {ru.name}'
            embed.add_field(name=name, value=self.count_to_string(record['count']))

        if self.user_record and self.user_record['user_id'] is not None:
            user_id = self.user_record['user_id']
            user = self.bot.get_user(user_id)
            if user is None:
                username = f'@deleted-user({user_id})'
            else:
                username = user.name
            embed.set_footer(text=f'Page: {page + 1}/{self.total_pages}')
        if self.message is not None:
            await self.message.edit(embed=embed)
        else:
            self.message = await self.ctx.send(embed=embed)

    async def first_page(self):
        await self.show_page(0)

    async def last_page(self):
        await self.show_page(self.total_pages - 1)

    async def next_page(self):
        await self.show_page(self.current_page + 1)

    async def previous_page(self):
        await self.show_page(self.current_page - 1)

    async def user_page(self):
        if self.user_record_page is not None:
            await self.show_page(self.user_record_page)

    def react_check(self, reaction, user):
        if user is None or user.id != self.author.id:
            return False

        if reaction.message.id != self.message.id:
            return False

        for (emoji, func) in self.reaction_emojis:
            if reaction.emoji == emoji:
                self.match = func
                return True
        return False
    
    async def build(self):
        await self.first_page()
        if self.paginating:
            await self.message.add_reaction(self.reaction_emojis[0][0])
            await self.message.add_reaction(self.reaction_emojis[1][0])
            await self.message.add_reaction(self.reaction_emojis[2][0])
            await self.message.add_reaction(self.reaction_emojis[3][0])
            if self.user_record_page is not None:
                await self.message.add_reaction(self.reaction_emojis[4][0])

        while self.paginating:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=self.react_check, timeout=30.0)
            except asyncio.TimeoutError:
                self.paginating = False
                try:
                    await self.message.clear_reactions()
                except:
                    pass
                finally:
                    break
            try:
                await self.message.remove_reaction(reaction, user)
            except:
                pass # can't remove it so don't bother doing so
            await self.match()