import backtrader as bt
import pandas as pd
from datetime import datetime

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    #获取数据
    # stock_hfq_df = pd.read_csv("./data/600000.csv", index_col="datetime", parse_dates=True, usecols=["datetime", "open", "high", "low", "close", "volume"])
    start_date = datetime(2021, 1, 4)  # 回测开始时间
    end_date = datetime(2021, 12, 4)  # 回测结束时间
    data = bt.feeds.GenericCSVData(dataname="./data/600000.csv",
                                   fromdate=start_date,
                                   todate=end_date,
                                   dtformat="%Y/%m/%d",
                                   datetime=0,
                                   open=4,
                                   high=2,
                                   low=3,
                                   close=1,
                                   volume=5,
                                   openinterest=-1,
                                   reverse=True)  #加载数据
    # data = bt.feeds.PandasData(dataname=stock_hfq_df, fromdate=start_date, todate=end_date)  # 加载数据
    
    cerebro.adddata(data)  # 将数据传入回测系统

    cerebro.broker.setcash(100000.0)
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())