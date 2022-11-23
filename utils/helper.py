import os
from dotenv import find_dotenv, load_dotenv


def init_env():
    load_dotenv(find_dotenv())


def get_env(key, default=''):
    return os.environ.get(key, default=default)
