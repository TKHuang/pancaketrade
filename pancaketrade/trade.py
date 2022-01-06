import logging
import sys

import click
from loguru import logger

import pancaketrade.commands
from pancaketrade.bot import TradeBot
from pancaketrade.utils.config import read_config
from pancaketrade.utils.generic import InterceptHandler
from pancaketrade.commands.scientist import Scientist
from pancaketrade.commands.plugin import NubiaExamplePlugin
from nubia import Nubia, context, Options

logger.remove()
logger.add(
    sys.stderr,
    format="<d>{time:YYYY-MM-DD HH:mm:ss}</>"
    "<lvl>{level: ^8}</>|<lvl><n>{message}</n></lvl>",
    level='INFO',
    backtrace=False,
    diagnose=False,
    colorize=True,
)
logging.getLogger("apscheduler.executors.default").setLevel("WARNING")
logging.basicConfig(handlers=[InterceptHandler()], level=0)

# @click.command()
# @click.argument('config_file', required=False, default='user_data/config.yml')
# @click.option('--gui', required=False, default=False)
# def main(config_file: str, gui: bool) -> None:
#     try:
#         config = read_config(config_file)
#         if (gui):
#             window = Gui(config=config)
#             window.start()
#         else:
#             bot = TradeBot(config=config)
#             bot.start()
#     finally:
#         logger.info('Bye!')


def main() -> int:
    # config = read_config('user_data/config.yml')
    # st = Scientist(config)
    plugin = NubiaExamplePlugin()
    # ctx = context.get_context()
    # ctx.config = config
    # ctx.st = st
    shell = Nubia(
        name='Scientist',
        command_pkgs=pancaketrade.commands,
        plugin=plugin,
        options=Options(persistent_history=False,
                        auto_execute_single_suggestions=False),
    )
    return shell.run()


if __name__ == '__main__':
    sys.exit(main())