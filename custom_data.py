from datetime import datetime
import backtrader as bt
import pandas as pd


class PrintClose(bt.Strategy):

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt} {txt}')  # Print date and close

    def next(self):
        self.log('Close: %.3f' % self.data0.close[0])
        self.log('turnover: %.8f' % self.data0.turnover[0])


class CustomData(bt.feeds.PandasData):
    # class CustomData(bt.feeds.GenericCSVData):
    lines = ("turnover", )
    params = (("turnover", -1), )


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(PrintClose)
    datapath = './data/t.csv'

    # 加载数据
    stock_hfq_df = pd.read_csv(datapath, index_col="date", parse_dates=True, usecols=["date", "open", "high", "low", "close", "volume", "turnover"])
    start_date = datetime(2016, 7, 4)  # 回测开始时间
    end_date = datetime(2021, 12, 4)  # 回测结束时间
    data = CustomData(dataname=stock_hfq_df, fromdate=start_date, todate=end_date)

    # 加载数据
    # data = CustomData(dataname=datapath, dtformat=('%Y-%m-%d %H:%M:%S%z'), datetime=0, open=1, high=2, low=3, close=4, volume=5, turnover=6, openinterest=-1)

    cerebro.adddata(data)
    cerebro.run()