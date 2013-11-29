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
    try:
        return Advisor._exchanges[k].request_info()
    except:
        return None

class Advisor:
    _exchanges = {
            BtcChinaExchange.Name: BtcChinaExchange(),
            OKCoinExchange.Name: OKCoinExchange(),
    }

    def __init__(self):
        self._pool = mp.Pool(2)    

    def close(self):
        self._pool.close()
        self._pool.join()
        self._pool = None

    def request_accounts_info(self):
        print 'Requesting all accounts info...'
        accounts = self._pool.map(_polled_request_account_info, Advisor._exchanges)        
        for a in accounts:
            if a == None:
                print 'ERROR: Failed to request account info'
                raise RuntimeError('Failed to request account info')
        #accounts = map(_polled_request_account_info, Advisor._exchanges)        
        print 'All Accounts info accquired'
        print 'ACCOUNT INFO:'
        for a in accounts:
            print '    exchange={0}\tBTC_balance={1}\tmoney_balance={2}\tbuy={3}'.format(a.name, a.stock_balance, a.money_balance, a.ticker.buy_price)
        return accounts

    def evaluate(self):
        try:
            self._do_evaluate()
        except:
            return None

    def _do_evaluate(self):
        accounts = self.request_accounts_info()
        accounts = sorted(accounts, key=lambda e:e.ticker.buy_price)
        lowest = accounts[0]
        highest = accounts[len(accounts) - 1]
        qty_per_order = config.configuration['qty_per_order']
        buy_price_rate = 1.002
        sell_price_rate = 0.998
        buy_price = round(lowest.ticker.buy_price * buy_price_rate, 2)
        sell_price = round(highest.ticker.buy_price * sell_price_rate, 2)
        buy_amount = buy_price * qty_per_order
        buy_amount -= buy_amount * lowest.trade_fee
        sell_amount = sell_price * qty_per_order
        sell_amount -= sell_amount * highest.trade_fee
        profit_rate = (sell_amount - buy_amount) / buy_amount
        threshold = config.configuration['profit_rate_threshold']
        print '[ADVISOR] threshold_rate={0}%\tprofit={1}\tprofit_rate={2}%'.format(
                round(threshold * 100, 4), round(sell_amount - buy_amount, 2), round(profit_rate * 100, 4))
        last_order = models.Order.last()
        is_last_order_finished = (last_order == None or (last_order.state == 'done' or last_order.state == 'cancel'))
        can_go = profit_rate > threshold and is_last_order_finished
        s = Suggestion(can_go, lowest.name, highest.name, buy_price, sell_price, qty_per_order)
        print '    lowest={0}\t\thighest={1}'.format(s.exchange_to_buy, s.exchange_to_sell)
        if s.can_go:
            print '[ADVISOR] TRADE CHANCE:'
            print '    lowest={0}\t\thighest={1}'.format(s.exchange_to_buy, s.exchange_to_sell)
            print '    sell_price={0}    buy_price={1}'.format(s.sell_price, s.buy_price)
            print '    TRADE IT NOW!!!'
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
        print 'Waitig for balance...'
        time.sleep(1)

    def _wait_sms(self):
        pass


def main_loop(stop_event):
    try:
        advisor = Advisor()
        trader = Trader()
        while not stop_event.is_set():
            s = advisor.evaluate()        
            if stop_event.is_set():
                break;
            if s != None and s.can_go:
                trader.trade(s)
                trader.make_balance()
                print '\n'
            else:
                print 'Bad time to trade, just wait a moment...'
                time.sleep(10)
            print '----------------------------------------------------'                
    except:
        pass
    finally:
        advisor.close()


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
