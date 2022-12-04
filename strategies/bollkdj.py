import backtrader as bt
from indicators.kdj import KDJ
from datetime import datetime
from backtrader import Order


class BOLLKDJStrategy(bt.Strategy):
    params = (("boll_period", 53), ("boll_mult", 2), ("kdj_period", 9), ("kdj_ma1", 3), ("kdj_ma2", 3), ("price_diff", 30), ("debug", True))

    def log(self, txt, dt=None):
        if not self.p.debug: return
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt} {txt}')

    def __init__(self):
        self.trade_count = 0
        self.boll = bt.indicators.BollingerBands(self.datas[0], period=self.p.boll_period, devfactor=self.p.boll_mult)
        self.kdj = KDJ(self.datas[0], period=self.p.kdj_period, period_dfast=self.p.kdj_ma1, period_dslow=self.p.kdj_ma2)
        # 保存交易状态
        self.marketposition = 0
        self.position_price = 0

        # BOLL信号
        self.boll_signal = 0
        # KDJ信号
        self.kdj_signal = 0

        self.stop_loss = 0

    def notify_order(self, order):
        if order.exectype == Order.Market and order.status == Order.Completed:
            self.position_price = order.executed.price
            self.log(
                f"Order: {order.ordtypename()}, Status: {order.getstatusname()}, Price: {order.executed.price}, Size: {order.executed.size}, Alive: {order.alive()}"
            )

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_count += 1

    def check_boll_signal(self):
        # 卖出信号
        if self.up_across():
            self.boll_signal = -1
        # 买入信号
        elif self.dn_across():
            self.boll_signal = 1

    def check_kdj_signal(self):
        condition1 = self.kdj.J[-1] - self.kdj.D[-1]
        condition2 = self.kdj.J[0] - self.kdj.D[0]
        if condition1 < 0 and condition2 > 0 and (self.kdj.K[0] <= 25 and self.kdj.D[0] <= 25 and self.kdj.J[0] <= 25):
            self.kdj_signal = 1  # 上穿(买入信号)
        elif condition1 > 0 and condition2 < 0 and (self.kdj.K[0] >= 75 and self.kdj.D[0] >= 75 and self.kdj.J[0] >= 75):
            self.kdj_signal = -1  # 下穿(卖出信号)

    def up_across(self):
        data = self.datas[0]
        return data.close[-1] < self.boll.top[-1] and data.close[0] > self.boll.top[0]

    def dn_across(self):
        data = self.datas[0]
        return data.close[-1] > self.boll.bot[-1] and data.close[0] < self.boll.bot[0]

    def dn_across_mid(self):
        data = self.datas[0]
        return data.close[-1] > self.boll.mid[-1] and data.close[0] < self.boll.mid[0]

    def up_across_mid(self):
        data = self.datas[0]
        return data.close[-1] < self.boll.mid[-1] and data.close[0] > self.boll.mid[0]

    def next(self):
        if self.stop_loss == -1:
            if self.dn_across():
                self.stop_loss = 0
                self.boll_signal = 0
                self.kdj_signal = 0
            else:
                return
        elif self.stop_loss == 1:
            if self.up_across():
                self.stop_loss = 0
                self.boll_signal = 0
                self.kdj_signal = 0
            else:
                return

        # BOLL信号检查
        self.check_boll_signal()
        # KDJ信号
        self.check_kdj_signal()

        # 未持仓
        if self.marketposition == 0:
            # 买入
            if self.boll_signal > 0 and self.kdj_signal > 0:
                self.position_price = self.datas[0].close[0]
                self.buy(self.datas[0])
                self.marketposition = 1
                self.boll_signal = 0
                self.kdj_signal = 0
            # 卖出
            elif self.boll_signal < 0 and self.kdj_signal < 0:
                self.position_price = self.datas[0].close[0]
                self.sell(self.datas[0])
                self.marketposition = -1
                self.boll_signal = 0
                self.kdj_signal = 0
        # 已持空仓
        elif self.marketposition == -1:
            if self.position_price > 0 and (self.datas[0].close[0] - self.position_price > self.p.price_diff):
                self.close()
                self.marketposition = 0
                self.position_price = 0
                self.boll_signal = 0
                self.kdj_signal = 0
                self.stop_loss = -1
            elif self.boll_signal > 0 and self.kdj_signal > 0:
                # elif self.dn_across():
                self.close()
                self.marketposition = 0
                self.position_price = 0
                self.boll_signal = 0
                self.kdj_signal = 0
        # 已持多仓
        else:
            if (self.position_price - self.datas[0].close[0] > self.p.price_diff):
                self.close()
                self.marketposition = 0
                self.position_price = 0
                self.boll_signal = 0
                self.kdj_signal = 0
                self.stop_loss = 1
            elif self.boll_signal < 0 and self.kdj_signal < 0:
                # elif self.up_across():
                self.close()
                self.marketposition = 0
                self.position_price = 0
                self.boll_signal = 0
                self.kdj_signal = 0

    def stop(self):
        print('(MA boll_period %2d, %2d) Ending Value: %.2f, Trade Count: %d' %
              (self.p.boll_period, self.p.kdj_period, self.broker.getcash(), self.trade_count))
