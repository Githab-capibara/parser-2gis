from __future__ import annotations

import json
from typing import Any

from ...logger import logger
from .file_writer import FileWriter


class JSONWriter(FileWriter):
    """Писатель в JSON файл."""
    def __enter__(self) -> JSONWriter:
        super().__enter__()
        self._wrote_count = 0
        self._items: list[dict[str, Any]] = []  # Собираем элементы в список для валидного JSON
        return self

    def __exit__(self, *exc_info) -> None:
        # Записываем весь список одним вызовом json.dump для гарантии валидного JSON
        json.dump(self._items, self._file, ensure_ascii=False, indent=2)
        super().__exit__(*exc_info)

    def _writedoc(self, catalog_doc: Any) -> None:
        """Добавляет документ в список для последующей записи в JSON.

        Args:
            catalog_doc: JSON-документ Catalog Item API.
        """
        item = catalog_doc['result']['items'][0]

        if self._options.verbose:
            try:
                name = item['name_ex']['primary']
            except KeyError:
                name = '...'

            logger.info('Парсинг [%d] > %s', self._wrote_count + 1, name)

        # Добавляем элемент в список вместо ручной записи
        self._items.append(item)
        self._wrote_count += 1

    def write(self, catalog_doc: Any) -> None:
        """Записывает JSON-документ Catalog Item API в JSON файл.

        Args:
            catalog_doc: JSON-документ Catalog Item API.
        """
        if not self._check_catalog_doc(catalog_doc):
            return

        self._writedoc(catalog_doc)
