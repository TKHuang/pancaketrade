"""Gui class."""
import time
import asyncio
import sys
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from web3 import Web3
from nubia import context, Nubia, command

from pancaketrade.commands import (AddToken)

from pancaketrade.network import Network
from pancaketrade.persistence import db
from pancaketrade.utils.config import Config, read_config
from pancaketrade.utils.db import get_token_watchers, init_db
from pancaketrade.watchers import OrderWatcher, TokenWatcher
from pancaketrade.utils.generic import start_in_thread
from pancaketrade.utils.config import read_config


@dataclass
class Events:
    """GUI events."""
    ADD_TOKEN: str = 'Add Token'


class Scientist:
    "Being a scientist!"

    def __init__(self, config: Config = 'user_data/config.yml'):
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

    # def event_handler(self, event, values):
    #     if event == self.events.ADD_TOKEN:
    #         address = values[f'{self.events.ADD_TOKEN}:address']
    #         slippage = values[f'{self.events.ADD_TOKEN}:slippage']
    #         icon = values[f'{self.events.ADD_TOKEN}:icon']
    #         try:
    #             self.actions[self.events.ADD_TOKEN].handler(
    #                 address, slippage, icon)
    #         except Exception as e:
    #             print(f'Add token {address} failed:\n {e}')


@command
def addtoken_address(address: str, slippage: str, icon: str = ''):
    "Add a token"
    ctx = context.get_context()
    st = ctx.st
    st.actions.handler(address, slippage, icon)
