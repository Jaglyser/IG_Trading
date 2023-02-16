import time
import sys
import traceback
import logging
import pandas as pd
import talib as ta
import numpy as np
import openpyxl
import matplotlib.pyplot as plt


from trading_ig import IGService, IGStreamService
from trading_ig.config import config
from trading_ig.lightstreamer import Subscription

closing_prices = []
counter = []
values = []
long = []

index = 0

open_order = []
openLong = []
openShort = []

totalOrder = 0

longSignal = False
shortSignal = False


epic = 'IX.D.DAX.IFMM.IP'
ig_service6 = IGService(config.username, config.password, config.api_key, config.acc_type)
ig_service6.create_session()

#account_info = ig_service.switch_account(config.acc_number, False) # not necessary
#print(account_info)




#epic = 'CS.D.EURUSD.MINI.IP'
resolution = '1min'
num_points = 40
response = ig_service6.fetch_historical_prices_by_epic_and_num_points(epic, resolution, num_points)
df_ask = (response['prices']['ask'] + response['prices']['bid'])/2
open_pos = ig_service6.fetch_open_positions()

print(len(open_pos))
print(len(openLong))
print(len(openShort))


values = df_ask['Close']

values = values.to_numpy()

stopLong = 0
stopShort = 0

noLongPos = True;
noShortPos = True;



# A simple function acting as a Subscription listener
def on_prices_update(item_update):
    # print("price: %s " % item_update)
    """
    print(
        "{stock_name:<19}: Time {UPDATE_TIME:<8} - "
        "Bid {BID:>5} - Ask {OFFER:>5}".format(
            stock_name=item_update["name"], **item_update["values"]
        )
    )"""

    df = pd.DataFrame(data=item_update)
    offer = df.loc['OFFER', :]
    bid = df.loc['BID', :]
    update_time = df.loc['UPDATE_TIME', :]
    #print("Price: ", offer['values'], end=" ")
    #print("Time: ", update_time['values'])
    hours, minutes, seconds = map(int, update_time['values'].split(":"))

    global closing_prices
    global counter
    global values
    global long
    global open_order
    global longSignal
    global shortSignal
    global totalOrder
    global openLong
    global openShort
    global stopLong
    global stopShort
    global outsideRange
    global noLongPos
    global noShortPos


    price = (float(offer['values'])+float(bid['values']))/2
    closing_prices.append(price)


    counter.append(minutes)
    n = len(counter)
    i = len(closing_prices)
    v = len(openLong) - 1
    u = len(openShort) - 1
    row = 50


    # find out when a minute has passed and ads the closing price
    if n > 5:
        if counter[n-1] != counter[n-2]:
            print("Program is still running")
            print("Time: ", update_time['values'])
            values = np.append(values, closing_prices[i - 2])
            mean = np.mean(values)
            meanv = np.append(mean)
            print("Mean: ", mean)

            counter = []
            closing_prices = []

            if len(meanv) > 2:
                meandiff = meanv[len(meanv) - 1] - meanv[len(meanv) - 2]

                # open long position
                if(meandiff > range(0.9)) and noLongPos:
                    open_position("BUY")
                    if noShortPos:
                        noLongPos = False

                # open short position
                if(meandiff < range(-0.9)) and noShortPos:
                    open_position("SELL")
                    if noLongPos:
                        noShortPos = False

                # close long position
                if meandiff < range(0.5):
                    open_position("SELL")
                    noLongPos = True

                # close short position
                if meandiff > range(-0.5):
                    open_position("BUY")
                    noShortPos = True






def on_account_update(balance_update):
    print("balance: %s " % balance_update)


def main():
    logging.basicConfig(level=logging.INFO)
    # logging.basicConfig(level=logging.DEBUG)

    ig_service = IGService(
        config.username, config.password, config.api_key, config.acc_type
    )

    ig_stream_service = IGStreamService(ig_service)
    ig_session = ig_stream_service.create_session()
    # Ensure configured account is selected
    accounts = ig_session[u"accounts"]
    for account in accounts:
        if account[u"accountId"] == config.acc_number:
            accountId = account[u"accountId"]
            break
        else:
            print("Account not found: {0}".format(config.acc_number))
            accountId = None
    ig_stream_service.connect(accountId)
    # Making a new Subscription in MERGE mode
    subscription_prices = Subscription(
        mode="MERGE",
        items=["L1:IX.D.DAX.IFMM.IP"],
        fields=["UPDATE_TIME", "BID", "OFFER", "CHANGE", "MARKET_STATE"],
    )
    # adapter="QUOTE_ADAPTER")

    # Adding the "on_price_update" function to Subscription
    subscription_prices.addlistener(on_prices_update)

    # Registering the Subscription
    sub_key_prices = ig_stream_service.ls_client.subscribe(subscription_prices)

    # Making an other Subscription in MERGE mode
    subscription_account = Subscription(
        mode="MERGE", items=["ACCOUNT:" + accountId], fields=["AVAILABLE_CASH"],
    )
    #    #adapter="QUOTE_ADAPTER")

    # Adding the "on_balance_update" function to Subscription
    subscription_account.addlistener(on_account_update)

    # Registering the Subscription
    sub_key_account = ig_stream_service.ls_client.subscribe(subscription_account)

    input(
        "{0:-^80}\n".format(
            "HIT CR TO UNSUBSCRIBE AND DISCONNECT FROM \
    LIGHTSTREAMER"
        )
    )

    # Disconnecting
    ig_stream_service.disconnect()

# function to open position
def open_position(direction):
    response = ig_service6.create_open_position(
        currency_code="EUR",
        direction=direction,
        epic="IX.D.DAX.IFMM.IP",
        expiry="-",
        force_open="false",
        guaranteed_stop="false",
        level=None,
        limit_distance=None,
        limit_level=None,
        order_type="MARKET",
        size="1",
        quote_id=None,
        stop_distance=None,
        stop_level=None,
        trailing_stop_increment=None,
        trailing_stop='false')


if __name__ == "__main__":
    main()