import backtrader as bt
from indicators.kdj import KDJ
from datetime import datetime


class BOLLKDJ(bt.Strategy):
    params = (("boll_period", 21), ("boll_mult", 2), ("kdj_period", 9), ("kdj_ma1", 3), ("kdj_ma2", 3))

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt} {txt}')

    def __init__(self):
        self.boll = bt.indicators.BollingerBands(self.datas[0], period=self.p.boll_period, devfactor=self.p.boll_mult)
        self.kdj = KDJ(self.datas[0], period=self.p.kdj_period, period_dfast=self.p.kdj_ma1, period_dslow=self.p.kdj_ma2)
        # 保存交易状态
        self.marketposition = 0
        self.last_price = 0
        # KDJ信号
        self.kdj_signal = 0

    def next(self):
        data = self.datas[0]
        up = self.boll.top[0]
        dn = self.boll.bot[0]
        diff = up - dn

        # KDJ信号
        condition1 = self.kdj.J[-1] - self.kdj.D[-1]
        condition2 = self.kdj.J[0] - self.kdj.D[0]
        if condition1 < 0 and condition2 > 0:
            self.kdj_signal = 1  # 上穿(买入信号)
        elif condition1 > 0 and condition2 < 0:
            self.kdj_signal = -1  # 下穿(卖出信号)

        # 未持仓
        if self.marketposition == 0:
            # 买入
            if data.close[0] > up and self.kdj_signal == 1 and diff > 50:
                self.buy(data)
                self.last_price = data.close[0]
                self.marketposition = 1
            # 卖出
            if data.close[0] < dn and self.kdj_signal == -1 and diff > 50:
                self.sell(data)
                self.last_price = data.close[0]
                self.marketposition = -1
        # 已持空仓
        elif self.marketposition == -1:
            if (self.kdj_signal == 1 and data.close[0] > dn) or (data.close[0] - self.last_price > 20):
                self.close()
                self.marketposition = 0
                self.last_price = 0
        # 已持多仓
        else:
            if (self.kdj_signal == -1 and data.close[0] < up) or (self.last_price - data.close[0] > 20):
                self.close()
                self.marketposition = 0
                self.last_price = 0
