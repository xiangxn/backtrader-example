import backtrader as bt
from datetime import datetime


class Abbration(bt.Strategy):
    # 策略的参数
    params = (
        ("boll_period", 200),
        ("boll_mult", 2),
    )

    # log相应的信息
    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or bt.num2date(self.datas[0].datetime[0])
        print('{}, {}'.format(dt.isoformat(), txt))

    # 初始化策略的数据
    def __init__(self):
        # 计算布林带指标，大名鼎鼎的布林带策略
        self.boll_indicator = bt.indicators.BollingerBands(self.datas[0], period=self.p.boll_period, devfactor=self.p.boll_mult)

        # 保存交易状态
        self.marketposition = 0

    def prenext(self):
        # 由于期货数据有几千个，每个期货交易日期不同，并不会自然进入next
        # 需要在每个prenext中调用next函数进行运行
        # self.next()
        pass

    # 在next中添加相应的策略逻辑
    def next(self):
        # 每次运行一次，bar_num自然加1,并更新交易日
        self.current_datetime = bt.num2date(self.datas[0].datetime[0])
        self.current_hour = self.current_datetime.hour
        self.current_minute = self.current_datetime.minute
        # 数据
        data = self.datas[0]
        # 指标值
        # 布林带上轨
        top = self.boll_indicator.top
        # 布林带下轨
        bot = self.boll_indicator.bot
        # 布林带中轨
        mid = self.boll_indicator.mid

        # 开多
        if self.marketposition == 0 and data.close[0] > top[0] and data.close[-1] < top[-1]:
            # 获取一倍杠杆下单的手数
            info = self.broker.getcommissioninfo(data)
            symbol_multi = info.p.mult
            close = data.close[0]
            total_value = self.broker.getvalue()
            lots = total_value / (symbol_multi*close)
            self.buy(data, size=lots)
            self.marketposition = 1

        # 开空
        if self.marketposition == 0 and data.close[0] < bot[0] and data.close[-1] > bot[-1]:
            # 获取一倍杠杆下单的手数
            info = self.broker.getcommissioninfo(data)
            symbol_multi = info.p.mult
            close = data.close[0]
            total_value = self.broker.getvalue()
            lots = total_value / (symbol_multi*close)
            self.sell(data, size=lots)
            self.marketposition = -1

        # 平多
        if self.marketposition == 1 and data.close[0] < mid[0] and data.close[-1] > mid[-1]:
            self.close()
            self.marketposition = 0

        # 平空
        if self.marketposition == -1 and data.close[0] > mid[0] and data.close[-1] < mid[-1]:
            self.close()
            self.marketposition = 0

    def notify_trade(self, trade):
        # 一个trade结束的时候输出信息
        if trade.isclosed:
            symbol = trade.getdataname()
            pnl = trade.pnl
            pnlcomm = trade.pnlcomm
            value = self.broker.getvalue()
            self.log(f'closed symbol is : {symbol}, total_profit : {pnl}, net_profit : {pnlcomm}, value: {value}')
            # self.trade_list.append([self.datas[0].datetime.date(0),trade.getdataname(),trade.pnl,trade.pnlcomm])

        if trade.isopen:
            self.log(f'open symbol is : {trade.getdataname()} , price : {trade.price} ')

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        dt = datetime.utcnow()
        msg = 'Data Status: {}'.format(data._getstatusname(status))
        print(dt, dn, msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    # def stop(self):

    #     pass