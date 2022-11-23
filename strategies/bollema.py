import backtrader as bt
from backtrader import Order
from datetime import datetime


class BollEMA(bt.Strategy):
    params = (("period_boll", 136), ("period_ema", 99), ("boll_diff", 40), ("price_diff", 20), ("production", False), ("debug", True))

    def log(self, txt, dt=None):
        if not self.p.debug: return
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt} {txt}')

    def __init__(self) -> None:
        self.marketposition = 0
        self.boll = bt.indicators.bollinger.BollingerBands(self.datas[0], period=self.p.period_boll)
        self.ema = bt.indicators.ExponentialMovingAverage(self.datas[0].close, period=self.p.period_ema)
        self.trade_count = 0
        self.last_price = 0
        self.live_data = False

    def notify_order(self, order):
        self.log(
            f"Order: {order.ordtypename()}, Status: {order.getstatusname()}, Price: {order.executed.price}, Size: {order.executed.size}, Alive: {order.alive()}"
        )
        if order.exectype == Order.Market and order.status == Order.Completed:
            self.last_price = order.executed.price

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_count += 1
            symbol = trade.getdataname()
            pnl = trade.pnl
            pnlcomm = trade.pnlcomm
            value = self.broker.getvalue()
            cash = self.broker.getcash()
            self.log(f'closed symbol is : {symbol}, total_profit : {pnl}, net_profit : {pnlcomm}, value: {value}, cash: {cash} count: {self.trade_count}')

        if trade.isopen:
            self.log(f'open symbol is : {trade.getdataname()} , price : {trade.price}, size: {trade.size} ')

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        msg = f'{dn} Data Status: {data._getstatusname(status)}'
        self.log(msg, datetime.utcnow())
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def gt_last_mid(self, data):
        return data.close[-1] > self.boll.mid[-1] and data.close[-2] > self.boll.mid[-2] and data.close[-3] > self.boll.mid[-3]

    def lt_last_mid(self, data):
        return data.close[-1] < self.boll.mid[-1] and data.close[-2] < self.boll.mid[-2] and data.close[-3] < self.boll.mid[-3]

    def close_gt_up(self, data):
        return data.close[0] > self.boll.top[0] and data.close[-1] > self.boll.top[-1]

    def close_lt_dn(self, data):
        return data.close[0] < self.boll.bot[0] and data.close[-1] < self.boll.bot[-1]

    def next(self):
        if self.p.production and not self.live_data:
            for data in self.datas:
                print('{}  {} | O: {} H: {} L: {} C: {} V:{}'.format(data.datetime.datetime(0), data._name, data.open[0], data.high[0], data.low[0],
                                                                     data.close[0], data.volume[0]))
            return

        data = self.datas[0]
        up = self.boll.top[0]
        mid = self.boll.mid[0]
        dn = self.boll.bot[0]
        ema = self.ema[0]
        diff = up - dn
        self.log(f" {data._name} | C: {data.close[0]} V:{data.volume[0]} UP:{up} MB:{mid} DN:{dn} EMA:{ema} Diff:{diff}", data.datetime.datetime(0))

        if self.marketposition == 0:
            if self.close_gt_up(data) and ema > mid and self.gt_last_mid(data) and diff > self.p.boll_diff:
                self.buy(data)
                self.marketposition = 1
            if self.close_lt_dn(data) and ema < mid and self.lt_last_mid(data) and diff > self.p.boll_diff:
                self.sell(data)
                self.marketposition = -1
        elif self.marketposition == 1:
            if self.last_price - data.close[0] > self.p.price_diff or ema <= mid:
                self.close()
                self.marketposition = 0
        elif self.marketposition == -1:
            if data.close[0] - self.last_price > self.p.price_diff or ema >= mid:
                self.close()
                self.marketposition = 0

    def stop(self):
        print('(MA Period_boll %2d, Period_ema %2d) Ending Value %.2f' % (self.p.period_boll, self.p.period_ema, self.broker.getcash()))
