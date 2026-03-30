"""
Модуль для файлового логирования.

Этот модуль перенаправляет импорты в parser_2gis.logging.handlers
для устранения циклической зависимости.

Примечание:
    FileLogger был перемещён в parser_2gis.logging.handlers.
    Этот модуль оставлен для обратной совместимости.
"""

# Перенаправляем импорт из выделенного модуля logging
from parser_2gis.logging.handlers import FileLogger

__all__ = ["FileLogger"]
