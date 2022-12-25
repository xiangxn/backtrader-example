import logging
import backtrader as bt
from indicators.kdj import KDJ
from backtrader.indicators import MACD
from backtrader import Order


class MACDKDJStrategy(bt.Strategy):
    logger = None
    params = (
        ('macd_fast_period', 12),
        ('macd_slow_period', 26),
        ('macd_signal_period', 9),
        ('kdj_fast_period', 9),
        ('kdj_slow_period', 3),
        ('debug', True),
    )

    def debug(self, txt, dt=None):
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
        self.macd = MACD(self.data, period_me1=self.p.macd_fast_period, period_me2=self.p.macd_slow_period, period_signal=self.p.macd_signal_period)
        self.kdj = KDJ(self.data, period=self.p.kdj_fast_period, period_dfast=self.p.kdj_slow_period, period_dslow=self.p.kdj_slow_period)
        self.marketposition = 0

    def notify_trade(self, trade):
        cash = self.broker.getcash()
        if trade.isclosed:
            self.trade_count += 1
            symbol = trade.getdataname()
            pnl = trade.pnl
            pnlcomm = trade.pnlcomm
            value = self.broker.getvalue()
            self.debug(f'closed symbol is : {symbol}, total_profit : {pnl}, net_profit : {pnlcomm}, value: {value}, cash: {cash} count: {self.trade_count}')

        if trade.isopen:
            self.debug(f'open symbol is : {trade.getdataname()} , price : {trade.price}, size: {trade.size}, cash: {cash} ')

    def next(self):
        if self.marketposition == 0:
            # 当 MACD 指标出现金叉时，购买股票
            if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] < self.macd.signal[-1]:
                self.buy()
                self.marketposition = 1
            # 当 KDJ 指标出现拐点时，卖出股票
            elif self.kdj.K[0] < self.kdj.D[0] and self.kdj.K[-1] > self.kdj.D[-1]:
                self.sell()
                self.marketposition = -1
        elif self.marketposition == -1:
            if self.macd.macd[0] > self.macd.signal[0] and self.macd.macd[-1] < self.macd.signal[-1]:
                self.close()
                self.marketposition = 0
        elif self.marketposition == 1:
            if self.kdj.K[0] < self.kdj.D[0] and self.kdj.K[-1] > self.kdj.D[-1]:
                self.close()
                self.marketposition = 0

    def stop(self):
        self.debug('Ending Value: %.2f, Trade Count: %d' % (self.broker.getcash(), self.trade_count))
