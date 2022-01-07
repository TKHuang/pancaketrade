import time
import asyncio
import sys

import questionary
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from questionary.prompts.select import select
from termcolor import cprint

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from web3 import Web3
from nubia import context, command

from pancaketrade.commands import (AddToken)
from pancaketrade.network import Network
from pancaketrade.persistence import db
from pancaketrade.utils.config import Config, read_config
from pancaketrade.utils.db import get_token_watchers, init_db
from pancaketrade.watchers import OrderWatcher, TokenWatcher
from pancaketrade.utils.generic import format_token_amount, start_in_thread, format_token_amount
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
        self.status_scheduler = BackgroundScheduler(job_defaults={
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 20,
        })
        self.start_status_update()
        self.last_status_message_id: Optional[int] = None

    def _get_actions(self):
        actions = {
            self.events.ADD_TOKEN: AddToken(self, self.config),
        }
        return actions

    def start_status_update(self):
        if not self.config.update_messages:
            return
        trigger = IntervalTrigger(seconds=30)
        self.status_scheduler.add_job(self.update_status, trigger=trigger)
        self.status_scheduler.start()

    def pause_status_update(self, pause: bool = True):
        for job in self.status_scheduler.get_jobs():
            # prevent running an update while we are changing the last message id
            if pause:
                job.pause()
            else:
                job.resume()

    def update_status(self):
        if self.last_status_message_id is None:
            return  # we probably did not call status since start
        sorted_tokens = sorted(self.watchers.values(),
                               key=lambda token: token.symbol.lower())
        balances: List[Decimal] = []
        for token in sorted_tokens:
            if token.last_status_message_id is None:
                continue
            status, balance_bnb = self.get_token_status(token)
            balances.append(balance_bnb)
            # try:
            #     self.dispatcher.bot.edit_message_text(
            #         status,
            #         chat_id=self.config.secrets.admin_chat_id,
            #         message_id=token.last_status_message_id,
            #     )
            # except Exception as e:  # for example message content was not changed
            #     if not str(e).startswith('Message is not modified'):
            #         logger.error(f'Exception during message update: {e}')
            #         self.dispatcher.bot.send_message(
            #             chat_id=self.config.secrets.admin_chat_id,
            #             text=f'Exception during message update: {e}')
        message = self.get_summary_message(balances)
        cprint(message, 'purple')

    def get_token_status(self, token: TokenWatcher) -> Tuple[str, Decimal]:
        token_price, base_token_address = self.net.get_token_price(
            token_address=token.address)
        chart_links = [
            f'<a href="https://poocoin.app/tokens/{token.address}">Poocoin</a>',
            f'<a href="https://charts.bogged.finance/?token={token.address}">Bogged</a>',
            f'<a href="https://dex.guru/token/{token.address}-bsc">Dex.Guru</a>',
        ]
        token_lp = self.net.find_lp_address(
            token_address=token.address, base_token_address=base_token_address)
        if token_lp:
            chart_links.append(
                f'<a href="https://www.dextools.io/app/pancakeswap/pair-explorer/{token_lp}">Dext</a>'
            )
        chart_links.append(
            f'<a href="https://bscscan.com/token/{token.address}?a={self.net.wallet}">BscScan</a>'
        )
        token_price_usd = self.net.get_token_price_usd(
            token_address=token.address, token_price=token_price)
        token_balance = self.net.get_token_balance(token_address=token.address)
        token_balance_bnb = self.net.get_token_balance_bnb(
            token_address=token.address,
            balance=token_balance,
            token_price=token_price)
        token_balance_usd = self.net.get_token_balance_usd(
            token_address=token.address, balance_bnb=token_balance_bnb)
        effective_buy_price = ''
        if token.effective_buy_price:
            price_diff_percent = ((token_price / token.effective_buy_price) -
                                  Decimal(1)) * Decimal(100)
            diff_icon = '🆙' if price_diff_percent >= 0 else '🔽'
            effective_buy_price = (
                f'<b>At buy (after tax)</b>: <code>{token.effective_buy_price:.3g}</code> BNB/token '
                + f'(now {price_diff_percent:+.1f}% {diff_icon})\n')
        orders_sorted = sorted(
            token.orders,
            key=lambda o: o.limit_price if o.limit_price else Decimal(1e12),
            reverse=True
        )  # if no limit price (market price) display first (big artificial value)
        orders = [str(order) for order in orders_sorted]
        message = (
            f'<b>{token.name}</b>: {format_token_amount(token_balance)}\n' +
            f'<b>Links</b>: {"    ".join(chart_links)}\n' +
            f'<b>Value</b>: <code>{token_balance_bnb:.3g}</code> BNB (${token_balance_usd:.2f})\n'
            +
            f'<b>Price</b>: <code>{token_price:.3g}</code> BNB/token (${token_price_usd:.3g})\n'
            + effective_buy_price +
            '<b>Orders</b>: (underlined = tracking trailing stop loss)\n' +
            '\n'.join(orders))
        return message, token_balance_bnb

    def get_summary_message(self, token_balances: List[Decimal]) -> str:
        balance_bnb = self.net.get_bnb_balance()
        price_bnb = self.net.get_bnb_price()
        total_positions = sum(token_balances)
        grand_total = balance_bnb + total_positions
        msg = (
            f'BNB balance: {balance_bnb:.4f} BNB (${balance_bnb * price_bnb:.2f})\n'
            f'Tokens balance: {total_positions:.4f} BNB (${total_positions * price_bnb:.2f})\n'
            f'Total: {grand_total:.4f} BNB (${grand_total * price_bnb:.2f}) '
            f'https://bscscan.com/address/{self.net.wallet}">\n'
            f'BNB price: ${price_bnb:.2f}\n')
        return msg

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
async def addtoken_address(address: str, slippage: str, icon: str = ''):
    "Add a token"
    ctx = context.get_context()
    st = ctx.st
    action = st.actions[Events.ADD_TOKEN]
    await action.handler(address, slippage, icon)


@command
def status():
    "List all tokens registered"
    st = context.get_context().st
    st.pause_status_update(True)
    sorted_tokens = sorted(st.watchers.values(),
                           key=lambda token: token.symbol.lower())
    balances: List[Decimal] = []
    for token in sorted_tokens:
        status, balance_bnb = st.get_token_status(token)
        balances.append(balance_bnb)
        cprint(f'{token.name} {token.address}: {balance_bnb}', "yellow")
    message = st.get_summary_message(balances)
    cprint(message, 'red')
    st.pause_status_update(False)


@command
async def approve():
    "Approve pancakeswap to transfer your token."
    st = context.get_context().st
    sorted_tokens = sorted(st.watchers.values(),
                           key=lambda token: token.symbol.lower())
    tokens = [f'{token.symbol}:{token.address}' for token in sorted_tokens]
    question = questionary.select('Which token to approve?', choices=tokens)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        choice = question.ask()
    else:
        choice = await loop.run_in_executor(None, question.ask)

    token_address = choice.split(':')[1].strip()
    if not Web3.isChecksumAddress(token_address):
        cprint('⛔️ Invalid token address.')
        return

    token = st.watchers[token_address]
    if token.net.is_approved(token.address):
        cprint(f'{token.symbol} is already approved on PancakeSwap.')
        return

    cprint(f'Approving {token.symbol} for trading on PancakeSwap...')
    approved = token.approve()
    if approved:
        cprint('✅ Approval successful on PancakeSwap!')
    else:
        cprint('⛔ Approval failed')