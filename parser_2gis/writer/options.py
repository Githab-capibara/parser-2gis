"""Модуль опций writer.

Предоставляет классы для настройки параметров записи:
- CSVOptions - опции для CSV Writer
- WriterOptions - общие опции для File Writer
"""

from __future__ import annotations

import codecs

from pydantic import BaseModel, Field, field_validator

from parser_2gis.constants import CSV_COLUMNS_PER_ENTITY

PYDANTIC_V2 = True


class CSVOptions(BaseModel):
    """Опции для CSV Writer.

    Атрибуты:
        add_rubrics: Добавлять колонку "Рубрики".
        add_comments: Добавлять комментарии к сложным колонкам (телефоны, email и т.д.).
        columns_per_entity: Количество колонок для множественных значений.
        remove_empty_columns: Удалять пустые колонки после парсинга.
        remove_duplicates: Удалять дубликаты после парсинга.
        join_char: Разделитель для комплексных значений.
    """

    add_rubrics: bool = True
    add_comments: bool = True
    columns_per_entity: int = Field(CSV_COLUMNS_PER_ENTITY, gt=0, le=CSV_COLUMNS_PER_ENTITY)
    remove_empty_columns: bool = True
    remove_duplicates: bool = True
    join_char: str = "; "


class WriterOptions(BaseModel):
    """Опции для File Writer.

    Атрибуты:
       encoding: Кодировка выходного файла.
       verbose: Выводить названия элементов парсинга.
    """

    encoding: str = "utf-8-sig"
    verbose: bool = True
    csv: CSVOptions = CSVOptions(columns_per_entity=CSV_COLUMNS_PER_ENTITY)

    @staticmethod
    def _validate_encoding(v: str) -> str:
        """Проверяет существование кодировки."""
        try:
            codecs.lookup(v)
        except LookupError as lookup_err:
            msg = f"Неизвестная кодировка: {v}"
            raise ValueError(msg) from lookup_err
        return v

    @field_validator("encoding")
    @classmethod
    def encoding_exists(cls, v: str) -> str:
        """Проверяет существование и валидность кодировки."""
        return cls._validate_encoding(v)
