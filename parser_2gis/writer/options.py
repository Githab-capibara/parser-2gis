from __future__ import annotations

import codecs

from pydantic import BaseModel, Field
try:
    from pydantic import field_validator
    PYDANTIC_V2 = True
except ImportError:
    from pydantic import validator
    PYDANTIC_V2 = False


class CSVOptions(BaseModel):
    """Представляет все возможные опции для CSV Writer.

    Атрибуты:
        add_rubrics: Добавлять ли рубрики в csv или нет.
        add_comments: Добавлять комментарии к сложным колонкам (телефоны, email и т.д.)
            с дополнительной информацией, часами работы.
        columns_per_entity: Количество колонок для результата с несколькими возможными значениями.
        remove_empty_columns: Удалять пустые колонки после завершения процесса парсинга.
        remove_duplicates: Удалять дубликаты после завершения процесса парсинга.
        join_char: Символ для объединения сложных значений.
    """
    add_rubrics: bool = True
    add_comments: bool = True
    columns_per_entity: int = Field(3, gt=0, le=5)
    remove_empty_columns: bool = True
    remove_duplicates: bool = True
    join_char: str = '; '


class WriterOptions(BaseModel):
    """Представляет все возможные опции для File Writer.

    Атрибуты:
       encoding: Кодировка выходного документа.
       verbose: Выводить в stdout название элемента парсинга.
    """
    encoding: str = 'utf-8-sig'
    verbose: bool = True
    csv: CSVOptions = CSVOptions()

    if PYDANTIC_V2:
        @field_validator('encoding')
        @classmethod
        def encoding_exists(cls, v: str) -> str:
            """Проверяет существование `encoding`."""
            try:
                codecs.lookup(v)
            except LookupError:
                raise ValueError(f'Неизвестная кодировка: {v}')
            return v
    else:
        @validator('encoding')
        def encoding_exists(cls, v: str) -> str:
            """Проверяет существование `encoding`."""
            try:
                codecs.lookup(v)
            except LookupError:
                raise ValueError
            return v
