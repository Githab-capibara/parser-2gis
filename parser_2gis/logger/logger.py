from __future__ import annotations

import logging
import os
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .options import LogOptions
    import queue


# Устанавливаем уровень логирования для сторонних библиотек
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("pychrome").setLevel(logging.ERROR)
warnings.filterwarnings(action="ignore", module="pychrome")

_LOGGER_NAME = "parser-2gis"


class QueueHandler(logging.Handler):
    def __init__(self, log_queue: queue.Queue[tuple[str, str]]) -> None:
        super().__init__()
        self._log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        log_message = (record.levelname, self.format(record) + os.linesep)
        self._log_queue.put(log_message)


def setup_gui_logger(
    log_queue: queue.Queue[tuple[str, str]], options: LogOptions
) -> None:
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
Logger = logging.Logger


def log_parser_start(
    version: str,
    urls_count: int,
    output_path: str,
    format: str,
    config_summary: dict | None = None,
) -> None:
    """
    Логирует запуск парсера с подробной информацией.

    Args:
        version: Версия парсера.
        urls_count: Количество URL для парсинга.
        output_path: Путь к выходному файлу.
        format: Формат выходного файла.
        config_summary: Краткая сводка конфигурации.
    """
    from .visual_logger import print_header, print_config, Emoji

    # Заголовок
    print_header(
        f"{Emoji.START} Parser2GIS запущен",
        subtitle=f"Версия: {version}",
    )

    # Основная информация
    main_info = {
        "URL для парсинга": str(urls_count),
        "Выходной файл": output_path,
        "Формат": format.upper(),
    }
    print_config("📋 Основная информация", main_info)

    # Конфигурация браузера
    if config_summary:
        if "chrome" in config_summary:
            print_config("🌐 Браузер", config_summary["chrome"])

        if "parser" in config_summary:
            print_config("🔎 Парсер", config_summary["parser"])

        if "writer" in config_summary:
            print_config("📄 Writer", config_summary["writer"])


def log_parser_finish(
    success: bool = True,
    stats: dict | None = None,
    duration: str | None = None,
) -> None:
    """
    Логирует завершение парсера.

    Args:
        success: Успешно ли завершено.
        stats: Статистика работы.
        duration: Продолжительность работы.
    """
    from .visual_logger import print_header, print_stats, print_success, print_error, Emoji

    emoji = Emoji.SUCCESS if success else Emoji.ERROR
    title = f"{emoji} Парсинг завершён"

    if success:
        print_success("Парсинг успешно завершён!")
    else:
        print_error("Парсинг завершён с ошибками")

    # Статистика
    if stats:
        if duration:
            stats["Время работы"] = duration
        print_stats(stats, title="📊 Итоговая статистика")

    print_header(title)
