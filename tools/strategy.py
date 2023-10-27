import logging
import signal
import backtrader as bt
from datetime import datetime


class BaseStrategy(bt.Strategy):
    params = (("debug", True), ('only_print', False), ("production", False))

    logger = None

    def __init__(self) -> None:
        signal.signal(signal.SIGINT, self.sigstop)
        self.logger = self.logger if self.logger else logging.getLogger(__name__)
        if self.p.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        self.live_data = False

    def sigstop(self, a, b):
        self.info('Stopping Backtrader...')
        self.env.runstop()

    def debug(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.datetime(0)
        self.logger.debug(f'[{dt}] {txt}')

    def info(self, txt):
        if not self.p.only_print:
            self.logger.info(txt)
        pass

    def notify_data(self, data, status, *args, **kwargs):
        dn = data._name
        msg = f'{dn} Data Status: {data._getstatusname(status)}'
        self.info(msg)
        if data._getstatusname(status) == 'LIVE':
            self.live_data = True
        else:
            self.live_data = False

    def prenext(self):
        if self.p.production and not self.live_data:
            for data in self.datas:
                self.debug(' {} | O: {} H: {} L: {} C: {} V:{:.4f}'.format(data._name, data.open[0], data.high[0], data.low[0], data.close[0], data.volume[0]))
        else:
            data = self.datas[0]
            self.debug(' {} | O: {} H: {} L: {} C: {} V:{:.4f}'.format(data._name, data.open[0], data.high[0], data.low[0], data.close[0], data.volume[0]))