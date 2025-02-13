import logging
import datetime

class NewLineFormatter(logging.Formatter):
    """Adds logging prefix to newlines to align multi-line messages."""

    def __init__(self, fmt, datefmt=None, style="%"):
        logging.Formatter.__init__(self, fmt, datefmt, style)

    def format(self, record):
        msg = logging.Formatter.format(self, record)
        if record.message != "":
            parts = msg.split(record.message)
            msg = msg.replace("\n", "\r\n" + parts[0])
        return msg


class NewLineMicrosecondsFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.datetime.fromtimestamp(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime("%m-%d %H:%M:.%S.%f")