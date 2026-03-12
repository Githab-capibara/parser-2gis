"""
Модуль TUI для Parser2GIS.

Предоставляет современный текстовый интерфейс с прогресс-барами,
панелями статистики и логами в реальном времени.
"""

from .app import TUIApp, TUIManager
from .components import (
    ProgressPanel,
    StatsPanel,
    LogPanel,
    HeaderPanel,
    create_main_layout,
    TUIState,
    TUIComponents,
)
from .logger import TUILogger, setup_tui_logger
from .parallel import TUIParallelParserWrapper, run_parallel_with_tui

__all__ = [
    "TUIApp",
    "TUIManager",
    "ProgressPanel",
    "StatsPanel",
    "LogPanel",
    "HeaderPanel",
    "create_main_layout",
    "TUILogger",
    "setup_tui_logger",
    "TUIState",
    "TUIComponents",
    "TUIParallelParserWrapper",
    "run_parallel_with_tui",
]
