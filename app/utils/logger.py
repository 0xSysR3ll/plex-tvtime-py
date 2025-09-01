"""
This module provides a ColoredFormatter class for colored logging output.
"""

import logging

from termcolor import colored


class ColoredFormatter(logging.Formatter):
    """
    This class provides a formatter for logging output with colors.
    """

    COLORS = {
        "WARNING": "yellow",
        "INFO": "white",
        "DEBUG": "blue",
        "CRITICAL": "red",
        "ERROR": "red",
    }

    def format(self, record):
        """
        Formats the log record with colors based on the log level.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted log record.
        """
        colored_record = record
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = colored(levelname, self.COLORS[levelname])
            colored_record.levelname = colored_levelname
        return super().format(colored_record)


def setup_logging():
    """
    This function sets up the logging configuration.
    """
    loggers = logging.Logger.manager.loggerDict
    for name in loggers:
        logging.getLogger(name).setLevel(logging.WARNING)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    formatter = ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)

    logger.addHandler(ch)
