#encoding: utf-8

class Ticker:
    def __init__(self, buy_price, sell_price, last_price):
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.last_price = last_price

    def __str__(self):
        s = str({ 
            'buy_price': self.buy_price, 
            'sell_price': self.sell_price,
            'last_price': self.last_price
        })
        return s


class AccountInfo:
    def __init__(self, 
            name, ticker, trade_fee, 
            money_balance, stock_balance, stock_deposit_address):
        assert name
        assert ticker
        self.name = name
        self.ticker = ticker
        self.trade_fee = trade_fee
        self.money_balance = money_balance
        self.stock_balance = stock_balance
        self.stock_deposit_address = stock_deposit_address
            

class Suggestion:
    def __init__(self, can_go, buy_account, sell_account, buy_price, sell_price, stock_qty):
        self.buy_account = buy_account
        self.sell_account = sell_account
        self.buy_price = buy_price
        self.sell_price = sell_price
        self.stock_qty = stock_qty 
        self.can_go = can_go
