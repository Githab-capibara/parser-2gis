"""Обработчик слияния CSV файлов.

ISSUE-025: Выделен из parallel/merger.py для соблюдения SRP.
Отвечает исключительно за логику обработки и объединения CSV файлов.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

from parser_2gis.constants import MERGE_BATCH_SIZE, MERGE_BUFFER_SIZE
from parser_2gis.parallel.filename_utils import extract_category_from_filename


class MergeCSVHandler:
    """Обработка и слияние CSV файлов.

    Отвечает за:
    - Чтение CSV файлов и извлечение категории из имени файла
    - Добавление колонки "Категория" к данным
    - Пакетную записи с буферизацией
    - Управление кэшем fieldnames
    """

    def __init__(
        self,
        log_callback: Callable[[str, str], None] | None = None,
        buffer_size: int = MERGE_BUFFER_SIZE,
        batch_size: int = MERGE_BATCH_SIZE,
    ) -> None:
        """Инициализирует обработчик CSV.

        Args:
            log_callback: Функция логирования (message, level).
            buffer_size: Размер буфера в байтах.
            batch_size: Размер пакета строк для записи.

        """
        self._log_callback = log_callback
        self._buffer_size = buffer_size
        self._batch_size = batch_size

    def _log(self, message: str, level: str = "debug") -> None:
        """Логирует сообщение."""
        if self._log_callback:
            self._log_callback(message, level)

    def extract_category_from_filename(self, csv_file: Path) -> str:
        """Извлекает название категории из имени CSV файла."""
        return extract_category_from_filename(csv_file, log_func=self._log)

    def process_single_csv_file(
        self,
        csv_file: Path,
        writer: csv.DictWriter | None,
        outfile: TextIO,
        fieldnames_cache: dict[tuple[str, ...], list[str]],
    ) -> tuple[csv.DictWriter | None, int]:
        """Обрабатывает один CSV файл и добавляет данные в выходной файл.

        Args:
            csv_file: Путь к исходному CSV файлу.
            writer: Текущий CSV writer.
            outfile: Выходной файл.
            fieldnames_cache: Кэш полей для файлов.

        Returns:
            Кортеж (writer, total_rows).

        """
        category_name = self.extract_category_from_filename(csv_file)

        with open(csv_file, encoding="utf-8-sig", newline="", buffering=self._buffer_size) as infile:
            reader = csv.DictReader(infile)

            if not reader.fieldnames:
                self._log(f"Файл {csv_file} пуст или не имеет заголовков", "warning")
                return writer, 0

            fieldnames_key = tuple(reader.fieldnames)
            if fieldnames_key not in fieldnames_cache:
                fieldnames = list(reader.fieldnames)
                if "Категория" not in fieldnames:
                    fieldnames.insert(0, "Категория")
                fieldnames_cache[fieldnames_key] = fieldnames
            else:
                fieldnames = fieldnames_cache[fieldnames_key]

            if writer is None:
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                writer.writeheader()

            batch = []
            batch_total = 0

            for row in reader:
                row_with_category = {"Категория": category_name, **row}
                batch.append(row_with_category)

                if len(batch) >= self._batch_size:
                    writer.writerows(batch)
                    batch_total += len(batch)
                    batch.clear()

            if batch:
                writer.writerows(batch)
                batch_total += len(batch)

            batch_count = (batch_total // self._batch_size) + (1 if batch_total % self._batch_size else 0)
            self._log(
                f"Файл {csv_file.name} обработан (строк: {batch_total}, пакетов: {batch_count})",
                "debug",
            )

            return writer, batch_total
