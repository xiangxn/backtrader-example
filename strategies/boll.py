import json
import logging
import signal
import math
import backtrader as bt
from backtrader import Order
from datetime import datetime


class BollStrategy(bt.Strategy):
    params = (("period_boll", 275), ("price_diff", 20), ('small_cotter', 10), ("production", False), ("debug", True), ('reversal', False),
              ('only_print', False), ('multiple', 75), ('stop_profit', 1.4), ('drawdown', 0.25), ('min_volume', 8.5), ('max_volume', 30))

    status_file = "status.json"
    logger = None

    def debug(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        self.logger.debug(f'[{dt}]: {txt}')

    def warning(self, txt):
        if not self.p.only_print:
            self.logger.warning(txt)
        pass

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
        self.stop_profit_price = 0
        self.initial_margin = 0
        self.profit_flag = False
        self.current_size = 0
        self.max_win = 0

    def read_status_data(self):
        if not self.p.production: return
        try:
            with open(self.status_file, 'r', encoding='utf-8') as fw:
                injson = json.load(fw)
                self.marketposition = injson['marketposition']
                self.position_price = injson['position_price']
                self.stop_loss = injson['stop_loss']
        except Exception as e:
            self.logger.exception("Failed to read status file: %s", e)

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

    def up_stop_profit(self):
        data = self.datas[0]
        point = (self.boll.top[0] - self.boll.mid[0]) * 0.618
        # point += self.boll.mid[0]
        point = self.boll.top[0] - point
        # return self.position_price < data.close[0] and data.close[0] <= point
        return data.close[0] <= point

    def down_stop_profit(self):
        data = self.datas[0]
        point = (self.boll.mid[0] - self.boll.bot[0]) * 0.618
        # point = self.boll.mid[0] - point
        point += self.boll.bot[0]
        # return self.position_price > data.close[0] and data.close[0] >= point
        return data.close[0] >= point

    def get_cotter(self):
        return self.boll.top[0] - self.boll.bot[0]

    def calc_initial_margin(self):
        data = self.datas[0]
        if self.marketposition > 0:
            self.current_size = self.getsizing(data, isbuy=True)
        elif self.marketposition < 0:
            self.current_size = self.getsizing(data, isbuy=False)
        self.initial_margin = self.position_price * self.current_size / self.p.multiple

    def clear_data(self):
        self.marketposition = 0
        self.position_price = 0
        self.profit_flag = False
        self.initial_margin = 0
        self.current_size = 0
        self.max_win = 0

    def get_current_win(self):
        if self.marketposition > 0:
            return (self.datas[0].close[0] - self.position_price) * self.current_size
        elif self.marketposition < 0:
            return (self.position_price - self.datas[0].close[0]) * self.current_size
        return 0

    def get_volume(self):
        data = self.datas[0]
        return data.volume[0] + data.volume[-1] + data.volume[-2] + data.volume[-3] + data.volume[-4] + data.volume[-5] + data.volume[-6]

    def check_volume(self):
        volume = self.get_volume()
        if volume <= (self.p.min_volume * 10000) or volume >= (self.p.max_volume * 10000):
            return True
        return False

    def prenext(self):
        if self.p.production and not self.live_data:
            for data in self.datas:
                self.debug(' {} | O: {} H: {} L: {} C: {} V:{}'.format(data._name, data.open[0], data.high[0], data.low[0], data.close[0], data.volume[0]))
        else:
            data = self.datas[0]
            self.debug(' {} | O: {} H: {} L: {} C: {} V:{}'.format(data._name, data.open[0], data.high[0], data.low[0], data.close[0], data.volume[0]))

    def next(self):
        if math.isnan(self.boll.mid[-6]): return

        if self.p.production and not self.live_data: return

        data = self.datas[0]
        self.debug('C: {} P: {} I: {} W: {} F: {} M: {}'.format(data.close[0], self.position_price, self.initial_margin, self.get_current_win(),
                                                                self.profit_flag, self.max_win))

        # 止损间隔
        if self.stop_loss:
            if self.up_across_mid() or self.down_across_mid():
                self.stop_loss = False
            else:
                return

        if self.marketposition != 0:
            current_win = self.get_current_win()
            if not self.profit_flag and current_win >= self.initial_margin * self.p.stop_profit:
                self.profit_flag = True
                self.max_win = current_win
            if self.profit_flag:
                if current_win > 0:
                    if current_win > self.max_win:  #如果可能，则继续扩大收益
                        self.max_win = current_win
                    if (self.max_win - current_win) / self.max_win >= self.p.drawdown:  # 判断止盈
                        self.close()
                        self.stop_loss = True
                        self.clear_data()
                        return
                else:
                    self.profit_flag = False
                    self.max_win = 0

        # 开仓
        if self.marketposition == 0:
            if self.get_cotter() <= self.p.small_cotter:
                return
            # if self.close_gt_up() and self.gt_last_mid():
            order = None
            if self.close_gt_up():
                if self.p.reversal or self.check_volume():
                    # 空头
                    order = self.sell(data)
                    self.marketposition = -2
                else:
                    # 多头
                    order = self.buy(data)
                    self.marketposition = 1
                self.position_price = order.price if order and order.price else data.close[0]
                self.calc_initial_margin()
                self.warning(f"-----------------Open: MP:{self.marketposition}, C:{data.close[0]}, [{self.get_volume()}]--------------------")
            # if self.close_lt_dn() and self.lt_last_mid():
            if self.close_lt_dn():
                if self.p.reversal or self.check_volume():
                    # 多头
                    order = self.buy(data)
                    self.marketposition = 2
                else:
                    # 空头
                    order = self.sell(data)
                    self.marketposition = -1
                self.position_price = order.price if order and order.price else data.close[0]
                self.calc_initial_margin()
                self.warning(f"-----------------Open: MP:{self.marketposition}, C:{data.close[0]}, [{self.get_volume()}]--------------------")
        elif self.marketposition > 0:
            # 止损
            if self.position_price - data.close[0] > self.p.price_diff:
                self.warning(f"------Stop Loss: MP:{self.marketposition}, C:{data.close[0]}, P:{self.position_price}, D:{self.p.price_diff}------")
                self.close()
                self.stop_loss = True
                self.clear_data()
            elif (self.marketposition == 1 and self.down_across_mid()) or (self.marketposition == 2 and self.up_across_mid()):
                self.warning(f"------Close: MP:{self.marketposition}, C:{data.close[0]}, P:{self.position_price}, D:{self.p.price_diff}------")
                self.close()
                self.clear_data()
        elif self.marketposition < 0:
            # 止损
            if data.close[0] - self.position_price > self.p.price_diff:
                self.warning(f"------Stop Loss: MP:{self.marketposition}, C:{data.close[0]}, P:{self.position_price}, D:{self.p.price_diff}------")
                self.close()
                self.stop_loss = True
                self.clear_data()
            elif (self.marketposition == -1 and self.up_across_mid()) or (self.marketposition == -2 and self.down_across_mid()):
                # elif self.down_stop_profit():
                self.warning(f"------Close: MP:{self.marketposition}, C:{data.close[0]}, P:{self.position_price}, D:{self.p.price_diff}------")
                self.close()
                self.clear_data()

    def stop(self):
        print('(MA Period_boll %2d,%.2f) Ending Value: %.2f, Trade Count: %d' %
              (self.p.period_boll, self.p.price_diff, self.broker.getcash(), self.trade_count))
