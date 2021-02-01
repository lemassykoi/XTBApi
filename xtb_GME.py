#!/usr/bin/env python3
# adaptation du script XTB pour #WSB $GME
##
debug = 1               ## DEBUG ENABLED OR DISABLED

from XTBApi.api import *
import time
import datetime as dt
import requests
import sys, traceback
from os import system

##
## SPINNER FUNC
##
import threading
import itertools

class Spinner:

    def __init__(self, message, delay=0.05):
        self.spinner = itertools.cycle(['-', '\\', '|', '/'])   # horaire
        self.delay = delay
        self.busy = False
        self.spinner_visible = False
        sys.stdout.write(message)

    def write_next(self):
        with self._screen_lock:
            if not self.spinner_visible:
                sys.stdout.write(next(self.spinner))
                self.spinner_visible = True
                sys.stdout.flush()

    def remove_spinner(self, cleanup=False):
        with self._screen_lock:
            if self.spinner_visible:
                sys.stdout.write('\b')
                self.spinner_visible = False
                if cleanup:
                    sys.stdout.write(' ')       # overwrite spinner with blank
                    sys.stdout.write('\r')      # move to next line
                sys.stdout.flush()

    def spinner_task(self):
        while self.busy:
            self.write_next()
            time.sleep(self.delay)
            self.remove_spinner()

    def __enter__(self):
        if sys.stdout.isatty():
            self._screen_lock = threading.Lock()
            self.busy = True
            self.thread = threading.Thread(target=self.spinner_task)
            self.thread.start()

    def __exit__(self, exception, value, tb):
        if sys.stdout.isatty():
            self.busy = False
            self.remove_spinner(cleanup=True)
        else:
            sys.stdout.write('\r')
##

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def NotifyLogDebug(Message):
    LOGGER.debug(Message)
    requests.get('https://api.telegram.org/bot' + TG_token + '/sendMessage?chat_id=' + TG_chat_id + '&text=' + Message)

def NotifyLogInfo(Message):
    LOGGER.info(Message)
    requests.get('https://api.telegram.org/bot' + TG_token + '/sendMessage?chat_id=' + TG_chat_id + '&text=' + Message)

def NotifyLogWarning(Message):
    LOGGER.warning(Message)
    requests.get('https://api.telegram.org/bot' + TG_token + '/sendMessage?chat_id=' + TG_chat_id + '&text=' + Message)

def NotifyLogError(Message):
    LOGGER.error(Message)
    requests.get('https://api.telegram.org/bot' + TG_token + '/sendMessage?chat_id=' + TG_chat_id + '&text=' + Message)

def NotifyLogCritical(Message):
    LOGGER.critical(Message)
    requests.get('https://api.telegram.org/bot' + TG_token + '/sendMessage?chat_id=' + TG_chat_id + '&text=' + Message)

def NormalExit():
    client.logout()
    LOGGER.info('Logged Out : Script Exited Normally')
    sys.exit()

if debug == 1: print(f"{bcolors.WARNING}  DEBUG IS ON{bcolors.ENDC}")

## LOGGER LEVEL 
LOGGER.setLevel(logging.INFO)
##
symbol = 'GME.US_9'
# NOKIA.FI_9
# BB.US
# TSLA.US_9
xtb_login  = '1234567'
xtb_pass   = '***************'
TG_chat_id = '123456789'
TG_token   = '1234567890:***********************************'
##
min_objectif_amount_sell = 69420
##
version = '20210201-0448'

## INIT XTB CONNEXION
NotifyLogInfo('Starting XTB GME WSB')
client = Client()
client.login(xtb_login, xtb_pass, mode='real')

## Check if Market is Opened or Closed # return an array with 'symbol : Bool'
def isOpened():
    is_opened = client.check_if_market_open([symbol])
    if is_opened[symbol] == False:
        LOGGER.warning('  ==MARKET IS CLOSED==')
        return False;
    else:
        return True;

