"""Модуль логирования для парсера.

Предоставляет компоненты для логирования:
- Logger, logger - основной логгер
- QueueHandler - обработчик очереди
- FileLogger - файловый логгер (импорт из parser_2gis.logging)
- VisualLogger - визуальный логгер с emoji и цветами
- LogOptions - опции логирования
- Функции настройки: setup_logger, setup_cli_logger, setup_gui_logger

Примечание:
    FileLogger выделен в отдельный модуль parser_2gis.logging для устранения
    циклической зависимости между logger и chrome модулями.
"""

# FileLogger импортируется из выделенного модуля logging для устранения
# циклической зависимости с chrome модулем
from parser_2gis.logging import FileLogger

from .logger import (
    Logger,
    QueueHandler,
    log_parser_finish,
    log_parser_start,
    logger,
    setup_cli_logger,
    setup_gui_logger,
    setup_logger,
)
from .options import LogOptions
from .visual_logger import (
    ColorCodes,
    Emoji,
    VisualLogger,
    print_config,
    print_debug,
    print_error,
    print_header,
    print_info,
    print_progress,
    print_stats,
    print_success,
    print_warning,
    visual_logger,
)

__all__ = [
    "logger",
    "Logger",
    "setup_cli_logger",
    "setup_gui_logger",
    "setup_logger",
    "QueueHandler",
    "LogOptions",
    "VisualLogger",
    "visual_logger",
    "print_header",
    "print_config",
    "print_progress",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_debug",
    "print_stats",
    "Emoji",
    "ColorCodes",
    "log_parser_start",
    "log_parser_finish",
    "FileLogger",
]
