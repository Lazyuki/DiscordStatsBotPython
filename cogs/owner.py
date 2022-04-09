from discord.ext import commands
import discord
import logging
import asyncio
import asyncpg
import subprocess
import textwrap
import traceback
import re
import io
from contextlib import redirect_stdout
from cogs.utils.ui import BanDismissView, add_ban_dismiss


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = bot.settings
        self.pool = bot.pool
        self.config = bot.config

    # This cog is bot owner only
    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    @commands.command()
    async def kill(self, ctx):
        await ctx.send("See you space cowboy...")
        await self.bot.close()

    @commands.command(aliases=["rl", "rc"])
    async def reload(self, ctx, *, module):
        try:
            await self.bot.reload_extension(f"cogs.{module}")
        except commands.ExtensionError as e:
            await ctx.send(f"{e.__class__.__name__}: {e}")
        except Exception as e:
            await ctx.send(str(e))
        else:
            await ctx.send("\N{OK HAND SIGN}")

    @commands.command(aliases=["gpl"])
    async def git_pull(self, ctx):
        async with ctx.typing():
            stdout, _ = await self.run_process("git pull")
            await ctx.send(stdout)

    @commands.command(aliases=["db"])
    async def db_fetch(self, ctx, *, query):
        async with ctx.typing():
            res = await self.pool.fetch(query)
            if res:
                await ctx.send([tuple(r) for r in res])
            else:
                await ctx.send("No rows returned")

    @commands.command(aliases=["rs"])
    async def restart(self, ctx):
        await self._restart(ctx)

    async def _restart(self, ctx):
        await ctx.send("Restarting...")
        self.bot.config.debugging = True
        await asyncio.create_subprocess_shell(
            "(sleep 3 && . ~/.venv/bin/activate && nohup python3 launcher.py) &",
            close_fds=True,
        )
        await self.bot.close()

    @commands.command()
    async def update(self, ctx):
        async with ctx.typing():
            stdout, _ = await self.run_process("git pull")
            if "bot.py" in stdout or "cogs/utils" in stdout:
                await ctx.send("Restarting...")
                await self._restart(ctx)
            else:
                cogs = re.findall(r"cogs/(\w+?)\.py", stdout)
                if not cogs:
                    await ctx.send("Nothing to update")
                    return
                try:
                    for cog in cogs:
                        if cog == "utils":
                            continue
                        await self.bot.reload_extension(f"cogs.{cog}")
                except commands.ExtensionError as e:
                    await ctx.send(f"{e.__class__.__name__}: {e}")
                except Exception as e:
                    await ctx.send(str(e))
                else:
                    await ctx.send(
                        "\N{OK HAND SIGN} Updated cogs {}".format(", ".join(cogs))
                    )

    @commands.command(aliases=["log"])
    async def tail_log(self, ctx):
        async with ctx.typing():
            stdout, stderr = await self.run_process("tail -n 30 cirilla.log")
            await ctx.send("```" + stdout[-1994:] + "```")
            if stderr:
                await ctx.send("Error:\n" + stderr)

    @commands.command(aliases=["err"])
    async def tail_error(self, ctx):
        async with ctx.typing():
            stdout, stderr = await self.run_process("tail -n 50 cirilla_errors.log")
            if not stdout:
                stdout = "No errors"
            await ctx.send("```" + stdout[-1994:] + "```")
            if stderr:
                await ctx.send("Error:\n" + stderr)

    @commands.command(aliases=["sh"])
    async def shell(self, ctx, *, script):
        async with ctx.typing():
            stdout, stderr = await self.run_process(script)
            await ctx.send(stdout)
            if stderr:
                await ctx.send("Error:\n" + stderr)

    @commands.command(hidden=True, name="eval")
    async def _eval(self, ctx, *, body: str):
        """Evaluates a code"""

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction("\u2705")
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                await ctx.send(f"```py\n{value}{ret}\n```")

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return "\n".join(content.split("\n")[1:-1])

        # remove `foo`
        return content.strip("` \n")

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    @commands.command(aliases=["bt"])
    async def button_test(self, ctx, *, perm):
        embed = discord.Embed(colour=0xFF0000)
        embed.description = f"TEST"
        wp = perm == "wp"
        minimo = perm == "minimo"
        mods = perm == "mods"

        embed.set_footer(
            text=f"{'WP' if wp else 'MINIMO' if minimo else 'MOD'}s can ban or dismiss this message and unmute them."
        )
        prompt = await ctx.reply(
            f"test",
            embed=embed,
            mention_author=False,
        )
        view = BanDismissView(
            message=prompt,
            bannees=[ctx.author],
            reason="New user trying to ping everyone",
            wp=wp,
            minimo=minimo,
            unmute_dismissed=True,
        )
        await add_ban_dismiss(prompt, view)


async def setup(bot):
    await bot.add_cog(Owner(bot))