def Routine():
    ## get open positions
    openpositions = client.get_trades()
    i = 0
    j = 0
    for keys in openpositions:
        i = i + 1
        if keys['symbol'] == symbol:
            j = j + 1
            trade_close_price       = keys['close_price']
            trade_close_time        = keys['close_time']
            trade_close_timeString  = keys['close_timeString']
            trade_closed            = keys['closed']
            trade_commission        = keys['commission']
            trade_digits            = keys['digits']
            trade_open_price        = keys['open_price']
            trade_open_time         = keys['open_time']
            trade_open_timeString   = keys['open_timeString']
            trade_order             = keys['order']
            trade_profit            = keys['profit']
            trade_nominal_value     = keys['nominalValue']
            trade_stoploss          = keys['sl']
            trade_spread            = keys['spread']
            trade_storage           = keys['storage']
            trade_traded_symbol     = keys['symbol']
            trade_taxes             = keys['taxes']
            trade_timestamp         = keys['timestamp']
            trade_takeprofit        = keys['tp']
            trade_volume            = keys['volume']
            ## calculs
            str_roll_fees = str(trade_storage).translate({ord(i):None for i in '-'})
            roll_fees = float(str_roll_fees)
            net_profit = trade_profit - roll_fees
            min_price_to_sell = trade_open_price + roll_fees
            diff_sell_price = trade_close_price - min_price_to_sell
            total_local_fiat = trade_nominal_value + trade_profit
            print('===================================================================================')
            print(' Open Price   : ', trade_open_price)
            print(' + Roll Fees  : ', min_price_to_sell)
            
            ## BUY Order
            if keys['cmd'] == 0:
                diff_percent_sell = diff_sell_price / trade_open_price * 100
                print(' Close Price  : ', trade_close_price)
                print(' Difference % : ', round(diff_percent_sell, 2), '%')
                print(' Difference $ : $', diff_sell_price)
                print(' Net Profit   : €', trade_profit)
                print('')
                print(' Total Fiat   : €', total_local_fiat)
                ## check if profit OK
                if total_local_fiat >= min_objectif_amount_sell:
                    print(' Objectif atteint !!')
                    limit = min_objectif_amount_sell * 1.3
                    ## close trade
                    #client.trade_transaction(symbol, trade_order, 0, trade_volume, stop_loss=min_objectif_amount_sell, take_profit=limit)
                    #client.close_trade(trade_order)
                    #client.close_trade([trade_order])
        print('')

def handle_exception():
    NotifyLogError("Exception handled on " + symbol + " ! Restarting...")
    main()

def main():
    while isOpened() == False:
        try:
            with Spinner('  Market Closed - Waiting...   '):
                time.sleep(30)
        except KeyboardInterrupt:
            print("")
            print(f"{bcolors.WARNING}Shutdown requested by Operator... Exiting !{bcolors.ENDC}")
            print("")
            NormalExit()
        except Exception:
            traceback.print_exc(file=sys.stdout)
            LOGGER.error("EXCEPTION Check Marjet on Bot XTB " + symbol + " ! Bot Stopped.")
            handle_exception()

    NotifyLogInfo('  ==MARKET OPEN !==')

    while True:
        try:
            Routine()
            print(f"{bcolors.HEADER}==================================================================================={bcolors.ENDC}")
            with Spinner('  Sleep... Zzzzz... '):
                time.sleep(4)
        except KeyboardInterrupt:
            print("")
            print(f"{bcolors.WARNING}Shutdown requested by Operator... Exiting !{bcolors.ENDC}")
            print("")
            NormalExit()
        except Exception:
            traceback.print_exc(file=sys.stdout)
            LOGGER.error("EXCEPTION on Bot XTB " + symbol + " ! Bot Stopped.")
            handle_exception()

if __name__ == "__main__":
    main()

NormalExit()
