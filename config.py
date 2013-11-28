#encoding: utf-8

import logging
import json

logging.basicConfig()

_CONFIG_FILE = 'brickmover.conf'


def load_config():
    with open(_CONFIG_FILE, 'r') as f:
        return json.loads(f.read()) 

configuration = load_config()
