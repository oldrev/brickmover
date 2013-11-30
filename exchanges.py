#encoding: utf-8

import json
import httplib
import datetime
import cookielib
import urllib, urllib2
import random
import logging
import os
import lxml.html
import lxml.etree

from info import *
import config
import btcchina

_logger = logging.getLogger('exchanges')


class OKCoinBtcDepositParser():
    def __init__(self):
        self.btc_deposit_address_path = '//div[@class="fincoinaddress-1"]/span'
        self.money_balance_path = '//div[@class="accountinfo1"]/div/ul/li[2]/span[2]'
        self.btc_balance_path = '//div[@class="accountinfo1"]/div/ul/li[3]/span[2]'
        self.btc_deposit_address = None
        self.money_balance = 0.0
        self.btc_balance = 0.0
        self.soup = None

    def parse(self, html):
        tree = lxml.html.document_fromstring(html)
        self.btc_deposit_address = tree.xpath(self.btc_deposit_address_path)[0].text
        self.money_balance = float(tree.xpath(self.money_balance_path)[0].text)
        self.btc_balance = float(tree.xpath(self.btc_balance_path)[0].text)


class OKCoinExchange:
    Name = 'okcoin'
    session_period = 10
    HOST = 'www.okcoin.com'
    BASE_URL = 'https://' + HOST

    def __init__(self):
        self._config = config.configuration['exchanges'][OKCoinExchange.Name]
        self.stock_withdraw_fee = 0.0001
        self.trade_fee = self._config['trade_fee']
        self._last_logged_time = None
        self.cookie_file = os.path.join(config.configuration['data_path'], 'okcoin.cookies')
        self.cookieJar = cookielib.MozillaCookieJar(self.cookie_file)
        # user provided username and password
        self.username = self._config['user_name']
        self.password = self._config['password']
        self.trade_password = self._config['trade_password']
        # set up opener to handle cookies, redirects etc
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

    def _make_post_url(self, action):
        rnd = int(random.random() * 100)
        return OKCoinExchange.BASE_URL + action + '?random=' + str(rnd)

    def _send_sms_code(self, type, withdraw_amount, withdraw_btc_addr, symbol):
        '''
        type 的解释：
        1: BTC/LTC提现
        2: 设置提现地址
        3: 人民币提现
        '''
        self.login()
        url = self._make_post_url('/account/sendMsgCode.do')
        params = urllib.urlencode({
            'type': type, 
            'withdrawAmount': withdraw_amount, 
            'withdrawBtcAddr': withdraw_btc_addr, 
            'symbol':symbol
        })
        response = self.opener.open(url, params)
        response.close()

    def login(self):
        if self._last_logged_time and ((datetime.datetime.now() - self._last_logged_time).total_seconds() < OKCoinExchange.session_period * 60):
            return
        base_url = 'https://' + OKCoinExchange.HOST
        self._last_logged_time = datetime.datetime.now()

        # open the front page of the website to set and save initial cookies
        response = self.opener.open(OKCoinExchange.BASE_URL)
        self.cookieJar.save()
        response.close()

        login_data = urllib.urlencode({
            'loginName' : self.username,
            'password' : self.password
        })
        login_action = '/login/index.do'
        login_url = self._make_post_url(login_action)
        response = self.opener.open(login_url, login_data)
        self.cookieJar.save()
        response.close()

    def request_ticker(self):
        url = 'https://www.okcoin.com/api/ticker.do'
        response = urllib2.urlopen(url, timeout=10)
        ticker_data = json.loads(response.read())['ticker']
        ticker = Ticker(float(ticker_data['buy']), float(ticker_data['sell']), float(ticker_data['last']))
        return ticker

    def request_info(self):
        _logger.info('准备开始请求 okcoin.com 帐号信息')
        ticker = self.request_ticker()
        self.login()
        response = self.opener.open('https://www.okcoin.com/rechargeBtc.do')
        parser = OKCoinBtcDepositParser()
        html = response.read()
        parser.parse(html)        
        btc_deposit_address = parser.btc_deposit_address
        response.close()
        #withdraw_btc_addr = '17Ar3q9Bkfz7i6RhTJcobgnYw6gNVfE4JE'
        #withdraw_amount = '0.1'
        #type = 1
        #symbol='btc'
        #self._send_sms_code(type, withdraw_amount, withdraw_btc_addr, symbol)
        return AccountInfo(OKCoinExchange.Name, ticker, self.trade_fee, parser.money_balance, parser.btc_balance, btc_deposit_address)

    def withdraw_stock(self, amount):
        trade_data = urllib.urlencode({
            'withdrawAddr': '',
            'withdrawAmount': amount,
            'tradePwd': self.trade_password,
            'validateCode': '',
            'symbol': 0,
        })
        action = '/account/withdrawBtcSubmit.do'
        url = self._make_post_url(action)
        response = self.opener.open(url, trade_data)
        response.close()

    def buy(self, stock_qty, price):
        trade_data = urllib.urlencode({
            'tradeAmount': stock_qty,
            'tradeCnyPrice': price,
            'tradePwd': self.trade_password,
            'symbol': 0,
        })
        action = '/trade/buyBtcSubmit.do'
        url = self._make_post_url(action)
        response = self.opener.open(url, trade_data)
        response.close()

    def sell(self, stock_qty, price):
        trade_data = urllib.urlencode({
            'tradeAmount': stock_qty,
            'tradeCnyPrice': price,
            'tradePwd': self.trade_password,
            'symbol': 0,
        })
        action = '/trade/sellBtcSubmit.do'
        url = self._make_post_url(action)
        response = self.opener.open(url, trade_data)
        response.close()


