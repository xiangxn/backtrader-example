from utils.helper import get_env
import backtrader as bt
import requests


class Telegram(bt.Observer):
    lines = ("buy", "sell")

    def __init__(self):
        self.chat_id = get_env("CHAT_ID")
        self.bot_token = get_env("BOT_TOKEN")

    def next(self):
        for order in self._owner._orderspending:
            if order.data is not self.data or not order.executed.size:
                continue
            if order.isbuy():
                self.lines.buy[0] = order.executed.price
                self.send_message(
                    f"Buy {order.data._name} at {bt.utils.num2date(order.executed.dt)}\n\t price: {order.executed.price}, size: {order.executed.size}")
            else:
                self.lines.sell[0] = order.executed.price
                self.send_message(
                    f"Sell {order.data._name} at {bt.utils.num2date(order.executed.dt)}\n\t price: {order.executed.price}, size: {order.executed.size}")

    def send_message(self, msg):
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage?chat_id={self.chat_id}&text={msg}"
            print(requests.get(url).json())
        except Exception as e:
            print("send_message error: ", e)
