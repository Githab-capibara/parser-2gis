"""Дедупликация записей CSV.

Предоставляет класс CSVDeduplicator для удаления дубликатов из CSV файлов:
- Хеширование строк с Unicode-нормализацией
- Оптимизированная пакетная обработка
- mmap поддержка для больших файлов

#72: Логика использования mmap аналогична csv_post_processor.py.
Рефакторинг отложен — оба файла используют общие утилиты из csv_buffer_manager.py.
"""

from __future__ import annotations

import hashlib
import os
import sys
import unicodedata

from parser_2gis.logger import logger

from .csv_buffer_manager import (
    HASH_BATCH_SIZE,
    _calculate_optimal_buffer_size,
    _safe_move_file,
    _should_use_mmap,
    mmap_file_context,
)


class CSVDeduplicator:
    """Класс для удаления дубликатов из CSV файлов."""

    def __init__(self, file_path: str, encoding: str = "utf-8") -> None:
        """Инициализация дедупликатора.

        Args:
            file_path: Путь к CSV файлу.
            encoding: Кодировка файла.

        """
        self._file_path = file_path
        self._encoding = encoding

    def _hash_row(self, row: str) -> str:
        """Вычисляет хеш строки с Unicode-нормализацией.

        ISSUE-158: Добавлен docstring с описанием алгоритма хеширования.

        Алгоритм хеширования:
            1. Нормализация строки: удаление завершающих пробелов и newlines (\\r, \\n)
            2. Unicode-нормализация NFKD (Normalization Form Compatibility Decomposition)
               - Разлагает символы на базовые символы + диакритические знаки
               - Обеспечивает корректное сравнение Unicode символов
            3. Кодирование в UTF-8
            4. Вычисление SHA256 хеша
            5. Возврат в hex формате (64 символа)

        Args:
            row: Строка для хеширования.

        Returns:
            SHA256 хеш строки в hex формате (64 символа).

        Raises:
            UnicodeEncodeError: При ошибке кодирования строки в UTF-8.
            TypeError: При некорректном типе входных данных.

        Примечание:
            - Unicode-нормализация NFKD для корректного сравнения
            - SHA256 для большей безопасности вместо MD5
            - Время выполнения: O(n) где n - длина строки

        """
        # Нормализуем строку: удаляем завершающие пробелы и newlines
        normalized_line = row.rstrip("\r\n")

        # Unicode-нормализация для корректного сравнения
        # NFKD разлагает символы на базовые символы + диакритические знаки
        normalized = unicodedata.normalize("NFKD", normalized_line)

        # Вычисляем хеш с использованием SHA256 для большей безопасности
        # Оптимизация: используем bytes напрямую для снижения конверсий
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def remove_duplicates(self) -> None:
        """Удаляет дубликаты из CSV файла.

        ISSUE-160: Добавлена проверка на блокировку файла.

        Оптимизация:
        - mmap для больших файлов (>10MB) вместо обычной буферизации
        - Увеличенная буферизация чтения/записи (256KB)
        - Предварительное выделение множества хешей
        - Использование bytes для хеширования вместо str
        - Пакетная запись строк для снижения накладных расходов
        - Проверка размера файла и выбор оптимального метода чтения

        Raises:
            OSError: При ошибке доступа к файлу.
            PermissionError: При отсутствии прав доступа к файлу.
            IOError: При ошибке ввода-вывода.

        Примечание:
            Использует хеширование строк с Unicode-нормализацией для надёжного сравнения.
            SHA256 используется вместо MD5 для большей безопасности.
            Включает улучшенную обработку ошибок и очистку временных файлов.

            Для файлов >10MB используется mmap для экономии памяти.
            Для файлов <=10MB используется обычная буферизация.
        """
        file_root, file_ext = os.path.splitext(self._file_path)
        tmp_csv_name = f"{file_root}.deduplicated{file_ext}"
        # #149: TODO — для больших файлов (>100K строк) использовать Bloom filter
        # вместо set[str] для снижения потребления памяти.
        # Bloom filter даст вероятностную проверку с фиксированным потреблением памяти
        # (например, 1MB для 1M строк с false-positive rate 1%).
        # Текущая реализация с set потребляет ~100 байт на хеш,
        # что для 1M строк = ~100MB памяти.
        seen_hashes: set[str] = set()
        duplicates_count = 0

        # ВАЖНО: Флаг для отслеживания создания временного файла
        temp_created = False

        # Проверка существования файла
        if not os.path.exists(self._file_path):
            logger.error("Файл CSV не найден: %s", self._file_path)
            return

        # ISSUE-160: Проверка на блокировку файла
        if not self._is_file_accessible(self._file_path):
            logger.error("Файл CSV заблокирован или недоступен: %s", self._file_path)
            raise OSError(f"Файл {self._file_path} заблокирован или недоступен")

        try:
            optimal_read_buffer = _calculate_optimal_buffer_size(file_path=self._file_path)
            file_size = os.path.getsize(self._file_path)
            optimal_write_buffer = _calculate_optimal_buffer_size(file_size_bytes=file_size)

            # Определяем метод чтения на основе размера файла
            try:
                use_mmap = _should_use_mmap(file_size) if file_size else False
                logger.info(
                    "Удаление дубликатов: размер файла %.2f MB, используется %s",
                    file_size / (1024 * 1024) if file_size else 0,
                    "mmap" if use_mmap else "обычная буферизация",
                )
            except OSError:
                use_mmap = False

            # Открываем файлы с mmap или обычной буферизацией
            # Используем контекстный менеджер для безопасной работы с mmap
            with mmap_file_context(self._file_path, "r", encoding="utf-8-sig") as (
                f_csv,
                is_mmap,
                _,  # underlying_fp не используется
            ):
                f_tmp_csv = open(
                    tmp_csv_name,
                    "w",
                    encoding=self._encoding,
                    newline="",
                    buffering=optimal_write_buffer,
                )

                try:
                    # ВАЖНО: Помечаем что временный файл создан
                    temp_created = True

                    # Оптимизация: читаем и записываем пакетно
                    batch: list[str] = []
                    batch_size = HASH_BATCH_SIZE

                    for line_num, line in enumerate(f_csv, 1):  # type: ignore[arg-type]
                        line_str: str = line  # type: ignore[assignment]
                        try:
                            # Вычисляем хеш строки
                            line_hash = self._hash_row(line_str)

                            if line_hash in seen_hashes:
                                duplicates_count += 1
                                continue

                            seen_hashes.add(line_hash)
                            batch.append(line_str)

                            # Пакетная запись для снижения накладных расходов
                            if len(batch) >= batch_size:
                                f_tmp_csv.writelines(batch)
                                batch.clear()

                        except (ValueError, TypeError, UnicodeError) as line_error:
                            logger.warning("Ошибка обработки строки %d: %s", line_num, line_error)
                            # Пропускаем проблемную строку и продолжаем

                    # Записываем оставшиеся строки
                    if batch:
                        f_tmp_csv.writelines(batch)

                    if duplicates_count > 0:
                        logger.info("Удалено дубликатов: %d", duplicates_count)
                    else:
                        logger.debug(
                            "Дубликаты не найдены (буфер чтения: %d, буфер записи: %d, mmap: %s)",
                            optimal_read_buffer,
                            optimal_write_buffer,
                            use_mmap,
                        )
                finally:
                    # Гарантированно закрываем файл записи
                    f_tmp_csv.close()

            # Замена оригинального файла новым с безопасной обработкой
            move_success = _safe_move_file(tmp_csv_name, self._file_path)
            if move_success:
                logger.info("Удалены дубликаты из CSV")
                temp_created = False  # Файл успешно перемещён, очистка не требуется
            else:
                logger.error("Не удалось переместить файл с удалёнными дубликатами")
                raise RuntimeError("Failed to move deduplicated file")

        except OSError as e:
            logger.error("Ошибка при удалении дубликатов: %s", e)
            raise

        except KeyboardInterrupt:
            logger.info("Операция удаления дубликатов прервана пользователем")
            raise

        except (TypeError, RuntimeError) as e:
            logger.error("Непредвиденная ошибка при удалении дубликатов: %s", e)
            raise

        finally:
            # ИСПРАВЛЕНИЕ C-003: Сохраняем информацию об оригинальном исключении
            # перед выполнением очистки чтобы перевыбросить его после
            # Это гарантирует что KeyboardInterrupt и другие критические исключения
            # не будут потеряны после очистки временного файла
            exc_info = sys.exc_info()

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

            # ИСПРАВЛЕНИЕ C-003: Перевыбрасываем оригинальное исключение после очистки
            # Проверяем exc_info[0] != None чтобы избежать перевыбрасывания None
            if exc_info[0] is not None:
                # Восстанавливаем оригинальное исключение
                raise exc_info[1].with_traceback(exc_info[2])

    def _is_file_accessible(self, file_path: str) -> bool:
        """Проверяет доступность файла для чтения и записи.

        ISSUE-160: Валидация на блокировку файла.

        Args:
            file_path: Путь к файлу для проверки.

        Returns:
            True если файл доступен для чтения и записи, False иначе.

        Примечание:
            - Проверяет существование файла
            - Проверяет права доступа (чтение/запись)
            - Пытается открыть файл в режиме чтения для проверки блокировки

        """
        try:
            # Проверяем существование
            if not os.path.exists(file_path):
                return False

            # Проверяем права доступа
            if not os.access(file_path, os.R_OK | os.W_OK):
                logger.warning("Файл %s недоступен для чтения/записи", file_path)
                return False

            # Пытаемся открыть файл для проверки на блокировку
            with open(file_path, "rb"):
                # Если файл открыт другим процессом с эксклюзивной блокировкой,
                # это вызовет ошибку. Тело with намеренно пустое — только проверка открытия.
                pass

            return True

        except PermissionError as perm_error:
            logger.error("Нет прав доступа к файлу %s: %s", file_path, perm_error)
            return False
        except OSError as os_error:
            logger.error("OSError при проверке файла %s: %s", file_path, os_error)
            return False
