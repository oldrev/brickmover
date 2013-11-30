#!/bin/python
#encoding: utf-8

import time
import datetime
import multiprocessing as mp

from info import *
from exchanges import BtcChinaExchange, OKCoinExchange
import config
import models
from wallet import Wallet

def _polled_request_account_info(k):
    try:
        print 'requesting exchange info...', k
        ai = Advisor._exchanges[k].request_info()
        print 'done'
        return ai
    except IOError as e:
        print e
        return None

class Advisor:
    _exchanges = {
            BtcChinaExchange.Name: BtcChinaExchange(),
            OKCoinExchange.Name: OKCoinExchange(),
    }

    def __init__(self):
        self.wallet = Wallet()
        self._pool = mp.Pool(2)
        self.qty_per_order = config.configuration['qty_per_order']

    def close(self):
        self._pool.close()
        self._pool.join()
        self._pool = None

    def request_accounts_info(self):
        print 'Requesting all accounts info...'
        accounts = self._pool.map(_polled_request_account_info, Advisor._exchanges)        
        #accounts = map(_polled_request_account_info, Advisor._exchanges)        
        for a in accounts:
            if a == None:
                print 'ERROR: Failed to request account info'
                raise RuntimeError('Failed to request account info')
        #accounts = map(_polled_request_account_info, Advisor._exchanges)        
        print 'All Accounts info accquired'
        print 'ACCOUNT INFO:'
        for a in accounts:
            print '    exchange={0}\tBTC_balance={1}\tmoney_balance={2}\tbuy={3}'.format(
                    a.name, round(a.stock_balance, 4), round(a.money_balance, 2), round(a.ticker.buy_price, 2))
        return accounts

    def _record_trade_lead(self, buy_exchange, buy_price, sell_exchange, sell_price):
        session = models.Session()
        try:
            tl = models.TradeLead(buy_exchange, buy_price, sell_exchange, sell_price)
            session.add(tl)
            session.commit()
        except Exception as e:
            print e
            session.rollback()

    def evaluate(self):
        try:
            s = self._do_evaluate()
            return s
        except IOError as e:
            print 'Network Error'
            print e
            return None
        except Exception as e:
            print e
            return None

    def _do_evaluate(self):
        accounts = self.request_accounts_info()
        #检查交易所账户余额 
        for a in accounts:
            if a.stock_balance < self.qty_per_order:
                msg = 'The balance in exchange "{0}" is not enough'.format(a.name)
                print msg
                #TODO 去掉下面的注视
                #raise RuntimeError(msg)
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
        wallet_transfer_fee_amount = buy_price * self.wallet.transfer_fee + buy_price * 0.0001
        trade_fee_amount = buy_amount * buy_account.trade_fee + sell_amount * sell_account.trade_fee
        gross_profit = round(sell_amount - buy_amount, 2)
        net_profit = round(sell_amount - buy_amount - wallet_transfer_fee_amount - trade_fee_amount, 2)
        profit_rate = net_profit / buy_amount
        threshold = config.configuration['profit_rate_threshold']
        print '[ADVISOR]\tthreshold_rate={0}%\tgross_profit={1}\t\tnet_profit={2}\tprofit_rate={3}%'.format(
                round(threshold * 100, 4), gross_profit, net_profit, round(profit_rate * 100, 4))
        print '\tbuy_price={0}\tbuy_amount={1}\tsell_price={2}\tsell_amount={3}'.format(buy_price, buy_amount, sell_price, sell_amount)
        print '\twallet_fee={0}\ttrade_fee={1}'.format(wallet_transfer_fee_amount, trade_fee_amount)
        last_order = models.Order.last()
        is_last_order_finished = (last_order == None or (last_order.state == 'done' or last_order.state == 'cancel'))
        can_go = profit_rate > threshold and net_profit > 0.01 
        if can_go:
            self._record_trade_lead(
                    buy_account.name, buy_account.ticker.buy_price, 
                    sell_account.name, sell_account.ticker.sell_price)

        can_go = can_go and is_last_order_finished    
        s = Suggestion(can_go, buy_account, sell_account, buy_price, sell_price, self.qty_per_order)
        if s.can_go:
            print '[ADVISOR]\tI FOUND A TRADE CHANCE:    TRADE IT NOW!!!'
        return s 
