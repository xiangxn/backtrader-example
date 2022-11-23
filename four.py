import backtrader as bt
import pandas as pd
from datetime import datetime


# 创建一个测试策略
class TestStrategy(bt.Strategy):

    def log(self, txt, dt=None):
        ''' 记录策略信息'''
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # 应用第一个数据源的收盘价
        self.dataclose = self.datas[0].close

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        if self.dataclose[0] < self.dataclose[-1]:
            # 当前的价格比上一次价格（也就是昨天的价格低）

            if self.dataclose[-1] < self.dataclose[-2]:
                # 上一次的价格（昨天）比上上一次的价格（前天的价格）低

                # 开始买！！
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                self.buy()


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    # 增加一个策略
    cerebro.addstrategy(TestStrategy)

    #获取数据
    start_date = datetime(2021, 1, 4)  # 回测开始时间
    end_date = datetime(2022, 11, 3)  # 回测结束时间
    stock_hfq_df = pd.read_csv("./data/sh600000.csv", index_col="datetime", parse_dates=True, usecols=["datetime", "open", "high", "low", "close", "volume"])
    stock_hfq_df = stock_hfq_df.iloc[::-1]
    data = bt.feeds.PandasData(dataname=stock_hfq_df, fromdate=start_date, todate=end_date)  # 加载数据

    cerebro.adddata(data)  # 将数据传入回测系统

    cerebro.broker.setcash(100000.0)
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())