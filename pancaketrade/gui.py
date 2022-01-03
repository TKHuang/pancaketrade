"""Gui class."""
import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from web3 import Web3

from pancaketrade.api import (AddToken)

from pancaketrade.network import Network
from pancaketrade.persistence import db
from pancaketrade.utils.config import Config
from pancaketrade.utils.db import get_token_watchers, init_db
from pancaketrade.watchers import OrderWatcher, TokenWatcher
from pancaketrade.utils.generic import start_in_thread


@dataclass
class Events:
    """GUI events."""
    ADD_TOKEN: str = 'Add Token'


class Gui:

    def __init__(self, config: Config):
        self.config = config
        self.db = db
        init_db()
        self.net = Network(
            rpc=self.config.bsc_rpc,
            wallet=self.config.wallet,
            min_pool_size_bnb=self.config.min_pool_size_bnb,
            secrets=self.config.secrets,
        )
        self.watchers: Dict[str, TokenWatcher] = get_token_watchers(
            net=self.net, config=self.config)
        self.events = Events()
        self.actions = self._get_actions()

    def _get_actions(self):
        actions = {
            self.events.ADD_TOKEN: AddToken(self, self.config),
        }
        return actions

    def event_handler(self, event, *args, **kwargs):
        if event == self.events.ADD_TOKEN:
            address = args[0]
            slippage = args[1]
            try:
                icon = args[2]
            except IndexError:
                icon = ''

            try:
                self.actions[self.events.ADD_TOKEN].handler(
                    address, slippage, icon)
            except Exception as e:
                print(f'Add token {address} failed:\n {e}')
                return str(e)
