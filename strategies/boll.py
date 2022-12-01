import json
import logging
import signal
import backtrader as bt
from backtrader import Order
from datetime import datetime


class BollStrategy(bt.Strategy):
    params = (("period_boll", 275), ("price_diff", 20), ("production", False), ("debug", True))

    status_file = "status.json"
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
        self.marketposition = 0
        self.trade_count = 0
        self.position_price = 0
        self.live_data = False
        self.stop_loss = False

    def read_status_data(self):
        if not self.p.production: return
        try:
            with open(self.status_file, 'r', encoding='utf-8') as fw:
                injson = json.load(fw)
                self.marketposition = injson['marketposition']
                self.position_price = injson['position_price']
                self.stop_loss = injson['stop_loss']
        except Exception as e:
            print("Failed to read status file: %s", e)

    def save_status_data(self):
        if not self.p.production: return
        data = { 'marketposition': self.marketposition, 'position_price': self.position_price, 'stop_loss': self.stop_loss }
        with open(self.status_file, 'w', encoding='utf-8') as fw:
            json.dump(data, fw, indent=4, ensure_ascii=False)

    def start(self):
        self.read_status_data()

    def sigstop(self, a, b):
        self.warning('Stopping Backtrader...')
        self.save_status_data()
        self.env.runstop()

    def notify_order(self, order):
        self.debug(
            f"Order: {order.ordtypename()}, Status: {order.getstatusname()}, Price: {order.executed.price}, Size: {order.executed.size}, Alive: {order.alive()}"
        )
        if order.exectype == Order.Market and order.status == Order.Completed:
            # self.position_price = order.executed.price # 无数据
            pass

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

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        msg = f'{dn} Data Status: {data._getstatusname(status)}'
        self.debug(msg, datetime.utcnow())
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def gt_last_mid(self):
        data = self.datas[0]
        return data.close[-1] > self.boll.mid[-1] and data.close[-2] > self.boll.mid[-2] and data.close[-3] > self.boll.mid[-3]

    def lt_last_mid(self):
        data = self.datas[0]
        return data.close[-1] < self.boll.mid[-1] and data.close[-2] < self.boll.mid[-2] and data.close[-3] < self.boll.mid[-3]

    def close_gt_up(self):
        data = self.datas[0]
        return data.close[0] > self.boll.top[0] and data.close[-1] > self.boll.top[-1]

    def close_lt_dn(self):
        data = self.datas[0]
        return data.close[0] < self.boll.bot[0] and data.close[-1] < self.boll.bot[-1]

    def down_across_mid(self):
        data = self.datas[0]
        return data.close[-1] > self.boll.mid[-1] and data.close[0] < self.boll.mid[0]

    def up_across_mid(self):
        data = self.datas[0]
        return data.close[-1] < self.boll.mid[-1] and data.close[0] > self.boll.mid[0]

    def down_across_top(self):
        data = self.datas[0]
        return data.close[-2] > self.boll.top[-2] and data.close[-1] > self.boll.top[-1] and data.close[0] < self.boll.top[0]

    def up_across_bot(self):
        data = self.datas[0]
        return data.close[-2] < self.boll.bot[-2] and data.close[-1] < self.boll.bot[-1] and data.close[0] > self.boll.bot[0]

    def prenext(self):
        if self.p.production and not self.live_data:
            for data in self.datas:
                print('{}  {} | O: {} H: {} L: {} C: {} V:{}'.format(data.datetime.datetime(0), data._name, data.open[0], data.high[0], data.low[0],
                                                                     data.close[0], data.volume[0]))

    def next(self):
        if self.p.production and not self.live_data:
            return

        data = self.datas[0]
        print('{}  {} | O: {} H: {} L: {} C: {} V:{} P:{}'.format(data.datetime.datetime(0), data._name, data.open[0], data.high[0], data.low[0], data.close[0],
                                                                  data.volume[0], self.position_price))

        # 止损间隔
        if self.stop_loss:
            if self.up_across_mid() or self.down_across_mid():
                self.stop_loss = False
            else:
                return

        # 开仓
        if self.marketposition == 0:
            # 多头
            if self.close_gt_up() and self.gt_last_mid():
                self.position_price = data.close[0]
                self.buy(data)
                self.marketposition = 1
                self.warning(f"---------------------------Open: MP:{self.marketposition}, C:{data.close[0]}------------------------------")
            # 空头
            if self.close_lt_dn() and self.lt_last_mid():
                self.position_price = data.close[0]
                self.sell(data)
                self.marketposition = -1
                self.warning(f"---------------------------Open: MP:{self.marketposition}, C:{data.close[0]}------------------------------")
        elif self.marketposition == 1:
            # 止损
            if self.position_price - data.close[0] > self.p.price_diff:
                self.warning(f"------Stop Loss: MP:{self.marketposition}, C:{data.close[0]}, P:{self.position_price}, D:{self.p.price_diff}------")
                self.close()
                self.marketposition = 0
                self.stop_loss = True
                self.position_price = 0
            elif self.down_across_mid():
                self.warning(f"------Close: MP:{self.marketposition}, C:{data.close[0]}, P:{self.position_price}, D:{self.p.price_diff}------")
                self.close()
                self.marketposition = 0
                self.position_price = 0
        elif self.marketposition == -1:
            # 止损
            if self.position_price > 0 and data.close[0] - self.position_price > self.p.price_diff:
                self.warning(f"------Stop Loss: MP:{self.marketposition}, C:{data.close[0]}, P:{self.position_price}, D:{self.p.price_diff}------")
                self.close()
                self.marketposition = 0
                self.stop_loss = True
                self.position_price = 0
            elif self.up_across_mid():
                self.warning(f"------Close: MP:{self.marketposition}, C:{data.close[0]}, P:{self.position_price}, D:{self.p.price_diff}------")
                self.close()
                self.marketposition = 0
                self.position_price = 0

    def stop(self):
        self.warning('(MA Period_boll %2d) Ending Value: %.2f, Trade Count: %d' % (self.p.period_boll, self.broker.getcash(), self.trade_count))
