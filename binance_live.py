import sys
import os
from ccxtbt import CCXTStore
import backtrader as bt
from datetime import datetime, timedelta
from strategies.boll import BollStrategy
from strategies.bollmacd import BollMACDStrategy
from utils.helper import init_env, get_env
import logging.config
import argparse
import time
from tools.telegram import Telegram

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(prog=sys.argv[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    # arg_parser.add_argument('-R', '--reversal', action="store_true", help='Whether to flip the transaction')
    arg_parser.add_argument('-C', '--clear', action="store_true", help='Whether to clear the status')
    arg_parser.add_argument('-S', '--stake', type=float, help='set stake', default=0.1)
    arg_parser.add_argument('-P', '--period', type=int, help='set period', default=92)
    arg_parser.add_argument('--critical_dif', type=float, help='DIF critical value', default=45)
    arg_parser.add_argument('-D', '--price_diff', type=int, help="stop loss price", default=200)
    arg_parser.add_argument('-L', '--limit_value', type=float, help="Set order price difference", default=100)
    args = arg_parser.parse_args(args=sys.argv[1:])

    status_file = "./status.json"
    if args.clear and os.path.exists(status_file):
        os.remove(status_file)

    init_env()
    logging.config.fileConfig("logging.ini")
    logging.Formatter.converter = time.gmtime  #utc
    cerebro = bt.Cerebro(quicknotify=True)

    # Add the strategy
    # cerebro.addstrategy(BollEMA, period_boll=200, period_ema=99, production=True)
    # cerebro.addstrategy(BollStrategy,
    #                     production=True,
    #                     period_boll=args.period,
    #                     price_diff=args.price_diff,
    #                     min_volume=args.min_volume,
    #                     max_volume=args.max_volume,
    #                     reversal=args.reversal)

    cerebro.addstrategy(
        BollMACDStrategy,
        production=True,
        period_boll=args.period,
        price_diff=args.price_diff,
        critical_dif=args.critical_dif,
        limit_value=args.limit_value,
    )

    cerebro.addanalyzer(Telegram)

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
    hist_start_date = datetime.utcnow() - timedelta(minutes=(args.period + 6) * 5)
    data = store.getdata(
        dataname='BTC/USDT',
        name="BTCUSDT",
        timeframe=bt.TimeFrame.Minutes,
        fromdate=hist_start_date,
        compression=5,
        ohlcv_limit=99999,
        drop_newest=True,
        # historical=True
    )

    # Add the feed
    cerebro.adddata(data)

    cerebro.broker.addcommissioninfo(bt.commissions.CommInfo_Futures_Perc(commission=0.05))
    cerebro.addsizer(bt.sizers.FixedSize, stake=args.stake)

    # Run the strategy
    cerebro.run()
