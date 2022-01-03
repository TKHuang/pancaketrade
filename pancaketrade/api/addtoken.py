from typing import NamedTuple, Dict
from decimal import Decimal

from pancaketrade.network import Network
from pancaketrade.persistence import Token, db
from pancaketrade.utils.config import Config
from pancaketrade.utils.db import token_exists
from pancaketrade.utils.generic import format_token_amount
from pancaketrade.watchers import TokenWatcher
from web3 import Web3
from web3.exceptions import ABIFunctionNotFound, ContractLogicError


class AddTokenResponses(NamedTuple):
    ADDRESS: int = 0
    EMOJI: int = 1
    SLIPPAGE: int = 2


class AddToken:
    def __init__(self, parent, config: Config):
        self.parent = parent
        self.net: Network = parent.net
        self.config = config

    def handler(self, address: str, slippage: str, icon: str):
        add = self.addtoken_address(address)
        add = self.addtoken_icon(add, icon)
        self.addtoken_slippage(add, slippage)

    def addtoken_icon(self, add: Dict[str, str], icon: str):
        add['icon'] = icon.strip()
        return add

    def addtoken_address(self, token_address: str):
        if Web3.isAddress(token_address):
            token_address = Web3.toChecksumAddress(token_address)
        else:
            raise Exception(
                '⚠️ The address you provided is not a valid ETH address.'
                ' Try again.')
        add = dict(address=token_address)
        try:
            add['decimals'] = self.net.get_token_decimals(token_address)
            add['symbol'] = self.net.get_token_symbol(token_address)
        except (ABIFunctionNotFound, ContractLogicError):
            raise Exception(
                '⛔ Wrong ABI for this address.\n' +
                'Check that address is a contract at ' +
                f'<a href="https://bscscan.com/address/{token_address}">'
                'BscScan</a> and try again.', )

        if token_exists(address=token_address):
            raise Exception(f'⚠️ Token {add["symbol"]} already exists.')

        return add

    def addtoken_slippage(self, add: Dict[str, str], slippage: str):
        try:
            slippage = Decimal(slippage.strip())
        except Exception:
            raise Exception(
                '⚠️ This is not a valid slippage value. '
                'Please enter a decimal number for percentage. Try again.')

        if slippage < Decimal("0.01") or slippage > 100:
            raise Exception('⚠️ This is not a valid slippage value. '
                            'Please enter a number between 0.01 and 100 for '
                            'percentage. Try again.')
        add['default_slippage'] = f'{slippage:.2f}'
        emoji = add['icon'] + ' ' if add['icon'] else ''

        print(f'Alright, the token {emoji}{add["symbol"]} '
              f'will use {add["default_slippage"]}% slippage by default.')
        try:
            db.connect()
            with db.atomic():
                token_record = Token.create(**add)
        except Exception as e:
            raise Exception(f'⛔ Failed to create database record: {e}')
        finally:
            db.close()
        token = TokenWatcher(token_record=token_record,
                             net=self.net,
                             config=self.config)
        self.parent.watchers[token.address] = token
        balance = self.net.get_token_balance(token_address=token.address)
        balance_usd = self.net.get_token_balance_usd(
            token_address=token.address, balance=balance)
        if not self.net.is_approved(token_address=token.address):
            yes = sg.popup_yes_no('Approve pancakeswap for selling')
            if yes:
                approved = token.approve()
                if approved:
                    print(f'{token.name} Approval successful on PancakeSwap!')
                else:
                    raise Exception(f'{token.name} Approval failed')

        print(f'{token.name} Token was added successfully. '
              f'Balance is {format_token_amount(balance)} {token.symbol}'
              f' (${balance_usd:.2f}).')
