#encoding: utf-8

import base64, hashlib, hmac, urllib2, time, urllib, json
import logging

from brickmover import config
from brickmover.info import *

base = 'https://data.mtgox.com/api/2/'

_logger = logging.getLogger('exchanges')

def post_request(key, secret, path, data):
    hmac_obj = hmac.new(secret, path + chr(0) + data, hashlib.sha512)
    hmac_sign = base64.b64encode(hmac_obj.digest())

    header = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'gox2 based client',
        'Rest-Key': key,
        'Rest-Sign': hmac_sign,
    }

    request = urllib2.Request(base + path, data, header)
    response = urllib2.urlopen(request, data)
    return json.load(response)


def gen_tonce():
    return str(int(time.time() * 1e6))


class MtGoxInterface:

    def __init__(self, key, secret):
        self.key = key
        self.secret = base64.b64decode(secret)

    def request(self, path, params={}):
        params = dict(params)
        params['tonce'] = gen_tonce()
        data = urllib.urlencode(params)

        result = post_request(self.key, self.secret, path, data)
        if result['result'] == 'success':
            return result['data']
        else:
            raise Exception(result['result'])

    def get_account_info(self):
        r = self.request('BTCUSD/money/info')
        return r


    def get_stock_deposit_address(self):
        return self.request('money/bitcoin/address')['addr']


class MtGoxExchange:

    def __init__(self, cfg):
        self._config = cfg
        self.can_withdraw_stock_to_address = True
        self.stock_withdraw_fee = 0.0005
        self.trade_fee = 0.006
        access = self._config['access_key'].encode('utf-8')
        secret = self._config['secret_key'].encode('utf-8')
        self._mtgox2 = MtGoxInterface(access, secret)

    def login(self):
        pass
            
    def request_ticker(self):
        url = 'http://data.mtgox.com/api/2/BTCUSD/money/ticker'
        response = urllib2.urlopen(url, timeout=10)
        ticker_data = json.loads(response.read())['data']
        ticker = Ticker(float(ticker_data['buy']['value']), float(ticker_data['sell']['value']), float(ticker_data['last']['value']))
        return ticker

    def request_info(self):
        self.login()
        ticker = self.request_ticker()
        ai = self._mtgox2.get_account_info()
        account_info = AccountInfo('mtgox', ticker, 
                self.trade_fee,
                float(ai['Wallets']['USD']['Balance']['value']), 
                float(ai['Wallets']['BTC']['Balance']['value']), 
                '12321321312')
        return account_info

    def buy(self, stock_qty, price):
        pass

    def sell(self, stock_qty, price):
        pass 

    def withdraw_stock(self, amount):
        params = {'address': None, 'amount_int': int(amount * 1e8), 'fee_int': 0}
        r = self.request('money/bitcoin/send_simple', )
        return  r
