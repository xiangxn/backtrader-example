from utils.helper import get_env
import backtrader as bt
import requests


class Telegram(bt.Analyzer):

    def __init__(self):
        self.chat_id = get_env("CHAT_ID")
        self.bot_token = get_env("BOT_TOKEN")

    def start(self):
        if not self.strategy.cerebro.p.quicknotify:
            print("cerebro does not have quicknotify enabled, so the notification will happen on the next candle.")

    def notify_order(self, order: bt.OrderBase):
        if order.status == bt.OrderBase.Completed:
            if order.isbuy():
                self.send_message(
                    f"Buy {order.data._name} at {bt.utils.num2date(order.executed.dt)}\n\t price: {order.executed.price}, size: {order.executed.size}")
            else:
                self.send_message(
                    f"Sell {order.data._name} at {bt.utils.num2date(order.executed.dt)}\n\t price: {order.executed.price}, size: {order.executed.size}")

    def send_message(self, msg):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_id}&text={msg}"
            print(requests.get(url).json())
        except Exception as e:
            print("send_message error: ", e)
