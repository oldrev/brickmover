#!/bin/python
#encoding: utf-8

import os, sys
import time
import datetime
import multiprocessing as mp
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

from info import *
import models
from advisor import Advisor
from wallet import Wallet
import exchanges

_logger = logging.getLogger(__name__)

class Trader:
    _exchanges = exchanges.actived_exchanges 

    def __init__(self):
        self.current_order = None
        self.wallet = Wallet()
        self.qty_per_order = config.configuration['qty_per_order']

    def trade(self, suggest):
        self.current_suggestion = suggest
        self.current_order = self._create_order()
        self._make_orders(),

    def _create_order(self):
        s = self.current_suggestion
        session = models.Session()
        order = models.Order(s.buy_account.name, s.buy_price, 
                    s.sell_account.name, s.sell_price, s.stock_qty)
        try:
            session.add(order)
            session.commit()
            return order
        except Exception as e:
            _logger.error(e)
            session.rollback()
            return None

    def _make_orders(self):
        '''下买卖委托单'''
        #TODO 并行化处理
        self._make_sell_order()
        self._make_buy_order()
        self._check_order_state()

    def _check_order_state(self):
        session = models.Session()
        try:
            if self.current_order.is_bought and self.current_order.is_sold:
                self.current_order.state = 'done'
                _logger.info('[TRADER] The order is done!')
                session.commit()
        except Exception as e:
            _logger.error(e)
            session.rollback()


    def _make_buy_order(self):
        buy_ex = Trader._exchanges[self.current_suggestion.buy_account.name]
        session = models.Session()
        try:
            #buy_ex.buy(self.current_suggestion.stock_qty, self.current_suggestion.buy_price)
            self.current_order.bought_time = datetime.datetime.now()
            self.current_order.is_bought = True
            session.commit()
            _logger.info('Buy Order made: {0}'.format(self.current_order.bought_time))
        except Exception as e:
            _logger.error(e)
            session.rollback()

    def _make_sell_order(self):
        sell_ex = Trader._exchanges[self.current_suggestion.sell_account.name]
        session = models.Session()
        try:
            #sell_ex.sell(self.current_suggestion.stock_qty, self.current_suggestion.sell_price)
            self.current_order.sold_time = datetime.datetime.now()
            self.current_order.is_sold = True
            session.commit()
            _logger.info('Sell Order made: {0}'.format(self.current_order.sold_time))
        except Exception as e:
            _logger.error(e)
            session.rollback()

    
    def _wait_balance(self):
        _logger.info('Waitig for balance...')
        time.sleep(1)

    def _wait_sms(self):
        pass


class Cashier:
    _exchanges = exchanges.actived_exchanges 

    def __init__(self):
        self.wallet = Wallet()
        self.qty_per_order = config.configuration['qty_per_order']

    def post_transfers(self, buy_account, sell_account):
        '''交易完成以后的比特币转账
        流程：
        1. 检查钱包是否有足够余额
            2.1 有余额则先发送比特币给卖方
        2. 买方转移比特币到钱包        
        '''
        buy_ex = Trader._exchanges[buy_account.name]
        sell_ex = Trader._exchanges[sell_account.name]
        wallet_balance = self.wallet.balance()
        if wallet_balance > self.qty_per_order:
            self.wallet.withdraw(sell_account.stock_deposit_address, self.qty_per_order)
        buy_ex.withdraw_stock(self.qty_per_order)            

    def make_balance(self, accounts):
        wallet_balance = self.wallet.balance()        
        for a in accounts:
            if a.stock_balance < self.qty_per_order and wallet_balance > self.qty_per_order:
                _logger.info('[CASHIER]\t\t Transfering BTC from wallet to account "{0}", qty={1}'
                        .format(a.name, self.qty_per_order))
                self.wallet.withdraw(a.stock_deposit_address, self.qty_per_order)
                wallet_balance -= self.qty_per_order


def wait_event(event, seconds):
    for i in xrange(0, seconds):
        if event.is_set():
            break            
        time.sleep(1)

def main_loop(stop_event):
    the_advisor = Advisor()
    trader = Trader()
    cashier = Cashier()

    try:
        while not stop_event.is_set():
            _logger.info(u'--------------------------- 交易处理开始 ---------------------------')
            accounts = the_advisor.request_accounts_info()

            #cashier.make_balance(accounts)

            s = the_advisor.evaluate(accounts)
            if stop_event.is_set():
                break;
            if s != None and s.can_go:
                print 'trader()'
                trader.trade(s)
                print 'post_transfers()'
                #trader.post_transfers()
                print '\n'
            else:
                _logger.info(u'交易条件不具备，等上一会儿....')
            wait_event(stop_event, 60)
    except Exception as e:
        print e
        pass
    finally:
        the_advisor.close()


if __name__ == '__main__':
    mp.freeze_support()
    print 'The Most Awesome Automatic Arbitrage Bot for BitCoin Exchanges'
    print 'Written By Wei Li <oldrev@gmail.com>'
    print 'It is the time to make some money!'
    print '\n'

    stop_main_event = mp.Event()
    main_loop_process = mp.Process(target=main_loop, args=(stop_main_event,))
    main_loop_process.start()
    cmd = ''
    while cmd != 'quit':
        cmd = raw_input("Type 'quit' to end: ")
    _logger.info('Preparing to stop main loop process...')
    stop_main_event.set()
    main_loop_process.join()
    _logger.info(u'程序已经成功停止')
    print 'All done. Bye.'
