from __future__ import annotations

import logging
import os
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .options import LogOptions
    import queue


# Устанавливаем уровень логирования для сторонних библиотек
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('pychrome').setLevel(logging.FATAL)
warnings.filterwarnings(
    action='ignore',
    module='pychrome'
)

_LOGGER_NAME = 'parser-2gis'


class QueueHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[tuple[str, str]]) -> None:
        super().__init__()
        self._log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        log_message = (record.levelname, self.format(record) + os.linesep)
        self._log_queue.put(log_message)


def setup_gui_logger(log_queue: queue.Queue[tuple[str, str]],
                     options: LogOptions) -> None:
    """Добавляет обработчик очереди к существующему логгеру, чтобы он
    отправлял логи в указанную очередь.

    Args:
        log_queue: Очередь для размещения сообщений логирования.
    """
    formatter = logging.Formatter(options.gui_format, options.gui_datefmt)
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(formatter)
    logger.addHandler(queue_handler)


def setup_cli_logger(options: LogOptions) -> None:
    """Настраивает CLI логгер из конфигурации.

    Args:
        options: Опции логирования.
    """
    setup_logger(
        options.level,
        options.cli_format,
        options.cli_datefmt,
    )


def setup_logger(level: str, fmt: str, datefmt: str) -> None:
    """Настраивает логгер.

    Args:
        level: Уровень логгера.
        fmt: Строка формата в процентном стиле.
        datefmt: Строка формата даты.
    """
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(fmt, datefmt)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.setLevel(level)


logger = logging.getLogger(_LOGGER_NAME)
