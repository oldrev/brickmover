#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
import time
import re
import hmac
import hashlib
import base64
import httplib
import json
import os, os.path
import urllib, urllib2
import cookielib
import logging

from brickmover import config
from brickmover.info import *

class BtcChinaInterface():
    def __init__(self,access=None,secret=None):
        self.access_key=access
        self.secret_key=secret
        self.conn=httplib.HTTPSConnection("api.btcchina.com")
 
    def _get_tonce(self):
        return int(time.time()*1000000)
 
    def _get_params_hash(self,pdict):
        pstring=""
        # The order of params is critical for calculating a correct hash
        fields=['tonce','accesskey','requestmethod','id','method','params']
        for f in fields:
            if pdict[f]:
                if f == 'params':
                    # Convert list to string, then strip brackets and spaces
                    # probably a cleaner way to do this
                    param_string=re.sub("[\[\] ]","",str(pdict[f]))
                    param_string=re.sub("'",'',param_string)
                    pstring+=f+'='+param_string+'&'
                else:
                    pstring+=f+'='+str(pdict[f])+'&'
            else:
                pstring+=f+'=&'
        pstring=pstring.strip('&')
 
        # now with correctly ordered param string, calculate hash
        phash = hmac.new(self.secret_key, pstring, hashlib.sha1).hexdigest()
        return phash
 
    def _private_request(self,post_data):
        #fill in common post_data parameters
        tonce=self._get_tonce()
        post_data['tonce']=tonce
        post_data['accesskey']=self.access_key
        post_data['requestmethod']='post'
 
        # If ID is not passed as a key of post_data, just use tonce
        if not 'id' in post_data:
            post_data['id']=tonce
 
        pd_hash=self._get_params_hash(post_data)
 
        # must use b64 encode        
        auth_string='Basic '+base64.b64encode(self.access_key+':'+pd_hash)
        headers={'Authorization':auth_string,'Json-Rpc-Tonce':tonce}
 
        #post_data dictionary passed as JSON        
        self.conn.request("POST",'/api_trade_v1.php',json.dumps(post_data),headers)
        response = self.conn.getresponse()
 
        # check response code, ID, and existence of 'result' or 'error'
        # before passing a dict of results
        if response.status == 200:
            # this might fail if non-json data is returned
            resp_dict = json.loads(response.read())
 
            # The id's may need to be used by the calling application,
            # but for now, check and discard from the return dict
            if str(resp_dict['id']) == str(post_data['id']):
                if 'result' in resp_dict:
                    return resp_dict['result']
                elif 'error' in resp_dict:
                    return resp_dict['error']
        else:
            # not great error handling....
            raise IOError('Request error')
 
        return None
 
    def get_account_info(self,post_data={}):
        post_data['method']='getAccountInfo'
        post_data['params']=[]
        return self._private_request(post_data)
 
    def get_market_depth(self,post_data={}):
        post_data['method']='getMarketDepth'
        post_data['params']=[]
        return self._private_request(post_data)
 
    def buy(self,price,amount,post_data={}):
        post_data['method']='buyOrder'
        post_data['params']=[price,amount]
        return self._private_request(post_data)
 
    def sell(self,price,amount,post_data={}):
        post_data['method']='sellOrder'
        post_data['params']=[price,amount]
        return self._private_request(post_data)
 
    def cancel(self,order_id,post_data={}):
        post_data['method']='cancelOrder'
        post_data['params']=[order_id]
        return self._private_request(post_data)
 
    def request_withdrawal(self,currency,amount,post_data={}):
        post_data['method']='requestWithdrawal'
        post_data['params']=[currency,amount]
        return self._private_request(post_data)
 
    def get_deposits(self,currency='BTC',pending=True,post_data={}):
        post_data['method']='getDeposits'
        if pending:
            post_data['params']=[currency]
        else:
            post_data['params']=[currency,'false']
        return self._private_request(post_data)
 
    def get_orders(self,id=None,open_only=True,post_data={}):
        # this combines getOrder and getOrders
        if id is None:
            post_data['method']='getOrders'
            if open_only:
                post_data['params']=[]
            else:
                post_data['params']=['false']
        else:
            post_data['method']='getOrder'
            post_data['params']=[id]
        return self._private_request(post_data)
 
    def get_withdrawals(self,id='BTC',pending=True,post_data={}):
        # this combines getWithdrawal and getWithdrawls
        try:
            id = int(id)
            post_data['method']='getWithdrawal'
            post_data['params']=[id]
        except:
            post_data['method']='getWithdrawals'
            if pending:
                post_data['params']=[id]
            else:
                post_data['params']=[id,'false']
        return self._private_request(post_data)


class BtcChinaExchange:
    Name = 'btcchina'
    session_period = 30
    HOST = 'api.btcchina.com'

    def __init__(self, cfg):
        self._logger = logging.getLogger('BtcChinaExchange')
        self._config = cfg
        self.can_withdraw_stock_to_address = False
        self._last_logged_time = None
        self.stock_withdraw_fee = 0.0001
        self.username = self._config['user_name']
        self.password = self._config['password']
        self.cookie_file = os.path.join(config.configuration['data_path'], 'btcchina.cookies')
        self.cookieJar = cookielib.MozillaCookieJar(self.cookie_file)
        self.trade_fee = self._config['trade_fee']
        access = self._config['access_key'].encode('utf-8')
        secret = self._config['secret_key'].encode('utf-8')
        self._btcchina = BtcChinaInterface(access, secret)
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
        self._logger.info(u'准备开始请求 btcchina.com 帐号信息')
        self.login()
        ticker = self.request_ticker()
        ai = self._btcchina.get_account_info()
        account_info = AccountInfo(BtcChinaExchange.Name, ticker, 
                self.trade_fee,
                float(ai['balance']['cny']['amount']), 
                float(ai['balance']['btc']['amount']), 
                ai['profile']['btc_deposit_address'])
        return account_info

    def withdraw_stock(self, address, amount):
        self._btcchina.request_withdrawal('btc', amount)

    def buy(self, stock_qty, price):
        self._btcchina.buy(price, stock_qty)

    def sell(self, stock_qty, price):
        self._btcchina.sell(price, stock_qty)

