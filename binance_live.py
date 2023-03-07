from ccxtbt import CCXTStore
import backtrader as bt
from datetime import datetime, timedelta
from strategies.bollema import BollEMA
from strategies.boll import BollStrategy
from strategies.boll_reverser import BollReverser
from utils.helper import init_env, get_env
import logging.config


class TestStrategy(bt.Strategy):

    def __init__(self):

        self.sma = bt.indicators.SMA(self.data, period=21)

    def next(self):

        # Get cash and balance
        # New broker method that will let you get the cash and balance for
        # any wallet. It also means we can disable the getcash() and getvalue()
        # rest calls before and after next which slows things down.

        # NOTE: If you try to get the wallet balance from a wallet you have
        # never funded, a KeyError will be raised! Change LTC below as approriate
        if self.live_data:
            # cash, value = self.broker.get_wallet_balance("BTC")
            cash, value = self.broker.get_balance()
        else:
            # Avoid checking the balance during a backfill. Otherwise, it will
            # Slow things down.
            cash = 'NA'
            value = 'NA'
            # return  # 仍然处于历史数据回填阶段，不执行逻辑，返回

        for data in self.datas:

            print('{} - {} | Cash {} | Value {} | O: {} H: {} L: {} C: {} V:{} SMA:{}'.format(data.datetime.datetime(), data._name, cash, value, data.open[0],
                                                                                              data.high[0], data.low[0], data.close[0], data.volume[0],
                                                                                              self.sma[0]))

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.utcnow()
        msg = 'Data Status: {}'.format(data._getstatusname(status))
        print(dt, dn, msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False


if __name__ == '__main__':
    init_env()
    logging.config.fileConfig("logging.ini")
    cerebro = bt.Cerebro()

    # Add the strategy
    # cerebro.addstrategy(TestStrategy)
    # cerebro.addstrategy(BollEMA, period_boll=200, period_ema=99, production=True)
    # cerebro.addstrategy(BollStrategy, production=True)
    cerebro.addstrategy(BollReverser)

    # Create our store
    config = {
        'apiKey': get_env('B_APIKEY'),
        'secret': get_env('B_SECRET'),
        'enableRateLimit': True,
    }
    if get_env("PROXY") == '1':
        # config['trust_env'] = True
        # config['aiohttp_trust_env'] = True
        config['requests_trust_env'] = True

    # IMPORTANT NOTE - Kraken (and some other exchanges) will not return any values
    # for get cash or value if You have never held any BNB coins in your account.
    # So switch BNB to a coin you have funded previously if you get errors
    store = CCXTStore(exchange='binance', currency='USDT', config=config, retries=100, debug=False)

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
    hist_start_date = datetime.utcnow() - timedelta(minutes=520)
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

    # cerebro.broker.setcommission(commission=0.0004, margin=0.1, mult=1.0)
    # cerebro.addsizer(bt.sizers.FixedSize, stake=2)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=80)

    # Run the strategy
    cerebro.run()