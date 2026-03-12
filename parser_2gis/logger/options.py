from __future__ import annotations

import re

from pydantic import BaseModel

try:
    from pydantic import field_validator  # type: ignore[attr-defined]

    PYDANTIC_V2 = True
except ImportError:
    from pydantic import validator

    PYDANTIC_V2 = False


class LogOptions(BaseModel):
    """Опции логирования.

    Атрибуты:
        gui_format: Формат сообщений для GUI.
        cli_format: Формат сообщений для CLI.
        gui_datefmt: Формат даты для GUI.
        cli_datefmt: Формат даты для CLI.
        file_format: Формат сообщений для файла.
        file_datefmt: Формат даты для файла.
        level: Уровень логирования.
        use_colors: Использовать ли цвета в выводе (None = авто).
        use_emoji: Использовать ли emoji.
    """

    gui_format: str = "%(asctime)s.%(msecs)03d | %(message)s"
    cli_format: str = "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s | %(message)s"
    gui_datefmt: str = "%H:%M:%S"
    cli_datefmt: str = "%d/%m/%Y %H:%M:%S"
    file_format: str = "%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
    file_datefmt: str = "%Y-%m-%d %H:%M:%S"
    level: str = "DEBUG"
    use_colors: bool | None = None  # None = автоматически
    use_emoji: bool = True

    @staticmethod
    def _validate_level(v: str) -> str:
        """Валидирует уровень логирования."""
        v = v.upper()
        if v not in (
            "ERROR",
            "WARNING",
            "WARN",
            "INFO",
            "DEBUG",
            "FATAL",
            "CRITICAL",
            "NOTSET",
        ):
            raise ValueError("Неверное имя уровня логирования")
        return v

    @staticmethod
    def _validate_format(v: str) -> str:
        """Проверяет строку формата в процентном стиле."""
        if not re.search(r"%\(\w+\)[#0+ \-]*(\*|\d+)?(\.(\*|\d+))?[diouxefgcrsa%]", v):
            raise ValueError("Строка формата неверна")
        return v

    if PYDANTIC_V2:

        @field_validator("level")
        @classmethod
        def level_validation(cls, v: str) -> str:
            return cls._validate_level(v)

        @field_validator("gui_format", "cli_format")
        @classmethod
        def format_validation(cls, v: str) -> str:
            return cls._validate_format(v)

    else:

        @validator("level")
        def level_validation(cls, v: str) -> str:
            return cls._validate_level(v)

        @validator("gui_format", "cli_format")
        def format_validation(cls, v: str) -> str:
            return cls._validate_format(v)
