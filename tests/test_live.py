import sys
import os
import sys
sys.path.append('.')
from ccxtbt import CCXTStore
import backtrader as bt
from utils.helper import init_env, get_env
import logging.config
import time
from observers.telegram import Telegram
from datetime import datetime, timedelta


class OneBuy(bt.Strategy):

    def __init__(self):
        self.m = 0

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt} {txt}')  # Print date and close

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        msg = f'{dn} Data Status: {data._getstatusname(status)}'
        self.log(msg, datetime.utcnow())
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def notify_order(self, order):
        self.log(
            f"Order: {order.ordtypename()}, Status: {order.getstatusname()}, Price: {order.executed.price}, Size: {order.executed.size}, Alive: {order.alive()}"
        )

    def next(self):
        if not self.live_data: return
        if self.m == 0:
            data = self.datas[0]
            self.buy(data)
            self.m = 1
            self.log("buy")


if __name__ == '__main__':

    init_env()
    logging.config.fileConfig("logging.ini")
    logging.Formatter.converter = time.gmtime  #utc
    cerebro = bt.Cerebro()

    # Add the strategy
    cerebro.addstrategy(OneBuy)
    cerebro.addobserver(Telegram)

    # Create our store
    config = { 'apiKey': get_env('B_APIKEY'), 'secret': get_env('B_SECRET'), 'enableRateLimit': True }
    if get_env("PROXY") == '1':
        config['requests_trust_env'] = True

    # IMPORTANT NOTE - Kraken (and some other exchanges) will not return any values
    # for get cash or value if You have never held any BNB coins in your account.
    # So switch BNB to a coin you have funded previously if you get errors
    store = CCXTStore(exchange='binanceusdm', currency='USDT', config=config, retries=10, debug=False)

    # Get the broker and pass any kwargs if needed.
    # ----------------------------------------------
    # Broker mappings have been added since some exchanges expect different values
    # to the defaults. Case in point, Kraken vs Bitmex. NOTE: Broker mappings are not
    # required if the broker uses the same values as the defaults in CCXTBroker.
    broker_mapping = {
        'order_types': {
            bt.Order.Market: 'market',
            bt.Order.Limit: 'limit',
            bt.Order.Stop: 'stop-loss',  #stop-loss for kraken, stop for bitmex
            bt.Order.StopLimit: 'stop limit'
        },
        'mappings': {
            'closed_order': {
                'key': 'status',
                'value': 'closed'
            },
            'canceled_order': {
                'key': 'status',
                'value': 'canceled'
            }
        }
    }

    broker = store.getbroker(broker_mapping=broker_mapping)
    cerebro.setbroker(broker)

    # Get our data
    # Drop newest will prevent us from loading partial data from incomplete candles
    hist_start_date = datetime.utcnow() - timedelta(minutes=(220 + 6) * 5)
    data = store.getdata(
        dataname='ETC/USDT',
        name="ETCUSDT",
        timeframe=bt.TimeFrame.Minutes,
        fromdate=hist_start_date,
        compression=5,
        ohlcv_limit=99999,
        drop_newest=True,
        # historical=True
    )

    # Add the feed
    cerebro.adddata(data)

    cerebro.broker.setcommission(commission=0.0004, margin=0.1, mult=1.0)
    cerebro.addsizer(bt.sizers.FixedSize, stake=1)

    # Run the strategy
    cerebro.run()