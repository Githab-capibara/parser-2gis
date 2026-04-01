"""Модуль для файлового логирования.

Этот модуль перенаправляет импорты в parser_2gis.logger.handlers
для устранения циклической зависимости.

Примечание:
    FileLogger был перемещён в parser_2gis.logger.handlers.
    Этот модуль оставлен для обратной совместимости.
"""

# Перенаправляем импорт из выделенного модуля handlers
from parser_2gis.logger.handlers import FileLogger

__all__ = ["FileLogger"]
