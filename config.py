#encoding: utf-8

import logging
import logging.config
import json
import os

logging.basicConfig()

_CONFIG_FILE = 'brickmover.conf'


def load_config():
    with open(_CONFIG_FILE, 'r') as f:
        return json.loads(f.read()) 

configuration = load_config()

def config_logger():
    # set up logging to file - see previous section for more details
    log_path = os.path.join(configuration['data_path'],'log')
    logging.config.dictConfig({
        'version': 1,              
        'disable_existing_loggers': False,  # this fixes the problem
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
            'console': {
                'format': '[%(levelname)s] %(message)s'
            }
        },
        'handlers': {
            'default': {
                'level':'DEBUG',    
                'class':'logging.StreamHandler',
                "formatter": "console",
            },  
            "info_file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "standard",
                "filename": os.path.join(log_path, 'brickmover.info.log'),
                "maxBytes": "10485760",
                "backupCount": "20",
                "encoding": "utf8"
            },
            "error_file_handler": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "standard",
                "filename": os.path.join(log_path, 'brickmover.error.log'),
                "maxBytes": "10485760",
                "backupCount": "20",
                "encoding": "utf8"
            },
        },
        'loggers': {
            '': {                  
                'handlers': ['default', 'info_file_handler', 'error_file_handler'],
                'level': 'DEBUG',  
                'propagate': True  
            }
        }
    })


config_logger()    
