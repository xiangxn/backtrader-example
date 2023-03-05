import json
import logging
import signal
import backtrader as bt
from backtrader import Order
from datetime import datetime


class BollReverser(bt.Strategy):
    params = (("period_boll", 52), ("production", False), ("debug", True))

    logger = None

    def debug(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        self.logger.debug(f'[{dt}]: {txt}')

    def warning(self, txt):
        self.logger.warning(txt)

    def __init__(self) -> None:
        signal.signal(signal.SIGINT, self.sigstop)
        self.boll = bt.indicators.bollinger.BollingerBands(self.datas[0], period=self.p.period_boll)
        self.logger = self.logger if self.logger else logging.getLogger(__name__)
        if self.p.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARNING)
        self.trade_count = 0
        self.live_data = False

    def sigstop(self, a, b):
        self.warning('Stopping Backtrader...')
        self.env.runstop()

    def stop(self):
        self.warning('(MA Period_boll %2d) Ending Value: %.2f, Trade Count: %d' % (self.p.period_boll, self.broker.getcash(), self.trade_count))

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        msg = f'{dn} Data Status: {data._getstatusname(status)}'
        self.debug(msg, datetime.utcnow())
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_count += 1
            symbol = trade.getdataname()
            pnl = trade.pnl
            pnlcomm = trade.pnlcomm
            value = self.broker.getvalue()
            cash = self.broker.getcash()
            self.debug(f'closed symbol is : {symbol}, total_profit : {pnl}, net_profit : {pnlcomm}, value: {value}, cash: {cash} count: {self.trade_count}')
        if trade.isopen:
            self.debug(f'open symbol is : {trade.getdataname()} , price : {trade.price}, size: {trade.size} ')

    def next(self):
        data = self.datas[0]
        vn = data._name.replace(self.broker.currency, "")
        _, value = self.broker.get_wallet_balance(vn)
        position = self.getposition()
        print('{}  {} | O: {} H: {} L: {} C: {} V:{} Value: {} Cash: {} Position: {}'.format(data.datetime.datetime(0), data._name, data.open[0], data.high[0],
                                                                                             data.low[0], data.close[0], data.volume[0], value,
                                                                                             self.broker.getcash(), position.size))

        if not self.live_data:
            return

        if position.size == 0:
            # if self.up_across_top():
            if self.close_gt_up():
                self.sell()
            # elif self.down_across_bot():
            elif self.close_lt_dn():
                self.buy()
        elif position.size > 0:
            # if self.down_across_mid():
            if self.close_across_top():
                self.close()
        elif position.size < 0:
            # if self.up_across_mid():
            if self.close_across_bot():
                self.close()

    def down_across_mid(self):
        data = self.datas[0]
        return data.close[-1] > self.boll.mid[-1] and data.close[0] < self.boll.mid[0]

    def up_across_mid(self):
        data = self.datas[0]
        return data.close[-1] < self.boll.mid[-1] and data.close[0] > self.boll.mid[0]

    def down_across_bot(self):
        data = self.datas[0]
        return data.close[-2] > self.boll.bot[-2] and data.close[-1] > self.boll.bot[-1] and data.close[0] < self.boll.bot[0]

    def close_across_bot(self):
        data = self.datas[0]
        return data.close[-1] > self.boll.bot[-1] and data.close[0] < self.boll.bot[0]

    def up_across_top(self):
        data = self.datas[0]
        return data.close[-2] < self.boll.top[-2] and data.close[-1] < self.boll.top[-1] and data.close[0] > self.boll.top[0]

    def close_across_top(self):
        data = self.datas[0]
        return data.close[-1] < self.boll.top[-1] and data.close[0] > self.boll.top[0]

    def close_gt_up(self):
        data = self.datas[0]
        return data.close[0] > self.boll.top[0] and data.close[-1] > self.boll.top[-1]

    def close_lt_dn(self):
        data = self.datas[0]
        return data.close[0] < self.boll.bot[0] and data.close[-1] < self.boll.bot[-1]
