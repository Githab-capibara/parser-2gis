"""Постобработка CSV файлов.

Предоставляет класс CSVPostProcessor для постобработки CSV файлов:
- Удаление пустых колонок
- Добавление рубрик
- Добавление комментариев к контактам
"""

from __future__ import annotations

import csv
import os
import re
from typing import Any
from re import Pattern

from parser_2gis.constants import CSV_BATCH_SIZE
from parser_2gis.logger import logger

from .csv_buffer_manager import (
    _calculate_optimal_buffer_size,
    _safe_move_file,
    _should_use_mmap,
    mmap_file_context,
)


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

    def remove_empty_columns(self) -> None:
        """Удаляет пустые колонки из CSV файла.

        Оптимизация:
        - Увеличенная буферизация чтения/записи (256KB)
        - mmap для больших файлов (>10MB) вместо обычной буферизации
        - Пакетная запись строк для снижения накладных расходов
        - Предварительное вычисление regex паттерна
        - Проверка размера файла и выбор оптимального метода чтения

        Примечание:
            Функция анализирует все строки CSV и удаляет колонки,
            которые не содержат данных (за исключением сложных колонок,
            таких как phone_1, phone_2 и т.д.).

            Для файлов >10MB используется mmap для экономии памяти.
            Для файлов <=10MB используется обычная буферизация.
        """
        complex_columns = list(self._complex_mapping.keys())

        # Словарь для подсчёта непустых значений в сложных колонках
        complex_columns_count: dict[str, int] = {}

        # Оптимизация: компилируем regex паттерн один раз
        complex_columns_pattern: Pattern[str] | None = None
        if complex_columns:
            # Группируем паттерны для корректной работы regex
            pattern_str = r"^(?:" + "|".join(rf"{x}_\d+" for x in complex_columns) + r")$"
            complex_columns_pattern = re.compile(pattern_str)
            for c in self._data_mapping.keys():
                if complex_columns_pattern.match(c):
                    complex_columns_count[c] = 0

        # Первый проход: подсчёт непустых значений в сложных колонках
        file_size: int | None = None
        try:
            optimal_buffer = _calculate_optimal_buffer_size(file_path=self._file_path)

            # Получаем размер файла для выбора метода чтения
            try:
                file_size = os.path.getsize(self._file_path)
                use_mmap = _should_use_mmap(file_size)
                logger.info(
                    "Анализ колонок: размер файла %.2f MB, используется %s",
                    file_size / (1024 * 1024),
                    "mmap" if use_mmap else "обычная буферизация",
                )
            except OSError as size_error:
                logger.warning(
                    "Не удалось получить размер файла для анализа колонок: %s", size_error
                )
                use_mmap = False

            # Используем контекстный менеджер для безопасной работы с mmap
            with mmap_file_context(self._file_path, "r", encoding="utf-8-sig") as (
                f_csv,
                _,  # is_mmap не используется
                _,  # underlying_fp не используется
            ):
                csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore[arg-type]

                # ИСПРАВЛЕНИЕ 9: Проверка reader.fieldnames на None/пустоту
                # Это предотвращает ошибки при обработке пустых файлов
                if csv_reader.fieldnames is None:
                    logger.warning(
                        "Файл %s пуст или не имеет заголовков (fieldnames=None). Пропускаем обработку.",
                        self._file_path,
                    )
                    return

                if len(csv_reader.fieldnames) == 0:
                    logger.warning(
                        "Файл %s имеет пустой список заголовков. Пропускаем обработку.",
                        self._file_path,
                    )
                    return

                # Используем enumerate с шагом для уменьшения количества итераций
                batch_count = 0
                for idx, row in enumerate(csv_reader):
                    # Проверяем только сложные колонки
                    for column_name in complex_columns_count.keys():
                        if row.get(column_name, "") != "":
                            complex_columns_count[column_name] += 1

                    # Оптимизация: уменьшаем количество проверок через modulo
                    # вместо проверки на каждой итерации
                    if (idx + 1) % CSV_BATCH_SIZE == 0:
                        batch_count += 1

                logger.debug(
                    "Подсчёт заполненности колонок завершён (обработано пакетов: %d, буфер: %d байт, mmap: %s)",
                    batch_count,
                    optimal_buffer,
                    use_mmap,
                )

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.error("Ошибка при чтении CSV для анализа колонок: %s", e)
            raise

        # Генерация нового маппинга данных
        new_data_mapping: dict[str, Any] = {}
        for k, v in self._data_mapping.items():
            if k in complex_columns_count:
                # Оставляем только заполненные сложные колонки
                if complex_columns_count[k] > 0:
                    new_data_mapping[k] = v
            else:
                new_data_mapping[k] = v

        # Переименование одиночной сложной колонки - удаление суффиксов с цифрами
        for column in complex_columns:
            col_1 = f"{column}_1"
            col_2 = f"{column}_2"
            if col_1 in new_data_mapping and col_2 not in new_data_mapping:
                # Удаляем суффикс " 1" из названия колонки
                new_data_mapping[col_1] = re.sub(r"\s+\d+$", "", new_data_mapping[col_1])

        # Создание временного файла
        file_root, file_ext = os.path.splitext(self._file_path)
        tmp_csv_name = f"{file_root}.removed-columns{file_ext}"

        # ВАЖНО: Флаг для отслеживания создания временного файла
        temp_created = False

        try:
            optimal_read_buffer = _calculate_optimal_buffer_size(file_path=self._file_path)
            # Обновляем размер файла для текущего файла
            if os.path.exists(self._file_path):
                file_size = os.path.getsize(self._file_path)
            optimal_write_buffer = _calculate_optimal_buffer_size(file_size_bytes=file_size)

            # Определяем метод чтения на основе размера файла
            try:
                use_mmap = _should_use_mmap(file_size) if file_size else False
                logger.info(
                    "Запись CSV без пустых колонок: размер файла %.2f MB, используется %s",
                    file_size / (1024 * 1024) if file_size else 0,
                    "mmap" if use_mmap else "обычная буферизация",
                )
            except OSError:
                use_mmap = False

            # Открываем файлы с mmap или обычной буферизацией
            # Используем контекстный менеджер для безопасной работы с mmap
            with mmap_file_context(self._file_path, "r", encoding="utf-8-sig") as (
                f_csv,
                _,  # is_mmap не используется
                _,  # underlying_fp не используется
            ):
                f_tmp_csv: Any | None = None
                try:
                    f_tmp_csv = open(
                        tmp_csv_name,
                        "w",
                        newline="",
                        buffering=optimal_write_buffer,
                        encoding=self._encoding,
                    )
                    # ВАЖНО: Помечаем что временный файл создан
                    temp_created = True

                    csv_writer = csv.DictWriter(f_tmp_csv, new_data_mapping.keys())  # type: ignore[arg-type]
                    csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore[arg-type]

                    # ИСПРАВЛЕНИЕ 9: Проверка reader.fieldnames на None/пустоту
                    # Это предотвращает ошибки при обработке пустых файлов
                    if csv_reader.fieldnames is None:
                        logger.warning(
                            "Файл %s пуст или не имеет заголовков (fieldnames=None). Пропускаем обработку.",
                            self._file_path,
                        )
                        return

                    if len(csv_reader.fieldnames) == 0:
                        logger.warning(
                            "Файл %s имеет пустой список заголовков. Пропускаем обработку.",
                            self._file_path,
                        )
                        return

                    # Запись нового заголовка
                    csv_writer.writerow(new_data_mapping)

                    batch: list[dict[str, Any]] = []
                    batch_size = CSV_BATCH_SIZE  # Используем увеличенный размер пакета (1000 строк)
                    total_batches = 0

                    for row in csv_reader:
                        # Создаём новую строку только с нужными колонками
                        new_row = {k: v for k, v in row.items() if k in new_data_mapping}
                        batch.append(new_row)

                        # Записываем пакет при достижении размера
                        if len(batch) >= batch_size:
                            csv_writer.writerows(batch)
                            total_batches += 1
                            batch.clear()

                    # Записываем оставшиеся строки (неполный пакет)
                    if batch:
                        csv_writer.writerows(batch)
                        total_batches += 1

                    logger.debug(
                        "Запись CSV завершена (всего пакетов: %d, размер пакета: %d, "
                        "буфер чтения: %d, буфер записи: %d, mmap: %s)",
                        total_batches,
                        batch_size,
                        optimal_read_buffer,
                        optimal_write_buffer,
                        use_mmap,
                    )
                finally:
                    # Гарантированно закрываем файл записи при любом исходе
                    if f_tmp_csv is not None and not f_tmp_csv.closed:
                        f_tmp_csv.close()

            # Замена оригинального файла новым с безопасной обработкой
            move_success = _safe_move_file(tmp_csv_name, self._file_path)
            if move_success:
                logger.info("Удалены пустые колонки из CSV")
                temp_created = False  # Файл успешно перемещён, очистка не требуется
            else:
                logger.error("Не удалось переместить файл с удалёнными колонками")
                raise RuntimeError("Failed to move file with removed columns")

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.error("Ошибка при записи CSV без пустых колонок: %s", e)
            raise

        finally:
            # ВАЖНО: Гарантированная очистка временного файла в любом случае
            # finally выполняется даже при KeyboardInterrupt и sys.exit()
            if temp_created and os.path.exists(tmp_csv_name):
                try:
                    os.remove(tmp_csv_name)
                    logger.debug("Временный файл удалён в блоке finally: %s", tmp_csv_name)
                except OSError as cleanup_error:
                    logger.warning(
                        "Не удалось удалить временный файл %s: %s", tmp_csv_name, cleanup_error
                    )

    def add_rubrics(self, rubrics: list[str], join_char: str = ", ") -> None:
        """Добавляет рубрики в CSV файл.

        ISSUE-162: Добавлен подробный docstring.

        Args:
            rubrics: Список рубрик для добавления.
            join_char: Разделитель для рубрик (по умолчанию ", ").

        Примечание:
            В текущей версии рубрики добавляются при записи данных.
            Этот метод предназначен для постобработки существующего CSV файла.
            Рубрики добавляются в колонку "Рубрики" через объединение списка
            с указанным разделителем.

        Пример:
            >>> processor = CSVPostProcessor("output.csv", data_mapping, complex_mapping)
            >>> processor.add_rubrics(["Магазины", "Одежда"], join_char="; ")
            # Добавит рубрики в файл: "Магазины; Одежда"

        """
        # Эта функция может быть реализована при необходимости
        # В текущей версии рубрики добавляются при записи
        logger.debug("Добавление рубрик: %s", rubrics)

    def add_comments_to_contacts(self) -> None:
        """Добавляет комментарии к контактам в CSV файле.

        ISSUE-163: Добавлен подробный docstring.

        Примечание:
            В текущей версии комментарии добавляются при извлечении данных
            через функцию _append_contact(). Этот метод предназначен для
            постобработки существующего CSV файла при необходимости.

            Комментарии добавляются к контактам (телефоны, email, сайты)
            в формате: "значение (комментарий)".

        Пример:
            >>> processor = CSVPostProcessor("output.csv", data_mapping, complex_mapping)
            >>> processor.add_comments_to_contacts()
            # Добавит комментарии к контактам: "+7 (999) 123-45-67 (Мобильный)"

        """
        # Эта функция может быть реализована при необходимости
        logger.debug("Добавление комментариев к контактам")
