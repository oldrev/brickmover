# -*- coding: utf-8 -*-
## Author:      t0pep0
## e-mail:      t0pep0.gentoo@gmail.com
## Jabber:      t0pep0@jabber.ru
## BTC   :      1ipEA2fcVyjiUnBqUx7PVy5efktz2hucb
## donate free =)
import httplib
import urllib, urllib2
import json
import hashlib
import hmac
import time, datetime
import os
import cookielib

from brickmover import config
from brickmover.info import *


class BTCEInterface:
    __api_key        =  '';
    __api_secret        = '' 
    __nonce_v        = 1;
    __wait_for_nonce = False

    def __init__(self,api_key,api_secret,wait_for_nonce=False):
        self.__api_key = api_key
        self.__api_secret = api_secret
        self.__wait_for_nonce = wait_for_nonce

    def __nonce(self):
        if self.__wait_for_nonce:
            time.sleep(1)
        self.__nonce_v = str(time.time()).split('.')[0]

    def __signature(self, params):
        return hmac.new(self.__api_secret, params, digestmod=hashlib.sha512).hexdigest()

    def __api_call(self,method,params):
        self.__nonce()
        params['method'] = method
        params['nonce'] = str(self.__nonce_v)
        params = urllib.urlencode(params)
        headers = {"Content-type" : "application/x-www-form-urlencoded",
                         "Key" : self.__api_key,
                        "Sign" : self.__signature(params)}
        conn = httplib.HTTPSConnection("btc-e.com")
        conn.request("POST", "/tapi", params, headers)
        response = conn.getresponse()
        data = json.load(response)
        conn.close()
        return data
     
    def get_param(self, couple, param):
        conn = httplib.HTTPSConnection("btc-e.com")
        conn.request("GET", "/api/2/"+couple+"/"+param)
        response = conn.getresponse()
        data = json.load(response)
        conn.close()
        return data

    def get_info(self):
        r = self.__api_call('getInfo', {})
        return r['return']

    def get_trans_history(self, tfrom, tcount, tfrom_id, tend_id, torder, tsince, tend):
        params = {
                "from"        : tfrom,
                "count"        : tcount,
                "from_id"        : tfrom_id,
                "end_id"        : tend_id,
                "order"        : torder,
                "since"        : tsince,
                "end"        : tend}
        return self.__api__call('TransHistory', params)

    def get_trade_history(self, tfrom, tcount, tfrom_id, tend_id, torder, tsince, tend, tpair):
        params = {
                "from"        : tfrom,
                "count"        : tcount,
                "from_id"        : tfrom_id,
                "end_id"        : tend_id,
                "order"        : torder,
                "since"        : tsince,
                "end"        : tend,
                "pair"        : tpair}
        return self.__api_call('TradeHistory', params)

    def get_active_orders(self, tpair):
        params = { "pair" : tpair }
        return self.__api_call('ActiveOrders', params)

    def trade(self, tpair, ttype, trate, tamount):
        params = {
                "pair"        : tpair,
                "type"        : ttype,
                "rate"        : trate,
                "amount"        : tamount}
        r = self.__api_call('Trade', params)
        if r['success'] != 1:
            raise Exception('BTCEInterface: Failed to trade')

    def cancel_order(self, torder_id):
        params = { "order_id" : torder_id }
        return self.__api_call('CancelOrder', params)



class BTCEExchange:
    session_period = 15

    def __init__(self, cfg):
        self._config = cfg
        self.can_withdraw_stock_to_address = True
        self.stock_withdraw_fee = 0.0005
        self.trade_fee = 0.005
        access = self._config['access_key'].encode('utf-8')
        secret = self._config['secret_key'].encode('utf-8')
        self.username = self._config['user_name']
        self.password = self._config['password']
        self.stock_deposit_address = self._config['stock_deposit_address']
        self._last_logged_time = None
        self._btce = BTCEInterface(access, secret)
        self.cookie_file = os.path.join(config.configuration['data_path'], 'btce.cookies')
        self.cookieJar = cookielib.MozillaCookieJar(self.cookie_file)
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(debuglevel=0),
            urllib2.HTTPSHandler(debuglevel=0),
            urllib2.HTTPCookieProcessor(self.cookieJar)
        )
        # pretend we're a web browser and not a python script
        self.opener.addheaders = [('User-agent', 
            ('Mozilla/4.0 (compatible; MSIE 10.0; '
            'Windows NT 5.2; .NET CLR 1.1.4322)'))
        ]


    def login(self):
        if self._last_logged_time and ((datetime.datetime.now() - self._last_logged_time).total_seconds() < BTCEExchange.session_period * 60):
            return
        base_url = 'https://btc-e.com'
        self._last_logged_time = datetime.datetime.now()

        # open the front page of the website to set and save initial cookies
        response = self.opener.open(base_url)
        self.cookieJar.save()
        response.close()

        login_data = urllib.urlencode({
            'email' : self.username,
            'password' : self.password
        })
        login_action = '/login'
        login_url = base_url + login_action 
        response = self.opener.open(login_url, login_data)
        self.cookieJar.save()
        response.close()


    def request_ticker(self):
        url = 'https://btc-e.com/api/2/btc_usd/ticker'
        response = urllib2.urlopen(url, timeout=10)
        ticker_data = json.loads(response.read())['ticker']
        ticker = Ticker(float(ticker_data['buy']), float(ticker_data['sell']), float(ticker_data['last']))
        return ticker


    def request_info(self):
        self.login()
        ticker = self.request_ticker()
        ai = self._btce.get_info()
        account_info = AccountInfo('btce', ticker, 
                self.trade_fee,
                float(ai['funds']['usd']), 
                float(ai['funds']['btc']), 
                self.stock_deposit_address)
        return account_info

    def buy(self, stock_qty, price):
        self.login()
        self._btce.trade('btc_usd', 'buy', price, stock_qty)

    def sell(self, stock_qty, price):
        self._btce.trade('btc_usd', 'sell', price, stock_qty)

    def withdraw_stock(self, amount):
        params = {'address': None, 'amount_int': int(amount * 1e8), 'fee_int': 0}
        r = self.request('money/bitcoin/send_simple', )
        return  r
