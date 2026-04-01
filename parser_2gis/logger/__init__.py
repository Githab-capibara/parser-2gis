"""Модуль логирования для парсера.

Предоставляет компоненты для логирования:
- Logger, logger - основной логгер
- QueueHandler - обработчик очереди
- FileLogger - файловый логгер (импорт из logger/handlers.py)
- VisualLogger - визуальный логгер с emoji и цветами
- LogOptions - опции логирования
- Функции настройки: setup_logger, setup_cli_logger, setup_gui_logger

Примечание:
    FileLogger выделен в отдельный модуль logger/handlers.py для устранения
    циклической зависимости между logger и chrome модулями.
"""

# FileLogger импортируется из выделенного модуля handlers для устранения
# циклической зависимости с chrome модулем
from .handlers import FileLogger
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
    "ColorCodes",
    "Emoji",
    "FileLogger",
    "LogOptions",
    "Logger",
    "QueueHandler",
    "VisualLogger",
    "log_parser_finish",
    "log_parser_start",
    "logger",
    "print_config",
    "print_debug",
    "print_error",
    "print_header",
    "print_info",
    "print_progress",
    "print_stats",
    "print_success",
    "print_warning",
    "setup_cli_logger",
    "setup_gui_logger",
    "setup_logger",
    "visual_logger",
]
