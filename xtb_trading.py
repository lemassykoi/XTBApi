#!/usr/bin/env python3
# adaptation du script FXCM pour XTB
##
debug = 1               ## DEBUG ENABLED OR DISABLED
from XTBApi.api import *
import time
import pandas as pd
import datetime as dt
import talib.abstract as ta

## Maths modules
import pyti.bollinger_bands as bb
from pyti.relative_strength_index import relative_strength_index as rsi
from pyti.bollinger_bands import upper_bollinger_band as ubb
from pyti.bollinger_bands import middle_bollinger_band as mbb
from pyti.bollinger_bands import lower_bollinger_band as lbb
from pyti.bollinger_bands import percent_bandwidth as percent_b
import requests
import sys, traceback
from os import system
from pprint import pprint

##
## SPINNER FUNC
##
import threading
import itertools

class Spinner:

    def __init__(self, message, delay=0.05):
        #self.spinner = itertools.cycle(['-', '/', '|', '\\'])  # anti horaire
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
pricedata = None
timeframe = 'm1'                                 ## TIMEFRAME (m1, m5,  m15,  m30,  H1,H2,H3,H4,H6,H8,D1,    W1,     M1)
mn_timeframe = 60                                ## Minutes   (60, 300, 900, 1800, 3600,     14400,   86400, 604800, 2592000)
numberofcandles = 300   ## minimum 35 pour calcul MACD
symbol = 'EURUSD'
xtb_login = '1234567'
xtb_pass  = 'myComplexPassword'
TG_chat_id='123456789'
TG_token='1234567890:aBcDeFgHiJkLmNoPqRsTuVwXyZ012345678'
amount = 0.1
objectif_percent_sell = 1.02
objectif_percent_buy = 0.98
min_objectif_amount_sell = 50
trailing_step = 150
##
rsi_periods = 14
bb_periods = 20
bb_standard_deviations = 2.0
upper_rsi = 72
lower_rsi = 28
version = '20210127-0110'

## INIT XTB CONNEXION
NotifyLogInfo('Starting XTB Bot Tests')
client = Client()
client.login(xtb_login, xtb_pass, mode='real')

## Check if Market is Opened or Closed # return an array with 'symbol : Bool'
is_opened = client.check_if_market_open([symbol])
if is_opened[symbol] == False:
    print('==MARKET IS CLOSED==')
    NormalExit()

# This function runs once at the beginning of the strategy to run initial one-time processes
def Prepare():
    global pricedata

    if debug == 1: print(f"{bcolors.HEADER}Requesting Initial Price Data...{bcolors.ENDC}")
    d = client.get_lastn_candle_history([symbol], mn_timeframe, numberofcandles)
    pricedata = pd.DataFrame(data=d)
    if debug == 1: print(f"{bcolors.OKGREEN}Initial Price Data Received...{bcolors.ENDC}")
    print('')
    ## DEBUG LIGHT
    #print(pricedata)
    ## DEBUG FULL
    #print(pricedata.to_string())
    print('')

# Get latest close bar prices and run Update() function every close of bar/candle
def StrategyHeartBeat():
    while True:
        currenttime = dt.datetime.now()
        if timeframe == "m1" and currenttime.second == 0 and getLatestPriceData():
            Update()
        elif timeframe == "m5" and currenttime.second == 0 and currenttime.minute % 5 == 0 and getLatestPriceData():
            Update()
            with Spinner('Waiting for m5 bar...'):
                time.sleep(240)
        elif timeframe == "m15" and currenttime.second == 0 and currenttime.minute % 15 == 0 and getLatestPriceData():
            Update()
            with Spinner('Waiting for m15 bar...'):
                time.sleep(840)
        elif timeframe == "m30" and currenttime.second == 0 and currenttime.minute % 30 == 0 and getLatestPriceData():
            Update()
            with Spinner('Waiting for m30 bar...'):
                time.sleep(1740)
        elif currenttime.second == 0 and currenttime.minute == 0 and getLatestPriceData():
            Update()
            with Spinner('Waiting for H1 bar...'):
                time.sleep(3540)
        with Spinner('Waiting for m1 bar...'):
            time.sleep(1)