class BtcChinaExchange:
    Name = 'btcchina'
    session_period = 30
    HOST = 'api.btcchina.com'

    def __init__(self):
        self._config = config.configuration['exchanges'][BtcChinaExchange.Name]
        self._last_logged_time = None
        self.stock_withdraw_fee = 0.0001
        self.username = self._config['user_name']
        self.password = self._config['password']
        self.cookie_file = os.path.join(config.configuration['data_path'], 'btcchina.cookies')
        self.cookieJar = cookielib.MozillaCookieJar(self.cookie_file)
        self.trade_fee = self._config['trade_fee']
        access = self._config['access_key'].encode('utf-8')
        secret = self._config['secret_key'].encode('utf-8')
        self._btcchina = btcchina.BtcChinaInterface(access, secret)
        # set up opener to handle cookies, redirects etc
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

    def _send_vcode(self):
        self.login()
        response = self.opener.open('https://vip.btcchina.com/account/withdraw.btc')
        html = response.read()
        tree = lxml.html.document_fromstring(html)
        #vcode_hidden = tree.xpath('//input[@id="vcode_id"]')
        vcode_hidden = tree.xpath('//input')
        print "######"
        print vcode_hidden
        response.close()
        pass

    def login(self):
        '''
        
        if self._last_logged_time and ((datetime.datetime.now() - self._last_logged_time).total_seconds() < BtcChinaExchange.session_period * 60):
            return
        base_url = 'https://vip.btcchina.com'
        self._last_logged_time = datetime.datetime.now()
        #open the front page of the website to set and save initial cookies
        login_url = base_url + '/bbs/ucp.php?mode=login'
        response = self.opener.open(login_url)
        self.cookieJar.save()
        response.close()
        login_data = urllib.urlencode({
            'username' : self.username,
            'password' : self.password,
            'redirect' : '/trade',
        })
        response = self.opener.open(login_url, login_data)
        self.cookieJar.save()
        response.close()
        '''
        pass

    def request_ticker(self):
        url = 'https://data.btcchina.com/data/ticker'
        response = urllib2.urlopen(url, timeout=10)
        ticker_data = json.loads(response.read())['ticker']
        ticker = Ticker(float(ticker_data['buy']), float(ticker_data['sell']), float(ticker_data['last']))
        return ticker

    def request_info(self):
        _logger.info('准备开始请求 btcchina.com 帐号信息')
        self.login()
        ticker = self.request_ticker()
        ai = self._btcchina.get_account_info()
        account_info = AccountInfo(BtcChinaExchange.Name, ticker, 
                self.trade_fee,
                float(ai['balance']['cny']['amount']), 
                float(ai['balance']['btc']['amount']), 
                ai['profile']['btc_deposit_address'])
        return account_info

    def withdraw_stock(self, amount):
        self._btcchina.request_withdrawal('btc', amount)

    def buy(self, stock_qty, price):
        self._btcchina.buy(price, stock_qty)

    def sell(self, stock_qty, price):
        self._btcchina.sell(price, stock_qty)
