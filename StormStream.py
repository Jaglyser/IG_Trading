import logging

from trading_ig import IGService, IGStreamService
from trading_ig.config import config
from trading_ig.lightstreamer import Subscription
import pandas as pd
import talib as ta
from functools import cached_property


class StormStream:
    counter = []
    prices = pd.DataFrame()

    open_long = []
    open_short = []

    current_bid = None
    current_offer = None

    ig_stream_service = None

    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        # logging.basicConfig(level=logging.DEBUG)

        ig_service = IGService(
            config.username, config.password, config.api_key, config.acc_type, acc_number=config.acc_number
        )

        self.ig_stream_service = IGStreamService(ig_service)
        self.ig_stream_service.create_session()
        # ig_stream_service.create_session(version='3')
        self.main()

    # A simple function acting as a Subscription listener

    def on_prices_update(self, item_update):
        df = pd.DataFrame(data=item_update)
        update_time = df.loc['UPDATE_TIME', :]
        hours, minutes, seconds = map(int, update_time['values'].split(":"))

        self.current_bid = df['values']['BID']
        self.current_offer = df['values']['OFFER']

        # print("price: %s " % item_update)
        print(
            "{stock_name:<19}: Time {UPDATE_TIME:<8} - "
            "Bid {BID:>5} - Ask {OFFER:>5}".format(
                stock_name=item_update["name"], **item_update["values"]
            )
        )
        self.minute_counter(df, minutes)

    def on_account_update(self, balance_update):
        print("balance: %s " % balance_update)

    def main(self):

        # Making a new Subscription in MERGE mode
        subscription_prices = Subscription(
            mode="MERGE",
            # items=["L1:CS.D.GBPUSD.CFD.IP", "L1:CS.D.USDJPY.CFD.IP"], # sample CFD epics
            # sample spreadbet epics
            items=["L1:IX.D.SPTRD.FWM2.IP"],
            fields=["UPDATE_TIME", "BID", "OFFER", "CHANGE", "MARKET_STATE"],
        )

        # Adding the "on_price_update" function to Subscription
        subscription_prices.addlistener(self.on_prices_update)

        # Registering the Subscription
        sub_key_prices = self.ig_stream_service.ls_client.subscribe(
            subscription_prices)

        # Making an other Subscription in MERGE mode
        subscription_account = Subscription(
            mode="MERGE", items=["ACCOUNT:" + config.acc_number], fields=["AVAILABLE_CASH"],
        )

        # Adding the "on_balance_update" function to Subscription
        subscription_account.addlistener(self.on_account_update)

        # Registering the Subscription
        sub_key_account = self.ig_stream_service.ls_client.subscribe(
            subscription_account)

        input(
            "{0:-^80}\n".format(
                "HIT CR TO UNSUBSCRIBE AND DISCONNECT FROM \
        LIGHTSTREAMER"
            )
        )

        # Disconnecting
        self.ig_stream_service.disconnect()

    def minute_counter(self, df, minutes):
        self.counter.append(minutes)
        if (len(self.counter) > 1 and self.counter[-1] != self.counter[-2]):
            print("A new minute arises")
            counter = []
            price_point = pd.DataFrame(
                {
                    "time": [df['values']['UPDATE_TIME']],
                    "offer": [df['values']['OFFER']],
                    "bid": [df['values']['BID']],
                }
            )
            self.create_price_list_point(price_point)

    def buy_condition(self):
        ma25 = ma25()
        if (self.prices[-1]['offer'] > ma25[-1] and self.prices[-2]['offer'] < ma25[-2]):
            open_position("LONG")

    """
    create similar sell position
    """

    @cached_property
    def ma25(self):
        return ta.SMA(self.prices)

    def create_price_list_point(self, price_point):
        self.prices = pd.concat([self.prices, price_point], ignore_index=True)
        print(self.prices)

    def mean_test(self):
        if (self.prices['offer'].count() > 10):
            mean = self.prices['offer'].mean()

            if (mean < self.current_offer + 10):
                self.test_long()

            if (mean > self.current_bid + 10):
                self.test_short()

    def test_long(self):
        if (len(self.open_long) == 0):
            self.open_position("LONG")

    def test_short(self):
        if (len(self.open_short) == 0):
            self.open_position("SHORT")

    def open_position(self, direction):
        response = self.ig_stream_service.create_open_position(
            currency_code="EUR",
            direction=direction,
            epic="IX.D.SPTRD.FWM2.IP",
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
        print("Order for {direction} openened \n {response}: ",
              response=response, direction=direction)

        if (direction == "LONG"):
            self.open_long.append(self.current_offer)
            self.open_short = []

        if (direction == "SHORT"):
            self.open_short.append(self.current_bid)
            self.open_long = []


if __name__ == "__main__":
    StormStream()
