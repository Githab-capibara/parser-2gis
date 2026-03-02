from __future__ import annotations

import re

from pydantic import BaseModel
try:
    from pydantic import field_validator
    PYDANTIC_V2 = True
except ImportError:
    from pydantic import validator
    PYDANTIC_V2 = False


class LogOptions(BaseModel):
    # Строка формата (процентный стиль)
    gui_format: str = '%(asctime)s.%(msecs)03d | %(message)s'
    cli_format: str = '%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s'

    # Формат даты
    gui_datefmt: str = '%H:%M:%S'
    cli_datefmt: str = '%d/%m/%Y %H:%M:%S'

    # Уровень по умолчанию DEBUG для тестов
    level: str = 'DEBUG'

    if PYDANTIC_V2:
        @field_validator('level')
        @classmethod
        def level_validation(cls, v: str) -> str:
            v = v.upper()
            if v not in ('ERROR', 'WARNING', 'WARN', 'INFO',
                         'DEBUG', 'FATAL', 'CRITICAL', 'NOTSET'):
                raise ValueError('Неверное имя уровня логирования')

            return v

        @field_validator('gui_format', 'cli_format')
        @classmethod
        def format_validation(cls, v: str) -> str:
            """Проверяет строку формата в процентном стиле."""
            # Упрощённая проверка: строка должна содержать %(...) и спецификатор формата
            if not re.search(r'%\(\w+\)[#0+ \-]*(\*|\d+)?(\.(\*|\d+))?[diouxefgcrsa%]', v):
                raise ValueError('Строка формата неверна')

            return v
    else:
        @validator('level')
        def level_validation(cls, v: str) -> str:
            v = v.upper()
            if v not in ('ERROR', 'WARNING', 'WARN', 'INFO',
                         'DEBUG', 'FATAL', 'CRITICAL', 'NOTSET'):
                raise ValueError('Неверное имя уровня логирования')

            return v

        @validator('gui_format', 'cli_format')
        def format_validation(cls, v: str) -> str:
            """Проверяет строку формата в процентном стиле."""
            # Упрощённая проверка: строка должна содержать %(...) и спецификатор формата
            if not re.search(r'%\(\w+\)[#0+ \-]*(\*|\d+)?(\.(\*|\d+))?[diouxefgcrsa%]', v):
                raise ValueError('Строка формата неверна')

            return v
