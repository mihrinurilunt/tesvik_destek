"""
Tüm servislerde aynı log formatını kullanmak için ortak logger ayarıdır.

Her servisin log formatı aynı olursa Docker Compose çıktısında hangi serviste
ne olduğunu takip etmek daha kolay olur.
"""

import logging
import sys

from shared.config import settings


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(settings.LOG_LEVEL.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.LOG_LEVEL.upper())

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False

    return logger