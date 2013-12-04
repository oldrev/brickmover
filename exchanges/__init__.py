#encoding: utf-8

import json
import httplib
import datetime
import cookielib
import urllib, urllib2
import random
import logging
import os
import sys
import lxml.html
import lxml.etree

import btcchina
import okcoin

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from brickmover import config

cfg = config.configuration['exchanges']
actived_exchanges = {'btcchina': btcchina.BtcChinaExchange(cfg['btcchina']), 'okcoin': okcoin.OKCoinExchange(cfg['okcoin'])}

_logger = logging.getLogger('exchanges')


