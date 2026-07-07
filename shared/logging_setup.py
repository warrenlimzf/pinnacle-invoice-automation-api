"""Simple logging: writes to logs/automation.log AND shows in the console window,
so your colleague can see what happened (and we can debug from the log file)."""
import logging
from logging.handlers import RotatingFileHandler

import config

_CONFIGURED = False


def get_logger(name: str) -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(name)s  %(message)s")

        file_h = RotatingFileHandler(
            config.LOGS_DIR / "automation.log",
            maxBytes=2_000_000, backupCount=5, encoding="utf-8",
        )
        file_h.setFormatter(fmt)

        console_h = logging.StreamHandler()
        console_h.setFormatter(fmt)

        root = logging.getLogger()
        root.setLevel(logging.INFO)
        root.addHandler(file_h)
        root.addHandler(console_h)
        _CONFIGURED = True

    return logging.getLogger(name)
