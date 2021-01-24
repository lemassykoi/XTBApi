import logging.config
from datetime import date
import os.path
from XTBApi.api import *
from XTBApi.__version__ import __version__

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format':
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
        },
        'rotating': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'default',
            'filename': os.path.join(os.path.dirname(__file__), 'logs/' + str(date.today()) + '.log'),
            'when': 'midnight',
            'backupCount': 3
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'CRITICAL',
            'propagate': True
        },
        'XTBApi': {
            'handlers': ['rotating'],
            #'level': 'DEBUG'
            'level': 'INFO'
        }
    }
})
