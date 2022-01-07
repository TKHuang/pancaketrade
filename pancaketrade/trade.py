import sys

from loguru import logger

import pancaketrade.commands
from plugin import NubiaExamplePlugin
from nubia import Nubia, Options
from pancaketrade.utils.config import read_config

# logger.remove()
# logger.add(
#     sys.stderr,
#     format="<d>{time:YYYY-MM-DD HH:mm:ss}</>"
#     "<lvl>{level: ^8}</>|<lvl><n>{message}</n></lvl>",
#     level='INFO',
#     backtrace=False,
#     diagnose=False,
#     colorize=True,
# )
# logging.getLogger("apscheduler.executors.default").setLevel("WARNING")
# logging.basicConfig(handlers=[InterceptHandler()], level=0)

# def main() -> int:
# config = read_config('user_data/config.yml')
# st = Scientist(config)
# ctx = context.get_context()
# ctx.config = config
# ctx.st = st

if __name__ == '__main__':
    config = read_config('user_data/config.yml')
    plugin = NubiaExamplePlugin(config)
    shell = Nubia(
        name='Scientist',
        command_pkgs=pancaketrade.commands,
        plugin=plugin,
        options=Options(persistent_history=False,
                        auto_execute_single_suggestions=False),
    )
    sys.exit(shell.run())