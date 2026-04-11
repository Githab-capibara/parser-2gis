"""Постобработка CSV файлов.

Предоставляет класс CSVPostProcessor для постобработки CSV файлов:
- Удаление пустых колонок
- Добавление рубрик
- Добавление комментариев к контактам

#72: Логика использования mmap аналогична csv_deduplicator.py.
Рефакторинг отложен — оба файла используют общие утилиты из csv_buffer_manager.py.
"""

from __future__ import annotations

import csv
import os
import re
from re import Pattern
from typing import Any

from parser_2gis.constants import CSV_BATCH_SIZE
from parser_2gis.logger import logger

from .csv_buffer_manager import _calculate_optimal_buffer_size, _safe_move_file, mmap_file_context

# Константы
TRAILING_NUMBER_PATTERN: Pattern[str] = re.compile(r"\s+\d+$")
"""Паттерн для удаления суффикса с цифрами из названия колонки."""


class CSVPostProcessor:
    """Класс для постобработки CSV файлов."""

    def __init__(
        self,
        file_path: str,
        data_mapping: dict[str, Any],
        complex_mapping: dict[str, Any],
        encoding: str = "utf-8",
    ) -> None:
        """Инициализация постпроцессора.

        Args:
            file_path: Путь к CSV файлу.
            data_mapping: Маппинг данных CSV.
            complex_mapping: Маппинг сложных полей (phone, email, и т.д.).
            encoding: Кодировка файла.

        """
        self._file_path = file_path
        self._data_mapping = data_mapping
        self._complex_mapping = complex_mapping
        self._encoding = encoding

    def _build_complex_columns_pattern(self) -> Pattern[str] | None:
        """Строит regex-паттерн для сложных колонок.

        Returns:
            Скомпилированный паттерн или None.

        """
        complex_columns = list(self._complex_mapping.keys())
        if not complex_columns:
            return None
        pattern_str = r"^(?:" + "|".join(rf"{x}_\d+" for x in complex_columns) + r")$"
        return re.compile(pattern_str)

    def _count_complex_columns(
        self, complex_columns_pattern: Pattern[str] | None
    ) -> dict[str, int]:
        """Подсчитывает непустые значения в сложных колонках.

        Args:
            complex_columns_pattern: Скомпилированный паттерн.

        Returns:
            Словарь с подсчётом непустых значений.

        """
        complex_columns_count: dict[str, int] = {}
        if complex_columns_pattern is None:
            return complex_columns_count

        for c in self._data_mapping:
            if complex_columns_pattern.match(c):
                complex_columns_count[c] = 0

        try:
            with mmap_file_context(self._file_path, "r", encoding="utf-8-sig") as (f_csv, _, _):
                csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())

                if csv_reader.fieldnames is None or len(csv_reader.fieldnames) == 0:
                    logger.warning(
                        "Файл %s пуст или не имеет заголовков. Пропускаем подсчёт колонок.",
                        self._file_path,
                    )
                    return complex_columns_count

                for row in csv_reader:
                    for column_name in complex_columns_count:
                        if row.get(column_name, "") != "":
                            complex_columns_count[column_name] += 1

        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError) as e:
            logger.error("Ошибка при чтении CSV для анализа колонок: %s", e)
            raise

        return complex_columns_count

    def _generate_new_mapping(self, complex_columns_count: dict[str, int]) -> dict[str, Any]:
        """Генерирует новый маппинг без пустых колонок.

        Args:
            complex_columns_count: Подсчёт заполненных сложных колонок.

        Returns:
            Новый маппинг данных.

        """
        new_data_mapping: dict[str, Any] = {}
        for k, v in self._data_mapping.items():
            # Добавляем колонку если она не в complex_columns_count или если count > 0
            if k not in complex_columns_count or complex_columns_count[k] > 0:
                new_data_mapping[k] = v

        # Переименование одиночной сложной колонки
        complex_columns = list(self._complex_mapping.keys())
        for column in complex_columns:
            col_1 = f"{column}_1"
            col_2 = f"{column}_2"
            if col_1 in new_data_mapping and col_2 not in new_data_mapping:
                new_data_mapping[col_1] = TRAILING_NUMBER_PATTERN.sub("", new_data_mapping[col_1])

        return new_data_mapping

    def _write_filtered_csv(self, new_data_mapping: dict[str, Any], tmp_csv_name: str) -> None:
        """Записывает CSV с отфильтрованными колонками во временный файл.

        Args:
            new_data_mapping: Новый маппинг данных.
            tmp_csv_name: Имя временного файла.

        """
        file_size = os.path.getsize(self._file_path) if os.path.exists(self._file_path) else 0
        optimal_write_buffer = _calculate_optimal_buffer_size(file_size_bytes=file_size)

        with mmap_file_context(self._file_path, "r", encoding="utf-8-sig") as (f_csv, _, _):
            f_tmp_csv = None
            try:
                f_tmp_csv = open(
                    tmp_csv_name,
                    "w",
                    newline="",
                    buffering=optimal_write_buffer,
                    encoding=self._encoding,
                )

                csv_writer = csv.DictWriter(f_tmp_csv, new_data_mapping.keys())
                csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())

                if csv_reader.fieldnames is None or len(csv_reader.fieldnames) == 0:
                    logger.warning(
                        "Файл %s пуст или не имеет заголовков. Пропускаем обработку.",
                        self._file_path,
                    )
                    return

                csv_writer.writerow(new_data_mapping)

                batch: list[dict[str, Any]] = []
                batch_size = CSV_BATCH_SIZE
                total_batches = 0

                for row in csv_reader:
                    new_row = {k: v for k, v in row.items() if k in new_data_mapping}
                    batch.append(new_row)

                    if len(batch) >= batch_size:
                        csv_writer.writerows(batch)
                        total_batches += 1
                        batch.clear()

                if batch:
                    csv_writer.writerows(batch)
                    total_batches += 1

                logger.debug(
                    "Запись CSV завершена (всего пакетов: %d, размер пакета: %d)",
                    total_batches,
                    batch_size,
                )
            finally:
                if f_tmp_csv is not None and not f_tmp_csv.closed:
                    f_tmp_csv.close()

    def remove_empty_columns(self) -> None:
        """Удаляет пустые колонки из CSV файла.

        #195: Добавлена проверка расширения файла.

        Оптимизация:
        - Увеличенная буферизация чтения/записи (256KB)
        - mmap для больших файлов (>10MB) вместо обычной буферизации
        - Пакетная запись строк для снижения накладных расходов
        - Предварительное вычисление regex паттерна
        - Проверка размера файла и выбор оптимального метода чтения

        Raises:
            ValueError: Если файл не имеет расширение .csv.

        Примечание:
            Функция анализирует все строки CSV и удаляет колонки,
            которые не содержат данных (за исключением сложных колонок,
            таких как phone_1, phone_2 и т.д.).

            Для файлов >10MB используется mmap для экономии памяти.
            Для файлов <=10MB используется обычная буферизация.

        """
        # #195: Проверка расширения файла
        if not str(self._file_path).endswith(".csv"):
            raise ValueError(f"Файл должен иметь расширение .csv, получен {self._file_path}")

        # ISSUE-088: Используем выделенные методы для анализа колонок
        complex_columns_pattern = self._build_complex_columns_pattern()
        complex_columns_count = self._count_complex_columns(complex_columns_pattern)

        # Генерация нового маппинга
        new_data_mapping = self._generate_new_mapping(complex_columns_count)

        # Создание временного файла
        file_root, file_ext = os.path.splitext(self._file_path)
        tmp_csv_name = f"{file_root}.removed-columns{file_ext}"
        temp_created = False

        try:
            # ISSUE-088: Используем выделенный метод для записи
            self._write_filtered_csv(new_data_mapping, tmp_csv_name)
            temp_created = True

            # Замена оригинального файла новым
            move_success = _safe_move_file(tmp_csv_name, self._file_path)
            if move_success:
                logger.info("Удалены пустые колонки из CSV")
                temp_created = False
            else:
                logger.error("Не удалось переместить файл с удалёнными колонками")
                raise RuntimeError("Failed to move file with removed columns")

        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError) as e:
            logger.error("Ошибка при записи CSV без пустых колонок: %s", e)
            raise
        finally:
            if temp_created and os.path.exists(tmp_csv_name):
                try:
                    os.remove(tmp_csv_name)
                    logger.debug("Временный файл удалён в блоке finally: %s", tmp_csv_name)
                except OSError as cleanup_error:
                    logger.warning(
                        "Не удалось удалить временный файл %s: %s", tmp_csv_name, cleanup_error
                    )
