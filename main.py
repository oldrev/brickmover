#!/bin/python
#encoding: utf-8

import time
import datetime
import multiprocessing as mp

from info import *
from exchanges import BtcChinaExchange, OKCoinExchange
import config
import models
from advisor import Advisor
from wallet import Wallet


class Trader:
    _exchanges = {
            BtcChinaExchange.Name: BtcChinaExchange(),
            OKCoinExchange.Name: OKCoinExchange(),
    }

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
        except:
            session.rollback()
            return None

    def _make_orders(self):
        '''下买卖委托单'''
        #TODO 并行化处理
        self._make_sell_order()
        self._make_buy_order()

    def _make_buy_order(self):
        buy_ex = Trader._exchanges[self.current_suggestion.buy_account.name]
        session = models.Session()
        try:
            #buy_ex.buy(self.current_suggestion.stock_qty, self.current_suggestion.buy_price)
            self.current_order.bought_time = datetime.datetime.now()
            self.current_order.is_bought = True
            session.commit()
            print 'Buy Order made: ', self.current_order.bought_time
        except:
            session.rollback()

    def _make_sell_order(self):
        sell_ex = Trader._exchanges[self.current_suggestion.sell_account.name]
        session = models.Session()
        try:
            #sell_ex.sell(self.current_suggestion.stock_qty, self.current_suggestion.sell_price)
            self.current_order.sold_time = datetime.datetime.now()
            self.current_order.is_sold = True
            session.commit()
            print 'Sell Order made: ', self.current_order.sold_time
        except:
            session.rollback()

    
    def _wait_balance(self):
        print 'Waitig for balance...'
        time.sleep(1)

    def _wait_sms(self):
        pass


class Cashier:
    _exchanges = {
            BtcChinaExchange.Name: BtcChinaExchange(),
            OKCoinExchange.Name: OKCoinExchange(),
    }

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
                self.wallet.withdraw(a.stock_deposit_address, self.qty_per_order)
                wallet_balance -= self.qty_per_order


def main_loop(stop_event):
    the_advisor = Advisor()
    trader = Trader()
    try:
        while not stop_event.is_set():
            s = the_advisor.evaluate()        
            if stop_event.is_set():
                break;
            if s != None and s.can_go:
                trader.trade(s)
                trader.post_transfers()
                print '\n'
            else:
                print 'Bad time to trade, just wait a moment...'
            print '----------------------------------------------------'                
            time.sleep(5)
    except:
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
    print 'Preparing to stop main loop process...'
    stop_main_event.set()
    main_loop_process.join()
    print 'All done. Bye.'
