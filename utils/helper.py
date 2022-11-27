import os
import re
import base64
from dotenv import find_dotenv, load_dotenv

B64ULOOKUP = { "/": "_", "_": "/", "+": "-", "-": "+", "=": ".", ".": "=", "N": 'p', "p": 'N'}


def b64_u_decode(value: str) -> str:
    v = re.sub(r"(-|_|\.)", lambda m: B64ULOOKUP[m.group(0)], value)
    return base64.b64decode(v).decode()


def b64_u_encode(value: str) -> str:
    v = base64.b64encode(value.encode()).decode()
    return re.sub(r"(\+|\/|=)", lambda m: B64ULOOKUP[m.group(0)], v)


def init_env():
    load_dotenv(find_dotenv())


def get_env(key, default=''):
    return os.environ.get(key, default=default)


def get_email():
    email = {
        "host": get_env("EMAIL_HOST"),
        "port": get_env("EMAIL_PORT"),
        "from": get_env("EMAIL_FROM"),
        "to": get_env("EMAIL_TO"),
        "user": get_env("EMAIL_USER"),
        "password": get_env("EMAIL_PASSWORD")
    }
    return email
