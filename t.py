import datetime
import backtrader as bt
import backtrader.feeds as btfeeds


class PrintClose(bt.Strategy):

    def __init__(self):
        self.dataclose = self.datas[0].close

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0).strftime('%Y-%m-%d %H:%M:%S%z')
        print(f'{dt} {txt}')  # Print date and close

    def next(self):
        self.log(self.dataclose[0])


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(PrintClose)
    datapath = './data/t.csv'

    data = btfeeds.GenericCSVData(dataname=datapath, dtformat=('%Y-%m-%d %H:%M:%S%z'), datetime=0, open=1, high=2, low=3, close=4, volume=5, openinterest=-1)

    cerebro.adddata(data)
    cerebro.run()