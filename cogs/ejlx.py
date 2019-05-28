from discord.ext import commands
import discord

JHO = 189571157446492161
EWBF = 277384105245802497
LANG_ROLES = {
  196765998706196480: {
    'name': 'Native Japanese',
    'short': ['nj', 'jp']
  },
  270391106955509770: {
    'name': 'Fluent Japanese',
    'short': ['fj']
  },
  197100137665921024: {
    'name': 'Native English',
    'short': ['ne', 'en']
  },
  241997079168155649: {
    'name': 'Fluent English',
    'short': ['fe']
  },
  248982130246418433: {
    'name': 'Other Language',
    'short': ['ol']
  },
  249695630606336000: {
    'name': 'New User',
    'short': ['nu']
  },
}

class EJLX(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.newbies = []
  
  @commands.command()
  async def tag(self, ctx, *, member: discord.Member = None):
    member = member or self.newbies[-1]
    pass

  @commands.Cog.listener()
  async def on_member_join(self, member):
    self.newbies.append(member.id)
    if len(self.newbies) > 3:
      self.newbies.pop(0)
    