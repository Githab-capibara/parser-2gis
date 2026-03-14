from .logger import (
    QueueHandler,
    logger,
    setup_cli_logger,
    setup_gui_logger,
    setup_logger,
    Logger,
    log_parser_start,
    log_parser_finish,
)
from .options import LogOptions
from .file_handler import FileLogger
from .visual_logger import (
    VisualLogger,
    visual_logger,
    print_header,
    print_config,
    print_progress,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_debug,
    print_stats,
    Emoji,
    ColorCodes,
)


# TUI импорт (ленивый - при необходимости)
def get_tui_app():
    """Получить TUI приложение (ленивый импорт)."""
    from ..tui.app import TUIApp, TUIManager
    return TUIApp, TUIManager


def get_tui_logger():
    """Получить TUI логгер (ленивый импорт)."""
    from ..tui.logger import TUILogger, setup_tui_logger
    return TUILogger, setup_tui_logger


__all__ = [
    "logger",
    "Logger",
    "setup_cli_logger",
    "setup_gui_logger",
    "setup_logger",
    "QueueHandler",
    "LogOptions",
    "FileLogger",
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
    "get_tui_app",
    "get_tui_logger",
]
