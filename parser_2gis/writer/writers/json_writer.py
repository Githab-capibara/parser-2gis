"""Писатель в JSON файл.

Предоставляет класс JSONWriter для потоковой записи данных в JSON формат:
- Запись в режиме streaming для экономии памяти
- Поддержка больших объёмов данных без переполнения памяти
"""

from __future__ import annotations

import json
from typing import Any

from ...logger import logger
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

    def __exit__(self, *exc_info) -> None:
        # Записываем закрывающую скобку массива
        self._file.write("\n]")
        super().__exit__(*exc_info)

    def _writedoc(self, catalog_doc: Any) -> None:
        """Добавляет документ в JSON файл.

        Args:
            catalog_doc: JSON-документ Catalog Item API.
        """
        item = catalog_doc["result"]["items"][0]

        if self._options.verbose:
            try:
                name = item["name_ex"]["primary"]
            except KeyError:
                name = "..."

            logger.info("Парсинг [%d] > %s", self._wrote_count + 1, name)

        # Записываем элемент сразу в файл для экономии памяти
        if not self._first_item:
            self._file.write(",\n")
        json.dump(item, self._file, ensure_ascii=False, indent=2)
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
