"""Модуль логирования для парсера.

Предоставляет компоненты для логирования:
- Logger, logger - основной логгер
- QueueHandler - обработчик очереди
- FileLogger - файловый логгер (ленивый импорт)
- VisualLogger - визуальный логгер с emoji и цветами
- LogOptions - опции логирования
- Функции настройки: setup_logger, setup_cli_logger, setup_gui_logger
"""

# FileLogger импортируется лениво для избежания циклического импорта
# Явный импорт невозможен из-за циклической зависимости с chrome.file_handler

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


def __getattr__(name: str):
    """Ленивый импорт FileLogger для избежания циклического импорта.
    
    PEP 562 позволяет определять __getattr__ на уровне модуля.
    """
    if name == "FileLogger":
        from parser_2gis.chrome.file_handler import FileLogger

        return FileLogger
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    "__getattr__",  # Для ленивого импорта FileLogger (PEP 562)
]
