import logging
import backtrader as bt
from indicators.kdj import KDJ
from backtrader.indicators.macd import MACD
from backtrader import Order


class MACDKDJStrategy(bt.Strategy):
    logger = None
    params = (("macd_period_me1", 12), ("macd_period_me2", 26), ("macd_period_signal", 9), ("kdj_period", 9), ("kdj_ma1", 3), ("kdj_ma2", 3),
              ("price_diff", 20), ("debug", True))

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        if len(self.logger.root.handlers) == 0:
            print(f'({dt}): {txt}')
        else:
            self.logger.debug(f'({dt}): {txt}')

    def __init__(self):
        self.trade_count = 0
        self.logger = self.logger if self.logger else logging.getLogger(__name__)
        if self.p.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARNING)
        self.kdj = KDJ(self.datas[0], period=self.p.kdj_period, period_dfast=self.p.kdj_ma1, period_dslow=self.p.kdj_ma2)
        self.macd = MACD(self.datas[0], period_me1=self.p.macd_period_me1, period_me2=self.p.macd_period_me2, period_signal=self.p.macd_period_signal)

    def next(self):
        self.log(f"{self.macd.macd[0]}, {self.macd.signal[0]}")
