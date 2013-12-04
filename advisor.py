#!/bin/python
#encoding: utf-8

import time
import datetime
import multiprocessing as mp
import logging

from info import *
import config
import models
from wallet import Wallet
import exchanges


def _polled_request_account_info(k):
    try:
        _logger = logging.getLogger(__name__)
        _logger.debug('Requesting exchange info...' + k)
        ai = Advisor._exchanges[k].request_info()
        _logger.debug(k + ' finished')
        return ai
    except IOError as e:
        _logger.error(e)
        return None

class Advisor:
    _exchanges = exchanges.actived_exchanges

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self.wallet = Wallet()
        self._pool = mp.Pool(2)
        self.qty_per_order = config.configuration['qty_per_order']

    def close(self):
        self._pool.close()
        self._pool.join()
        self._pool = None

    def request_accounts_info(self):
        self._logger.info('Requesting all accounts info...')
        accounts = self._pool.map(_polled_request_account_info, Advisor._exchanges)        
        #accounts = map(_polled_request_account_info, Advisor._exchanges)        
        for a in accounts:
            if a == None:
                self._logger.info('ERROR: Failed to request account info')
                raise RuntimeError('Failed to request account info')
        #accounts = map(_polled_request_account_info, Advisor._exchanges)        
        self._logger.info('All Accounts info accquired')
        self._logger.debug('ACCOUNT INFO:')
        for a in accounts:
            self._logger.debug('\texchange={0}\tBTC_balance={1}\tmoney_balance={2}\tbuy={3}'.format(
                    a.name, round(a.stock_balance, 4), round(a.money_balance, 2), round(a.ticker.buy_price, 2)))
        return accounts

    def _record_trade_lead(self, buy_exchange, buy_price, sell_exchange, sell_price):
        session = models.Session()
        try:
            tl = models.TradeLead(buy_exchange, buy_price, sell_exchange, sell_price)
            session.add(tl)
            session.commit()
        except Exception as e:
            self._logger.error(e)
            session.rollback()

    def evaluate(self, accounts):
        try:
            return self._do_evaluate(accounts)
        except IOError as e:
            self._logger.error('Network Error')
            self._logger.error(e)
            return None
        except Exception as e:
            self._logger.error(e)
            return None

    def _do_evaluate(self, accounts):
        #计算价格
        accounts = sorted(accounts, key=lambda e:e.ticker.buy_price)
        buy_account = accounts[0]
        sell_account = accounts[len(accounts) - 1]
        buy_price_rate = 1.001
        sell_price_rate = 0.999
        buy_price = round(buy_account.ticker.buy_price * buy_price_rate, 2)
        sell_price = round(sell_account.ticker.buy_price * sell_price_rate, 2)
        buy_amount = buy_price * self.qty_per_order
        sell_amount = round(sell_price * self.qty_per_order, 2)
        wallet_transfer_fee_amount = round(buy_price * self.wallet.transfer_fee + buy_price * 0.0001, 2)
        trade_fee_amount = round(buy_amount * buy_account.trade_fee + sell_amount * sell_account.trade_fee, 2)
        gross_profit = round(sell_amount - buy_amount, 2)
        net_profit = round(sell_amount - buy_amount - wallet_transfer_fee_amount - trade_fee_amount, 2)
        profit_rate = net_profit / buy_amount
        threshold = config.configuration['profit_rate_threshold']
        self._logger.debug('threshold_rate={0}%\tgross_profit={1}\t\tnet_profit={2}\tprofit_rate={3}%'.format(
                round(threshold * 100, 4), gross_profit, net_profit, round(profit_rate * 100, 4)))
        self._logger.debug('\tbuy_price={0}\tbuy_amount={1}\tsell_price={2}\tsell_amount={3}'.format(buy_price, buy_amount, sell_price, sell_amount))
        self._logger.debug('\twallet_fee={0}\ttrade_fee={1}'.format(wallet_transfer_fee_amount, trade_fee_amount))
        is_balance_ok = buy_account.money_balance > buy_amount and sell_account.stock_balance > sef.qty_per_order
        if not is_balance_ok:
            self._logger.warn(u'帐号余额不足')
        can_go = is_balance_ok and profit_rate > threshold and net_profit > 0.01 #and net_profit < 0.05
        if can_go:
            self._record_trade_lead(
                    buy_account.name, buy_account.ticker.buy_price, 
                    sell_account.name, sell_account.ticker.sell_price)

        s = Suggestion(can_go, buy_account, sell_account, buy_price, sell_price, self.qty_per_order)
        if s.can_go:
            self._logger.info('I FOUND A CHANCE AND I WILL TRADE IT NOW!!!')
        return s 