# Returns True when pricedata is properly updated
def getLatestPriceData():
    global pricedata

    # Normal operation will update pricedata on first attempt
    d = client.get_lastn_candle_history([symbol], mn_timeframe, numberofcandles)
    new_pricedata = pd.DataFrame(data=d)
    if new_pricedata['timestamp'][len(new_pricedata['timestamp'])-1] != pricedata['timestamp'][len(pricedata['timestamp'])-1]:
        pricedata = new_pricedata
        return True

    counter = 0
    # If data is not available on first attempt, try up to 6 times to update pricedata
    while new_pricedata['timestamp'][len(new_pricedata['timestamp'])-1] == pricedata['timestamp'][len(pricedata['timestamp'])-1] and counter < 6:
        print(f"{bcolors.BOLD}No updated prices found, trying again in 10 seconds...{bcolors.ENDC}")
        print("")
        counter+=1
        with Spinner('Still waiting for next bar...'):
            time.sleep(10)
        d = client.get_lastn_candle_history([symbol], mn_timeframe, numberofcandles)
        new_pricedata = pd.DataFrame(data=d)
    if new_pricedata['timestamp'][len(new_pricedata['timestamp'])-1] != pricedata['timestamp'][len(pricedata['timestamp'])-1]:
        pricedata = new_pricedata
        return True
    else:
        return False

# Returns true if stream1 crossed over stream2 in most recent candle, stream2 can be integer/float or data array
def crossesOver(stream1, stream2):
    # If stream2 is an int or float, check if stream1 has crossed over that fixed number
    if isinstance(stream2, int) or isinstance(stream2, float):
        if stream1[len(stream1)-1] <= stream2:
            return False
        else:
            if stream1[len(stream1)-2] > stream2:
                return False
            elif stream1[len(stream1)-2] < stream2:
                return True
            else:
                x = 2
                while stream1[len(stream1)-x] == stream2:
                    x = x + 1
                if stream1[len(stream1)-x] < stream2:
                    return True
                else:
                    return False
    # Check if stream1 has crossed over stream2
    else:
        if stream1[len(stream1)-1] <= stream2[len(stream2)-1]:
            return False
        else:
            if stream1[len(stream1)-2] > stream2[len(stream2)-2]:
                return False
            elif stream1[len(stream1)-2] < stream2[len(stream2)-2]:
                return True
            else:
                x = 2
                while stream1[len(stream1)-x] == stream2[len(stream2)-x]:
                    x = x + 1
                if stream1[len(stream1)-x] < stream2[len(stream2)-x]:
                    return True
                else:
                    return False

# Returns true if stream1 crossed under stream2 in most recent candle, stream2 can be integer/float or data array
def crossesUnder(stream1, stream2):
    # If stream2 is an int or float, check if stream1 has crossed under that fixed number
    if isinstance(stream2, int) or isinstance(stream2, float):
        if stream1[len(stream1)-1] >= stream2:
            return False
        else:
            if stream1[len(stream1)-2] < stream2:
                return False
            elif stream1[len(stream1)-2] > stream2:
                return True
            else:
                x = 2
                while stream1[len(stream1)-x] == stream2:
                    x = x + 1
                if stream1[len(stream1)-x] > stream2:
                    return True
                else:
                    return False
    # Check if stream1 has crossed under stream2
    else:
        if stream1[len(stream1)-1] >= stream2[len(stream2)-1]:
            return False
        else:
            if stream1[len(stream1)-2] < stream2[len(stream2)-2]:
                return False
            elif stream1[len(stream1)-2] > stream2[len(stream2)-2]:
                return True
            else:
                x = 2
                while stream1[len(stream1)-x] == stream2[len(stream2)-x]:
                    x = x + 1
                if stream1[len(stream1)-x] > stream2[len(stream2)-x]:
                    return True
                else:
                    return False

# This function places a market order in the direction BuySell, "B" = Buy, "S" = Sell, uses symbol, amount, stop, limit
def enter(BuySell, stop, limit):
    volume = amount
    order = 'buy'
    if BuySell == "S":
        order = 'sell'
    try:
        msg = '   Opening tradeID for symbol ' + symbol
        NotifyLogInfo(msg)
        opentrade = client.open_trade(order, symbol, amount)
    except:
        msg = '   Error Opening Trade.'
        NotifyLogError(msg)
    else:
        msg = '   Trade Opened Successfully.'
        LOGGER.info(msg)

