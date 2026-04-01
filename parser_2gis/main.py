"""Модуль точки входа CLI для Parser2GIS.

Парсит аргументы командной строки, инициализирует конфигурацию
и запускает CLI приложение.

Backward совместимость:
Этот модуль теперь является обёрткой над parser_2gis.cli
Все импорты из parser_2gis.main продолжают работать.
"""

from __future__ import annotations

# Импортируем все символы из нового пакета cli для backward совместимости
from parser_2gis.cli import ArgumentHelpFormatter, ArgumentValidator, main, parse_arguments

# Импортируем TUI символы для backward совместимости
from parser_2gis.cli.main import Parser2GISTUI, run_new_tui_omsk

# Экспортируем для backward совместимости
__all__ = [
    "ArgumentHelpFormatter",
    "ArgumentValidator",
    "Parser2GISTUI",
    "main",
    "parse_arguments",
    "run_new_tui_omsk",
]
