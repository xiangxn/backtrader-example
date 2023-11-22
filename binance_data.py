from datetime import datetime
import backtrader as bt
import logging.config
import time

from data.dataset import CustomDataset
from strategies.abbration import Abbration
from strategies.bollkdj import BOLLKDJStrategy
from strategies.bollema import BollEMA
from strategies.boll import BollStrategy
from strategies.bollmacd import BollMACDStrategy
from strategies.macdkdj import MACDKDJStrategy
from strategies.boll_reverser import BollReverser
from utils.helper import init_env


class PrintClose(bt.Strategy):

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt} {txt}')  # Print date and close

    def next(self):
        self.log('Close: %.3f' % self.data0.close[0])


def float_range(start, stop, steps):
    return [start + float(i) * (stop-start) / (float(steps) - 1) for i in range(steps)]


if __name__ == '__main__':
    init_env()
    logging.config.fileConfig("logging.ini")
    logging.Formatter.converter = time.gmtime  #utc
    cerebro = bt.Cerebro(maxcpus=1)
    # cerebro.addstrategy(PrintClose)

    cerebro.addstrategy(BollMACDStrategy)
    # cerebro.addstrategy(BollMACDStrategy, period_boll=265)  #, reversal=True)
    # cerebro.optstrategy(BollStrategy, period_boll=range(260, 280, 1), debug=False, only_print=True)
    # cerebro.optstrategy(BollStrategy, period_boll=265, price_diff=range(50, 180, 10), debug=False, only_print=True)
    # cerebro.optstrategy(BollStrategy, period_boll=265, price_diff=150, drawdown=0.2, stop_profit=float_range(0.4, 1.6, 10), debug=False, only_print=True)
    # cerebro.optstrategy(BollStrategy, period_boll=265, price_diff=150, drawdown=float_range(0.05, 0.35, 10), stop_profit=0.44, debug=False, only_print=True)
    # cerebro.addstrategy(BollStrategy, period_boll=265, price_diff=150, drawdown=0.2, stop_profit=0.44)
    # cerebro.optstrategy(BollStrategy, period_boll=range(22, 280, 10), price_diff=150, drawdown=0.2, stop_profit=0.44, debug=False, only_print=True)

    # cerebro.addstrategy(BollMACDStrategy, period_boll=265)
    # cerebro.optstrategy(BollMACDStrategy, period_boll=range(22, 300, 10), debug=False, only_print=True)
    # cerebro.optstrategy(BollMACDStrategy, period_boll=92, critical_dif=range(15, 42, 2), debug=False, only_print=True)
    # cerebro.optstrategy(BollMACDStrategy, period_boll=92, critical_dif=32, drawdown=float_range(0.05, 0.35, 10), debug=False, only_print=True)
    # cerebro.optstrategy(BollMACDStrategy, period_boll=92, critical_dif=32, drawdown=0.15, stop_profit=float_range(1.8, 2.5, 10), debug=False, only_print=True)

    # cerebro.addstrategy(BollEMA)
    # cerebro.addstrategy(Abbration, boll_period=200)
    # cerebro.addstrategy(BOLLKDJStrategy, price_diff=30)
    # cerebro.addstrategy(MACDKDJStrategy)

    # cerebro.addstrategy(BollReverser)
    # cerebro.optstrategy(BollReverser, period_boll=range(100, 300, 20), debug=False)

    # cerebro.optstrategy(BOLLKDJStrategy, price_diff=range(5, 50,5), debug=False)

    # cerebro.addobserver(Telegram)

    # 加载数据
    data = CustomDataset(name="BTC",
                         dataname="data/BTCUSDT-1m-2023.csv",
                         dtformat=lambda x: datetime.utcfromtimestamp(int(x) / 1000),
                         timeframe=bt.TimeFrame.Minutes,
                         fromdate=datetime(2023, 1, 1),
                         todate=datetime(2023, 12, 31),
                         nullvalue=0.0)
    cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=5)

    cerebro.broker.setcash(600.0)

    # 配置滑点费用,2跳
    # cerebro.broker.set_slippage_fixed(slippage*1)

    cerebro.broker.setcommission(commission=0.0005, margin=0.1, mult=1.0)
    # cerebro.broker.setcommission(commission=0.00075)

    cerebro.addsizer(bt.sizers.FixedSize, stake=0.1)
    # cerebro.addsizer(bt.sizers.PercentSizer, percents=100)

    # cerebro.addwriter(bt.WriterFile, out='log.csv', csv=True)

    cerebro.run()

    cerebro.plot()
