#!/bin/python
#encoding: utf-8

import time
import datetime
import multiprocessing as mp

from info import *
from exchanges import BtcChinaExchange, OKCoinExchange
import config
import models

def _polled_request_account_info(k):
    return Advisor._exchanges[k].request_info()

class Advisor:
    _exchanges = {
            BtcChinaExchange.Name: BtcChinaExchange(),
            OKCoinExchange.Name: OKCoinExchange(),
    }

    def __init__(self):
        self._pool = mp.Pool(2)    

    def request_accounts_info(self):
        print 'Requesting all accounts info...'
        accounts = self._pool.map(_polled_request_account_info, Advisor._exchanges)        
        print 'All Accounts info accquired'
        return accounts

    def evaluate(self):
        accounts = self.request_accounts_info()
        accounts = sorted(accounts, key=lambda e:e.ticker.buy_price)
        lowest = accounts[0]
        highest = accounts[len(accounts) - 1]
        qty_per_order = config.configuration['qty_per_order']
        buy_price_rate = 1.005
        sell_price_rate = 0.995
        buy_price = round(lowest.ticker.buy_price * buy_price_rate, 2)
        sell_price = round(highest.ticker.buy_price * sell_price_rate, 2)
        buy_amount = buy_price * qty_per_order
        buy_amount -= buy_amount * lowest.trade_fee
        sell_amount = sell_price * qty_per_order
        sell_amount -= sell_amount * lowest.trade_fee
        profit_rate = (sell_amount - buy_amount) / buy_amount
        threshold = config.configuration['profit_rate_threshold']
        last_order = models.Order.last()
        is_last_order_finished = (last_order == None or (last_order.state == 'done' or last_order.state == 'cancel'))
        can_go = profit_rate > threshold and is_last_order_finished
        s = Suggestion(can_go, lowest.name, highest.name, buy_price, sell_price, qty_per_order)
        if s.can_go:
            print 'TRADE CHANCE:'
            print '\tlowest={0}    highest={1}'.format(s.exchange_to_buy, s.exchange_to_sell)
            print '\tsell_price={0}    buy_price={1}    profit={2}'.format(s.sell_price, s.buy_price, s.stock_qty * (s.sell_price - s.buy_price))
            print '\tTRADE IT NOW!!!'
        else:
            print 'Sleeping time!\n'
        return s 

 
class Trader:
    _exchanges = {
            BtcChinaExchange.Name: BtcChinaExchange(),
            OKCoinExchange.Name: OKCoinExchange(),
    }

    def __init__(self):
        self.current_order = None

    def trade(self, suggest):
        self.current_suggestion = suggest
        self.current_order = self._create_order()
        self._make_orders(),

    def _create_order(self):
        s = self.current_suggestion
        session = models.Session()
        order = models.Order(s.exchange_to_buy, s.buy_price, 
                s.exchange_to_sell, s.sell_price, s.stock_qty)
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
        buy_ex = Trader._exchanges[self.current_suggestion.exchange_to_buy]
        session = models.Session()
        try:
            buy_ex.buy(self.current_suggestion.stock_qty, self.current_suggestion.buy_price)
            self.current_order.bought_time = datetime.datetime.now()
            self.current_order.is_bought = True
            session.commit()
            print 'Buy Order made: ', self.current_order.bought_time
        except:
            session.rollback()

    def _make_sell_order(self):
        sell_ex = Trader._exchanges[self.current_suggestion.exchange_to_sell]
        session = models.Session()
        try:
            sell_ex.sell(self.current_suggestion.stock_qty, self.current_suggestion.sell_price)
            self.current_order.sold_time = datetime.datetime.now()
            self.current_order.is_sold = True
            session.commit()
            print 'Sell Order made: ', self.current_order.sold_time
        except:
            session.rollback()

    def make_balance(self):
        '''比特币转账
        '''
        self._wait_balance()
    
    def _wait_balance(self):
        print 'Waiting for balance...'
        time.sleep(1)

    def _wait_sms(self):
        pass


def main_loop():
    advisor = Advisor()
    trader = Trader()
    while True:
        s = advisor.evaluate()        
        if s.can_go:
            trader.trade(s)
            trader.make_balance()
            print '\n'
        time.sleep(5)        

if __name__ == '__main__':
    mp.freeze_support()
    print 'The Most Awesome Automatic Arbitrage Bot for BitCoin Exchanges'
    print 'Written By Wei Li <oldrev@gmail.com>'
    print 'Dad, I gonna make you rich!'
    print '\n'

    main_loop_process = mp.Process(target=main_loop)
    main_loop_process.start()
    time.sleep(5)
    cmd = ''
    while cmd != 'quit':
        cmd = raw_input("Type 'quit' to end: ")
    main_loop_process.join()
