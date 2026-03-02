from __future__ import annotations

import re

from pydantic import BaseModel, validator


class LogOptions(BaseModel):
    # Строка формата (процентный стиль)
    gui_format: str = '%(asctime)s.%(msecs)03d | %(message)s'
    cli_format: str = '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s'

    # Формат даты
    gui_datefmt: str = '%H:%M:%S'
    cli_datefmt: str = '%d/%m/%Y %H:%M:%S'

    # Уровень
    level: str = 'INFO'

    @validator('level')
    def level_validation(cls, v: str) -> str:
        v = v.upper()
        if v not in ('ERROR', 'WARNING', 'WARN', 'INFO',
                     'DEBUG', 'FATAL', 'CRITICAL', 'NOTSET'):
            raise ValueError('Level name not found')

        return v

    @validator('gui_format', 'cli_format')
    def format_validation(cls, v: str) -> str:
        """Проверяет строку формата в процентном стиле."""
        fmt_match = re.match(r'%\(\w+\)[#0+ -]*(\*|\d+)?(\.(\*|\d+))?[diouxefgcrsa%]', v, re.I)
        if not fmt_match:
            raise ValueError('Format string is invalid')

        return v
