"""
Модуль точки входа CLI для Parser2GIS.

Парсит аргументы командной строки, инициализирует конфигурацию
и запускает CLI приложение.

Backward совместимость:
Этот модуль теперь является обёрткой над parser_2gis.cli
Все импорты из parser_2gis.main продолжают работать.
"""

from __future__ import annotations

# Импортируем все символы из нового пакета cli для backward совместимости
from parser_2gis.cli import ArgumentHelpFormatter, ArgumentValidator, main, parse_arguments

# Импортируем TUI символы и cleanup_resources для backward совместимости с тестами
from parser_2gis.cli.main import (
    Parser2GISTUI,
    _get_signal_handler_cached,
    _tui_omsk_stub,
    _tui_stub,
    cleanup_resources,
    run_new_tui_omsk,
)

# Экспортируем для backward совместимости
__all__ = [
    "main",
    "parse_arguments",
    "ArgumentValidator",
    "ArgumentHelpFormatter",
    "Parser2GISTUI",
    "_tui_omsk_stub",
    "_tui_stub",
    "run_new_tui_omsk",
    "_get_signal_handler_cached",
    "cleanup_resources",
]
