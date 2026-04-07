"""Модуль обратной совместимости.

Реэкспортирует основные компоненты из parser_2gis.cli
для обеспечения обратной совместимости со старыми импортами.

Backward совместимость:
Этот модуль теперь является обёрткой над parser_2gis.cli
Все импорты из parser_2gis.main продолжают работать.
"""

from __future__ import annotations

# Импортируем все символы из нового пакета cli для backward совместимости
from parser_2gis.cli import ArgumentHelpFormatter, ArgumentValidator, main, parse_arguments

# Экспортируем для backward совместимости
__all__ = ["ArgumentHelpFormatter", "ArgumentValidator", "main", "parse_arguments"]
