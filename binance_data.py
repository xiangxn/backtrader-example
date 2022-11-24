from datetime import datetime
import backtrader as bt

from data.dataset import CustomDataset
from strategies.abbration import Abbration
from strategies.bollkdj import BOLLKDJ
from strategies.bollema import BollEMA
from strategies.boll import Boll


class PrintClose(bt.Strategy):

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        print(f'{dt} {txt}')  # Print date and close

    def next(self):
        self.log('Close: %.3f' % self.data0.close[0])


if __name__ == '__main__':
    cerebro = bt.Cerebro(maxcpus=1)
    # cerebro.addstrategy(PrintClose)
    cerebro.addstrategy(Boll, period_boll=275)
    # cerebro.addstrategy(BollEMA)
    # cerebro.addstrategy(Abbration, boll_period=200)
    # cerebro.addstrategy(BOLLKDJ, boll_period=200, kdj_period=72, kdj_ma1=24, kdj_ma2=24)

    # cerebro.optstrategy(Boll, period_boll=range(8, 22), debug=False)

    # 加载数据
    data = CustomDataset(name="ETH",
                         dataname="data/ETHUSDT-1m-2022.csv",
                         dtformat=lambda x: datetime.utcfromtimestamp(int(x) / 1000),
                         timeframe=bt.TimeFrame.Minutes,
                         fromdate=datetime(2022, 5, 1),
                         todate=datetime(2022, 11, 1),
                         nullvalue=0.0)
    cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=5)

    cerebro.broker.setcash(100.0)

    # 配置滑点费用,2跳
    # cerebro.broker.set_slippage_fixed(slippage*1)

    cerebro.broker.setcommission(commission=0.0004, margin=0.1, mult=1.0)
    # cerebro.broker.setcommission(commission=0.00075)

    cerebro.addsizer(bt.sizers.FixedSize, stake=1)

    cerebro.run()

    cerebro.plot()