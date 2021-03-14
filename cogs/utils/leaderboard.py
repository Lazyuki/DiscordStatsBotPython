import asyncio
import discord

class PaginatedLeaderboard:
    def __init__(self, ctx, *, 
        records=[],
        title='Leaderboard',
        description='For the last 30 days (UTC)',
        rank_for='user_id',
        find_record=None,
        field_name_resolver=None,
        record_to_rank=lambda r: r['rank'],
        record_to_count=lambda r: r['count'],
        count_to_string=lambda x: x,
        per_page=25):

        self.ctx = ctx             
        self.bot = ctx.bot
        self.records = records
        self.rank_for = rank_for
        self.find_record = find_record
        self.name_resolver = field_name_resolver or self.user_resolver
        self.record_to_rank = record_to_rank
        self.record_to_count = record_to_count
        self.count_to_string = count_to_string
        self.message = ctx.message
        self.author = ctx.author
        self.per_page = per_page
        total, left_over = divmod(len(self.records), per_page)
        if left_over:
            total += 1

        self.total_pages = total
        self.current_page = None
        if find_record and 'rank' in find_record:
            self.find_record_page = self.record_to_rank(find_record) // per_page
        else:
            self.find_record_page = None

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

    def user_resolver(self, rank, user_id, record):
        user = self.bot.get_user(user_id)
        is_user = '\N{ROUND PUSHPIN}' if user_id == self.author.id else ''
        if user is None:
            name = f'{rank}) @user-left({user_id})'
        else:
            name = f'{is_user}{rank}) {user.name}'
        return name
    
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
            record_value = record[self.rank_for]
            rank = self.record_to_rank(record)
            name = self.name_resolver(rank, record_value, record)
            embed.add_field(name=name, value=self.count_to_string(self.record_to_count(record)))

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
        if self.find_record_page is not None:
            await self.show_page(self.find_record_page)

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
            if self.find_record_page is not None:
                await self.message.add_reaction(self.reaction_emojis[4][0])

        while self.paginating:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=self.react_check, timeout=20.0)
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