# This function closes all positions that are in the direction BuySell, "B" = Close All Buy Positions, "S" = Close All Sell Positions, uses symbol
# def exit(BuySell=None):
    # openpositions = con.get_open_positions(kind='list')
    # isbuy = True
    # if BuySell == "S":
        # isbuy = False
    # for position in openpositions:
        # if position['currency'] == symbol:
            # if BuySell is None or position['isBuy'] == isbuy:
                # msg = '   Closing tradeID : ' + trade_order
                # NotifyLogInfo(msg)
                # try:
                    # closetrade = con.close_trade(trade_id=position['tradeId'], amount=position['amountK'])
                # except:
                    # msg = "   Error Closing Trade."
                    # NotifyLogError(msg)
                # else:
                    # msg = "   Trade Closed Successfully."
                    # LOGGER.info(msg)

# Returns number of Open Positions for symbol in the direction BuySell, returns total number of both Buy and Sell positions if no direction is specified
def countOpenTrades(BuySell=None):
    openpositions = client.get_trades()
    counter = 0
    isbuy = 0
    if BuySell == "S":
        isbuy = 1
    for keys in openpositions:
        if keys['symbol'] == symbol:
            if BuySell is None or keys['cmd'] == isbuy:
                counter+=1
    return counter

def Update():
    print(f"{bcolors.HEADER}==================================================================================={bcolors.ENDC}")
    print(f"{bcolors.BOLD}" + str(dt.datetime.now()) + f"{bcolors.ENDC}" + "     " + timeframe + " Bar Closed - Running Update Function...")
    print("Version        : " + f"{bcolors.BOLD}" + version + '         ' + sys.argv[0] + f"{bcolors.ENDC}")
    print("Symbol         : " + f"{bcolors.BOLD}" + symbol + f"{bcolors.ENDC}")
    
    # Calculate Indicators
    macd = ta.MACD(pricedata['close'])
    pricedata['cci'] = ta.CCI(pricedata['high'],pricedata['low'],pricedata['close'])
    iBBUpper = bb.upper_bollinger_band(pricedata['close'], bb_periods, bb_standard_deviations)
    iBBMiddle = bb.middle_bollinger_band(pricedata['close'], bb_periods, bb_standard_deviations)
    iBBLower = bb.lower_bollinger_band(pricedata['close'], bb_periods, bb_standard_deviations)
    iRSI = rsi(pricedata['close'], rsi_periods)
    
    # Declare simplified variable names for most recent close candle
    pricedata['macd'] = macd[0]
    pricedata['macdsignal'] = macd[1]
    pricedata['macdhist'] = macd[2]
    BBUpper = iBBUpper[len(iBBUpper)-1]
    BBMiddle = iBBMiddle[len(iBBMiddle)-1]
    BBLower = iBBLower[len(iBBLower)-1]
    close_price = pricedata['close'][len(pricedata)-1]
    last_close_price = pricedata['close'][len(pricedata)-2]
    macd_now = pricedata['macd'][len(pricedata)-1]
    macdsignal = pricedata['macdsignal'][len(pricedata)-1]
    macdhist = pricedata['macdhist'][len(pricedata)-1]
    cci = pricedata['cci'][len(pricedata)-1]
    rsi_now = iRSI[len(iRSI)-1]

    ## DEBUG FULL
    #print(pricedata.to_string())

    # Print Price/Indicators
    if close_price > last_close_price:
        print(f"Close Price    : {bcolors.OKGREEN}" + str(close_price) + f"{bcolors.ENDC}")
    elif close_price < last_close_price:
        print(f"Close Price    : {bcolors.FAIL}" + str(close_price) + f"{bcolors.ENDC}")
    else:
        print(f"Close Price    : {bcolors.OKCYAN}" + str(close_price) + f"{bcolors.ENDC}")
    print("MACD           : " + str(macd_now))
    print("Signal MACD    : " + str(macdsignal))
    print("MACD History   : " + str(macdhist))
    if cci <= -50:
        print(f"{bcolors.OKGREEN}CCI            : " + str(cci) + f"{bcolors.ENDC}")
    elif cci >= 100:
        print(f"{bcolors.FAIL}CCI            : " + str(cci) + f"{bcolors.ENDC}")
    else:
        print(f"{bcolors.OKCYAN}CCI            : " + str(cci) + f"{bcolors.ENDC}")
    print("RSI            : " + str(rsi_now))
    
    # Change Any Existing Trades' Limits to Middle Bollinger Band
    if countOpenTrades()>0:
        openpositions = client.get_trades()
        for position in openpositions:
            if position['symbol'] == symbol and ((position['cmd'] == 0) or (position['cmd'] == 1)):
                NotifyLogInfo("Changing Limit for tradeID: " + str(position['order']))
                try:
                    NotifyLogInfo('client.trade_transaction')
                    #client.trade_transaction(symbol, position['cmd'], trans_type, volume, stop_loss=0, take_profit=0)
                except:
                    NotifyLogError("       Error Changing Limit :(")
                else:
                    print("       Limit Changed Successfully. ;)")

    # # Entry Logic
    # if countOpenTrades('B') == 0:
        # if ((crossesOver(pricedata['macd'], macdsignal) & (cci <= -50.0))):
            # print(f"{bcolors.OKGREEN}   BUY SIGNAL ! MACD{bcolors.ENDC}")
            # NotifyLogInfo("       Opening " + symbol + " Buy Trade... MACD")
            # stop = round((pricedata['close'][len(pricedata['close'])-1] * buy_stop_loss), 5)
            # limit = round((pricedata['close'][len(pricedata['close'])-1] * buy_take_profit), 5)
            # #enter('B', stop, limit)
        # elif (crossesOver(iRSI, lower_rsi) and close_price < BBLower):
            # print(f"{bcolors.OKGREEN}   BUY SIGNAL ! RSI{bcolors.ENDC}")
            # NotifyLogInfo("       Opening " + symbol + " Buy Trade... RSI")
            # #stop = pricedata['close'][len(pricedata['close'])-1] - (BBMiddle - pricedata['close'][len(pricedata['close'])-1])
            # stop = round((pricedata['close'][len(pricedata['close'])-1] * buy_stop_loss), 5)
            # limit = BBMiddle
            # #enter('B', stop, limit)

    # if (countOpenTrades('S') == 0 and close_price > BBUpper):
        # if crossesUnder(iRSI, upper_rsi):
            # print(f"{bcolors.FAIL}   SELL SIGNAL ! RSI{bcolors.ENDC}")
            # NotifyLogInfo('       Opening ' + symbol + ' Sell Trade... RSI')
            # stop = pricedata['close'][len(pricedata['close'])-1] + (pricedata['close'][len(pricedata['close'])-1] - BBMiddle)
            # limit = BBMiddle
            # #enter('S', stop, limit)
        # elif (crossesUnder(pricedata['macd'], macdsignal) and macd_now > 0):
            # print(f"{bcolors.FAIL}   SELL SIGNAL ! MACD{bcolors.ENDC}")
            # NotifyLogInfo('       Opening ' + symbol + ' Sell Trade... MACD')
            # stop = pricedata['close'][len(pricedata['close'])-1] + (pricedata['close'][len(pricedata['close'])-1] - BBMiddle)
            # limit = BBMiddle
            # #enter('S', stop, limit)

    # # Exit Logic
    # if countOpenTrades('B') > 0:
        # if ((crossesUnder(pricedata['macd'], macdsignal) & (cci >= 100.0))):
            # NotifyLogInfo('       Closing ' + symbol + ' Buy Trade(s)... Reason : MACD')
            # #exit('B')
        # elif (crossesUnder(iRSI, upper_rsi)):
            # NotifyLogInfo('       Closing ' + symbol + ' Buy Trade(s)... Reason : RSI')
            # #exit('B')
    # if countOpenTrades('S') > 0:
        # if (iRSI[len(iRSI)-1] < lower_rsi):
            # NotifyLogInfo('       Closing ' + symbol + ' SELL Trade because of RSI')
            # #exit('S')
        # elif (close_price < BBMiddle):
            # NotifyLogInfo('       Closing ' + symbol + ' SELL Trade because of BBMiddle')
            # #exit('S')

    print(f"{bcolors.BOLD}" + str(dt.datetime.now()) + f"{bcolors.ENDC}" + "     " + timeframe + " Update Function Completed.\n")

def handle_exception():
    NotifyLogError("Exception handled on " + symbol + " ! Restarting...")
    main()

## STARTING TRADING LOOP
def main():
    try:
        Prepare()
        StrategyHeartBeat()
    except KeyboardInterrupt:
        print("")
        print(f"{bcolors.WARNING}Shutdown requested by Operator... Exiting !{bcolors.ENDC}")
        print("")
        NormalExit()
    except Exception:
        traceback.print_exc(file=sys.stdout)
        LOGGER.error("EXCEPTION on Bot XTB " + symbol + " ! Bot Stopped.")
        handle_exception()
    except ServerError:
        traceback.print_exc(file=sys.stdout)
        NotifyLogError("SERVER ERROR on Bot XTB " + symbol + " ! Bot Stopped.")
        handle_exception()

if __name__ == "__main__":
    main()

NormalExit()
