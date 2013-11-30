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

SATOSHI_PER_BTC = 100000000

class Wallet:
    __base_url = 'https://blockchain.info/zh-cn/merchant'    
    __timeout = 30
    
    def __init__(self):
        self._config = config.configuration['wallet']
        self.userid = self._config['userid']
        self.password = self._config['password']
        self.transfer_fee = 0.0005

    def balance(self):
        '''URL:
        https://blockchain.info/zh-cn/merchant/$guid/balance?password=$main_password
        '''
        url = '{0}/{1}/balance?password={2}'.format(Wallet.__base_url, self.userid, self.password)
        request = urllib2.Request(url)
        response = urllib2.urlopen(request, timeout=Wallet.__timeout)
        balance_data = json.loads(response.read())
        response.close()
        return float(balance_data['balance']) / float(SATOSHI_PER_BTC)

    def withdraw(self, address, btc):
        '''
        URL:
        https://blockchain.info/zh-cn/merchant/$guid/payment?password=$main_password&second_password=$second_password&to=$address&amount=$amount&from=$from&shared=$shared&fee=$fee¬e=$note
        '''
        satoshi = btc * SATOSHI_PER_BTC 
        url = '{0}/{1}/payment?password={2}&to={3}&amount={4}'.format(
                Wallet.__base_url, self.userid, self.password, address, satoshi)
        request = urllib2.Request(url)
        response = urllib2.urlopen(request, timeout=Wallet.__timeout)
        response_data = json.loads(response.read())
        response.close()
        return response_data['tx_hash']
