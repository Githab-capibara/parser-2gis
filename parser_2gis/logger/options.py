"""Модуль опций логирования.

Предоставляет класс LogOptions для настройки параметров логирования:
- Форматы сообщений для GUI/CLI
- Уровни логирования
- Настройки цветов и emoji
"""

from __future__ import annotations

import re

from pydantic import BaseModel, field_validator


class LogOptions(BaseModel):
    """Опции логирования.

    Атрибуты:
        gui_format: Формат сообщений для GUI.
        cli_format: Формат сообщений для CLI.
        gui_datefmt: Формат даты для GUI.
        cli_datefmt: Формат даты для CLI.
        file_format: Формат сообщений для файла.
        _file_datefmt: Формат даты для файла.
        level: Уровень логирования.
        use_colors: Использовать ли цвета в выводе (None = авто).
        use_emoji: Использовать ли emoji.
    """

    gui_format: str = "%(asctime)s.%(msecs)03d | %(message)s"
    cli_format: str = "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(message)s"
    gui_datefmt: str = "%H:%M:%S"
    cli_datefmt: str = "%d/%m/%Y %H:%M:%S"
    file_format: str = "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    _file_datefmt: str = "%Y-%m-%d %H:%M:%S"
    level: str = "DEBUG"
    use_colors: bool | None = None  # None = автоматически
    use_emoji: bool = True

    @staticmethod
    def _validate_level(v: str) -> str:
        """Валидирует уровень логирования."""
        v = v.upper()
        if v not in ("ERROR", "WARNING", "WARN", "INFO", "DEBUG", "FATAL", "CRITICAL", "NOTSET"):
            msg = "Неверное имя уровня логирования"
            raise ValueError(msg)
        return v

    @staticmethod
    def _validate_format(v: str) -> str:
        """Проверяет строку формата в процентном стиле."""
        if not re.search(r"%\(\w+\)[#0+ \-]*(\*|\d+)?(\.(\*|\d+))?[diouxefgcrsa%]", v):
            msg = "Строка формата неверна"
            raise ValueError(msg)
        return v

    @field_validator("level")
    @classmethod
    def _level_validation(cls, v: str) -> str:
        """Валидатор уровня логирования."""
        return cls._validate_level(v)

    @field_validator("gui_format", "cli_format")
    @classmethod
    def _format_validation(cls, v: str) -> str:
        """Валидатор формата строк."""
        return cls._validate_format(v)
