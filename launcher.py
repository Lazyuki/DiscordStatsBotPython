import asyncio
import asyncpg
import logging
import contextlib
import uvloop
import sys

from bot import Cirilla, initial_extensions
import config

# Faster asyncio
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

@contextlib.contextmanager
def setup_logging():
    try:
        # __enter__
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)

        log = logging.getLogger()
        log.setLevel(logging.INFO)
        if config.debugging:
            handler = logging.StreamHandler(sys.stdout)
        else:
            handler = logging.FileHandler(filename='cirilla.log', encoding='utf-8', mode='w')
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter('[{asctime}] [{levelname:<7}] {name}: {message}', dt_fmt, style='{')
        handler.setFormatter(fmt)
        log.addHandler(handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            log.removeHandler(hdlr)

def run_bot():
    loop = asyncio.get_event_loop()
    log = logging.getLogger()

    try:
        pool = loop.run_until_complete(asyncpg.create_pool(**config.db,  command_timeout=60))
    except Exception:
        log.exception('Could not set up PostgreSQL. Exiting.')
        return

    bot = Cirilla(pool)
    bot.run(config.token)
    print('Bot finished running')

def main():
    with open('cirilla_errors.log', 'w') as f:
        with contextlib.redirect_stderr(f):
            with setup_logging():
                run_bot()

if __name__ == '__main__':
    main()