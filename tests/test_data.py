import sys
import os
from ccxtbt import CCXTStore, CCXTFeed
import backtrader as bt
from datetime import datetime, timedelta
from utils.helper import init_env, get_env


class PrintClose(bt.Strategy):

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt} {txt}')  # Print date and close

    def next(self):
        self.log(f'Close: {self.data0._name} {self.data0.close[0]:.3f}')
        self.log(f'Close: {self.data1._name} {self.data1.close[0]:.3f}')


if __name__ == '__main__':
    init_env()
    cerebro = bt.Cerebro()

    # Add the strategy
    cerebro.addstrategy(PrintClose)

    # Create our store
    config = { 'apiKey': get_env('B_APIKEY'), 'secret': get_env('B_SECRET'), 'enableRateLimit': True, 'options': { 'defaultType': 'spot'} }
    if get_env("PROXY") == '1':
        config['requests_trust_env'] = True

    # IMPORTANT NOTE - Kraken (and some other exchanges) will not return any values
    # for get cash or value if You have never held any BNB coins in your account.
    # So switch BNB to a coin you have funded previously if you get errors
    store = CCXTStore(exchange='binance', currency='USDT', config=config, retries=10, debug=False)
    c2 = { 'apiKey': get_env('B_APIKEY'), 'secret': get_env('B_SECRET'), 'enableRateLimit': True, 'options': { 'defaultType': 'future'} }
    if get_env("PROXY") == '1':
        c2['requests_trust_env'] = True
    store2 = CCXTStore(exchange='binance', currency='USDT', config=c2, retries=10, debug=False)

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

    # Get our data
    # Drop newest will prevent us from loading partial data from incomplete candles
    hist_start_date = datetime.utcnow() - timedelta(minutes=(210+6) * 5)
    data = CCXTFeed(dataname='ETH/USDT',
                    name="ETHUSDT",
                    timeframe=bt.TimeFrame.Minutes,
                    fromdate=hist_start_date,
                    compression=5,
                    ohlcv_limit=99999,
                    drop_newest=True,
                    exchange='binance',
                    currency='USDT',
                    config=config,
                    retries=10,
                    debug=False)

    data2 = CCXTFeed(dataname='BTC/USDT',
                     name="BTCUSDT",
                     timeframe=bt.TimeFrame.Minutes,
                     fromdate=hist_start_date,
                     compression=5,
                     ohlcv_limit=99999,
                     drop_newest=True,
                     exchange='binance',
                     currency='USDT',
                     config=c2,
                     retries=10,
                     debug=False)

    # Add the feed
    cerebro.adddata(data)
    cerebro.adddata(data2)

    # Run the strategy
    cerebro.run()