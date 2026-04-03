"""Писатель в JSON файл.

Предоставляет класс JSONWriter для потоковой записи данных в JSON формат:
- Запись в режиме streaming для экономии памяти
- Поддержка больших объёмов данных без переполнения памяти
"""

from __future__ import annotations

import json
from typing import Any

from parser_2gis.logger import logger

from .file_writer import FileWriter


class JSONWriter(FileWriter):
    """Писатель в JSON файл.

    Записывает элементы в JSON файл в потоковом режиме для предотвращения
    переполнения памяти при больших объёмах данных.
    """

    def __enter__(self) -> JSONWriter:
        super().__enter__()
        self._wrote_count = 0
        self._first_item = True
        # Записываем открывающую скобку массива
        self._file.write("[\n")
        return self

    def __exit__(self, *exc_info: Any) -> None:
        # Записываем закрывающую скобку массива
        try:
            self._file.write("\n]")
        except OSError as write_error:
            logger.error("Ошибка записи закрывающей скобки JSON: %s", write_error)
            raise
        super().__exit__(*exc_info)

    def _writedoc(self, catalog_doc: Any) -> None:
        """Добавляет документ в JSON файл.

        ISSUE-170: Добавлена обработка json.JSONDecodeError.
        ISSUE-171: Используется буферизация для json.dump().

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        Raises:
            json.JSONDecodeError: При ошибке декодирования JSON.

        """
        if not isinstance(catalog_doc, dict):
            logger.warning("catalog_doc не является словарём, пропускаем")
            return

        result = catalog_doc.get("result")
        if not isinstance(result, dict):
            logger.warning("catalog_doc['result'] отсутствует или не является словарём, пропускаем")
            return

        items = result.get("items")
        if not isinstance(items, list) or len(items) == 0:
            logger.warning(
                "catalog_doc['result']['items'] пуст или не является списком, пропускаем"
            )
            return

        item = items[0]

        if self._options.verbose:
            try:
                name = item["name_ex"]["primary"]
            except KeyError:
                name = "..."

            logger.info("Парсинг [%d] > %s", self._wrote_count + 1, name)

        # Записываем элемент сразу в файл для экономии памяти
        if not self._first_item:
            self._file.write(",\n")

        # ISSUE-170: Обработка JSONDecodeError
        try:
            # ISSUE-171: Буферизация через явный вызов flush после dump
            json.dump(item, self._file, ensure_ascii=False, indent=2)
            self._file.flush()  # Явная буферизация для предотвращения потери данных
        except (TypeError, ValueError, json.JSONDecodeError) as json_error:
            # TypeError: объект не сериализуем в JSON
            # ValueError: объект содержит некорректные данные для JSON
            # json.JSONDecodeError: ошибка декодирования JSON
            logger.error("Ошибка сериализации JSON: %s", json_error)
            raise

        self._first_item = False
        self._wrote_count += 1

    def write(self, catalog_doc: Any) -> None:
        """Записывает JSON-документ Catalog Item API в JSON файл.

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        """
        if not self._check_catalog_doc(catalog_doc):
            return

        self._writedoc(catalog_doc)
