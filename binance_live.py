import sys
import os
from ccxtbt import CCXTStore
import backtrader as bt
from datetime import datetime, timedelta
from strategies.bollema import BollEMA
from strategies.boll import BollStrategy
from utils.helper import init_env, get_env
import logging.config
import argparse
import time

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(prog=sys.argv[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    arg_parser.add_argument('-R', '--reversal', action="store_true", help='Whether to flip the transaction')
    arg_parser.add_argument('-C', '--clear', action="store_true", help='Whether to clear the status')
    arg_parser.add_argument('-S', '--stake', type=int, help='set stake', default=1)
    arg_parser.add_argument('-P', '--period', type=int, help='set period', default=220)
    arg_parser.add_argument('-X', '--slope', type=float, help='set slope', default=0.09)
    args = arg_parser.parse_args(args=sys.argv[1:])

    if args.clear:
        os.remove("./status.json")

    init_env()
    logging.config.fileConfig("logging.ini")
    logging.Formatter.converter = time.gmtime  #utc
    cerebro = bt.Cerebro()

    # Add the strategy
    # cerebro.addstrategy(BollEMA, period_boll=200, period_ema=99, production=True)
    cerebro.addstrategy(BollStrategy, production=True, period_boll=args.period, slope=args.slope, reversal=args.reversal)

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
    hist_start_date = datetime.utcnow() - timedelta(minutes=args.period*5)
    data = store.getdata(
        dataname='ETH/USDT',
        name="ETHUSDT",
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
    cerebro.addsizer(bt.sizers.FixedSize, stake=args.stake)

    # Run the strategy
    cerebro.run()