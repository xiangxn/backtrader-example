import logging
import json
import backtrader as bt
from backtrader import OrderBase
from backtrader.indicators import MACDHisto
from tools.strategy import BaseStrategy


class BollMACDStrategy(BaseStrategy):
    params = (
        ("period_boll", 92),
        ('macd_fast_period', 12),
        ('macd_slow_period', 26),
        ('macd_signal_period', 9),
        ("price_diff", 200),
        ('small_cotter', 300),
        ('multiple', 75),
        ('stop_profit', 1.5),
        ('drawdown', 0.15),
        ('critical_dif', 45),
        ('limit_value', 100),  # This fits the price setup for BTC
        ('limit_value_min', 10),  # This fits the price setup for BTC
    )

    status_file = "status.json"

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        super().__init__()
        self.boll = bt.indicators.bollinger.BollingerBands(self.datas[0], period=self.p.period_boll)
        self.macd = MACDHisto(self.data, period_me1=self.p.macd_fast_period, period_me2=self.p.macd_slow_period, period_signal=self.p.macd_signal_period)
        self.marketposition = 0
        self.tmp_position = 0
        self.trade_count = 0
        self.position_price = 0
        self.stop_loss = False
        self.stop_profit_price = 0
        self.initial_margin = 0
        self.profit_flag = False
        self.current_size = 0
        self.max_win = 0
        self.current_order = None

    def read_status_data(self):
        if not self.p.production: return
        try:
            with open(self.status_file, 'r', encoding='utf-8') as fw:
                injson = json.load(fw)
                self.marketposition = injson['marketposition']
                self.position_price = injson['position_price']
                self.stop_loss = injson['stop_loss']
        except Exception as e:
            # self.logger.exception("Failed to read status file: %s", e)
            pass

    def on_exit(self):
        self.save_status_data()

    def save_status_data(self):
        if not self.p.production: return
        data = { 'marketposition': self.marketposition, 'position_price': self.position_price, 'stop_loss': self.stop_loss }
        with open(self.status_file, 'w', encoding='utf-8') as fw:
            json.dump(data, fw, indent=4, ensure_ascii=False)

    def start(self):
        self.read_status_data()

    def notify_order(self, order: OrderBase):
        self.info(
            f"Order: {order.ordtypename()}, Status: {order.getstatusname()}, Price: {order.executed.price:.4f}, Size: {order.executed.size}, Alive: {order.alive()}"
        )
        if self.current_order:
            if order.status == bt.Order.Completed:
                self.position_price = self.current_order.price
                self.current_order = None
                self.marketposition = self.tmp_position
                self.tmp_position = 0
                self.calc_initial_margin()
            elif order.status == bt.Order.Canceled:
                self.tmp_position = 0
                self.current_order = None
                self.clear_data()

    def notify_trade(self, trade):
        if trade.isclosed:
            self.trade_count += 1
            symbol = trade.getdataname()
            pnl = trade.pnl
            pnlcomm = trade.pnlcomm
            value = self.broker.getvalue()
            cash = self.broker.getcash()
            self.debug(
                f'Closed: {symbol}, stop_loss:{self.stop_loss}, total_profit : {pnl:.4f}, net_profit : {pnlcomm:.4f}, value: {value:.4f}, cash: {cash:.4f} count: {self.trade_count}'
            )

        if trade.isopen:
            self.debug(f'Open: {trade.getdataname()} , price : {trade.price:.4f}, size: {trade.size}, MP: {self.marketposition}')

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

    def get_cotter(self):
        return self.boll.top[0] - self.boll.bot[0]

    def check_direction(self):
        if (abs(self.macd.macd[0]) < self.p.critical_dif):
            return False
        # else:
        #     if self.macd.histo[0] < 0:
        #         if self.macd.histo[-1] > 0 or self.macd.histo[-2] > 0 or self.macd.histo[-3] > 0:
        #             return True
        #         else:
        #             return False
        #     elif self.macd.histo[0] > 0:
        #         if self.macd.histo[-1] < 0 or self.macd.histo[-2] < 0 or self.macd.histo[-3] < 0:
        #             return True
        #         else:
        #             return False
        return True

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

    def check_take_profit(self, current_win):
        if (self.max_win - current_win) / self.max_win >= self.p.drawdown:
            if self.macd.histo[0] > 0:
                if self.macd.histo[-1] <= 0:
                    return True
            elif self.macd.histo[0] < 0:
                if self.macd.histo[-1] >= 0:
                    return True
        return False

    def _sell(self, data, lv=None):
        size = self.getsizing(data, isbuy=False)
        limit_value = self.p.limit_value
        if lv:
            limit_value = lv
        price = round(data.close[0] + limit_value, 2)
        self.position_price = price
        self.info(f"sell price: {price}")
        return self.sell(data, size=size, price=price, exectype=bt.Order.Limit)

    def _buy(self, data, lv=None):
        size = self.getsizing(data)
        limit_value = self.p.limit_value
        if lv:
            limit_value = lv
        price = round(data.close[0] - limit_value, 2)
        self.position_price = price
        self.info(f"buy price: {price}")
        return self.buy(data, size=size, price=price, exectype=bt.Order.Limit)

    def _close(self):
        data = self.datas[0]
        size = self.getposition(data, self.broker).size
        if size > 0:
            return self._sell(data, self.p.limit_value_min)
        elif size < 0:
            return self._buy(data, self.p.limit_value_min)
        return None

    def next(self):
        if self.p.production and not self.live_data: return

        self.debug("DIF:{}, EDA:{}, MACD:{}".format(self.macd.macd[0], self.macd.signal[0], self.macd.histo[0]))

        data = self.datas[0]
        self.debug('C: {} V: {:.2f} P: {} I: {:.2f} W: {:.2f} F: {} M: {:.2f}'.format(data.close[0], data.volume[0], self.position_price, self.initial_margin,
                                                                                      self.get_current_win(), self.profit_flag, self.max_win))

        # 检查未完成订单
        if self.current_order:
            if self.tmp_position == 0:
                self.current_order = None
            elif self.tmp_position > 0:
                if data.close[0] - self.position_price > self.p.limit_value * 1.5:
                    self.cancel(self.current_order)
            elif self.tmp_position < 0:
                if self.position_price - data.close[0] > self.p.limit_value * 1.5:
                    self.cancel(self.current_order)
            return

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
                    if self.check_take_profit(current_win):  # 判断止盈
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
            if self.close_gt_up():
                if self.check_direction():
                    # 空头
                    self.current_order = self._sell(data)
                    self.tmp_position = -2
                else:
                    # 多头
                    self.current_order = self._buy(data)
                    self.tmp_position = 1
            # if self.close_lt_dn() and self.lt_last_mid():
            if self.close_lt_dn():
                if self.check_direction():
                    # 多头
                    self.current_order = self._buy(data)
                    self.tmp_position = 2
                else:
                    # 空头
                    self.current_order = self._sell(data)
                    self.tmp_position = -1
        elif self.marketposition > 0:
            # 止损
            if self.position_price - data.close[0] > self.p.price_diff:
                self.close()
                mp = self.marketposition
                self.clear_data()
                if mp == 2:  # 砸止损后杀跌
                    self.current_order = self._sell(data)
                    self.tmp_position = -1
                else:
                    self.stop_loss = True
            elif (self.marketposition == 1 and self.down_across_mid()) or (self.marketposition == 2 and self.up_across_mid()):
                self.close()
                self.clear_data()

        elif self.marketposition < 0:
            # 止损
            if data.close[0] - self.position_price > self.p.price_diff:
                self.close()
                mp = self.marketposition
                self.clear_data()
                if mp == -2:  # 拉止损后追涨
                    self.current_order = self._buy(data)
                    self.tmp_position = 1
                else:
                    self.stop_loss = True
            elif (self.marketposition == -1 and self.up_across_mid()) or (self.marketposition == -2 and self.down_across_mid()):
                self.close()
                self.clear_data()

    def stop(self):
        print('Period_boll: %d,stop_profit: %.2f,drawdown: %.2f,price_diff: %.2f,critical_dif: %.2f [Ending Value: %.2f,Trade Count: %d]' % (
            self.p.period_boll,
            self.p.stop_profit,
            self.p.drawdown,
            self.p.price_diff,
            self.p.critical_dif,
            self.broker.getcash(),
            self.trade_count,
        ))
