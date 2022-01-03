import logging
import sys

import click
import zerorpc
from loguru import logger

from pancaketrade.utils.config import read_config
from pancaketrade.utils.generic import InterceptHandler
from pancaketrade.gui import Gui

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


@click.command()
@click.argument('config_file', required=False, default='user_data/config.yml')
def main(config_file: str) -> None:
    try:
        print('sssssss')
        config = read_config(config_file)
        s = zerorpc.Server(Gui(config=config))
        s.bind('tcp://0.0.0.0:4242')
        s.run()
    finally:
        logger.info('Bye!')


if __name__ == '__main__':
    main()
