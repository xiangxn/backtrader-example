import datetime
import logging
import logging.handlers
import sys
from .helper import b64_u_decode, get_email


class Logger(object):

    def __init__(self, name="console", debug=False, screen=False, email: dict = None, secure=()):
        self.is_debug = debug
        self.path_prefix = f"logs/{name}"
        self.logger = logging.getLogger("%s_logger" % name)
        if not email:
            email = get_email()
            if not email['user']:
                email = None
        if self.is_debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARNING)
        self.formatter = logging.Formatter("[%(asctime)s %(name)s %(levelname)s]: %(message)s")

        if screen:
            self.print_handle = logging.StreamHandler(sys.stdout)
            self.print_handle.setLevel(logging.DEBUG)
            self.print_handle.setFormatter(self.formatter)
            self.logger.addHandler(self.print_handle)

        if email:
            user = (email['user'], b64_u_decode(email['password']))
            self.email_handle = logging.handlers.SMTPHandler((email['host'], email['port']), email['from'], email['to'], f"{name}_logs", user, secure=secure)
            self.email_handle.setLevel(logging.ERROR)
            self.email_handle.setFormatter(self.formatter)
            self.logger.addHandler(self.email_handle)

        self.err_handler = logging.FileHandler(filename=f"{self.path_prefix}_error.log")
        self.err_handler.setLevel(logging.ERROR)
        self.err_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.err_handler)

        self.debug_handler = logging.handlers.TimedRotatingFileHandler(f"{self.path_prefix}_debug.log",
                                                                       when="midnight",
                                                                       interval=1,
                                                                       backupCount=7,
                                                                       atTime=datetime.time(0, 0, 0, 0))
        self.debug_handler.setLevel(logging.DEBUG)
        self.debug_handler.setFormatter(self.formatter)
        self.logger.addHandler(self.debug_handler)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.logger.exception(msg, *args, exc_info=exc_info, **kwargs)