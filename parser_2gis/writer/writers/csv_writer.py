from __future__ import annotations

import csv
import hashlib
import os
import re
import shutil
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import ValidationError

from ...common import CSV_BATCH_SIZE, DEFAULT_BUFFER_SIZE, report_from_validation_error
from ...logger import logger
from ..models import CatalogItem
from .file_writer import FileWriter

# =============================================================================
# КОНСТАНТЫ ДЛЯ ОПТИМИЗАЦИИ (ОБОСНОВАНИЕ ЗНАЧЕНИЙ)
# =============================================================================

# ОБОСНОВАНИЕ: 256 KB выбрано как баланс между:
# - Частые системные вызовы (маленький буфер)
# - Избыточное использование памяти (большой буфер)
# - Стандартный размер страницы памяти: 4KB
# - 256KB = 64 страницы - оптимально для последовательного чтения/записи
# Буфер для чтения файлов в байтах (256 KB)
READ_BUFFER_SIZE = DEFAULT_BUFFER_SIZE

# ОБОСНОВАНИЕ: 256 KB для записи обеспечивает:
# - Уменьшение количества системных вызовов write()
# - Эффективное использование кэша диска
# - Баланс между памятью и производительностью
# Буфер для записи файлов в байтах (256 KB)
WRITE_BUFFER_SIZE = DEFAULT_BUFFER_SIZE

# Размер пакета для хеширования строк
# ОБОСНОВАНИЕ: 1000 строк выбрано исходя из:
# - Средняя длина строки: 200-500 байт
# - 1000 * 300 байт = 300KB - разумное использование памяти
# - Пакетная обработка улучшает производительность хеширования
HASH_BATCH_SIZE = 1000

# Размер пакета для чтения/записи CSV (Оптимизация 17)

CSV_BATCH_SIZE_LOCAL = CSV_BATCH_SIZE

# =============================================================================
# =============================================================================

# Порог размера файла для использования увеличенного буфера (100 MB)
LARGE_FILE_THRESHOLD_MB = 100

# Множитель увеличения буфера для больших файлов
LARGE_FILE_BUFFER_MULTIPLIER = 4

# Максимальный размер буфера (1 MB)
MAX_BUFFER_SIZE = 1048576


def _calculate_optimal_buffer_size(file_path: Optional[str] = None, file_size_bytes: Optional[int] = None) -> int:
    """
    Рассчитывает оптимальный размер буфера для чтения/записи CSV файлов.

        - Для файлов >100MB используется увеличенный буфер (1MB)
    - Для файлов <=100MB используется стандартный буфер (256KB)
    - Автоматическое определение размера файла если не предоставлен
    - Настройка через конфигурацию (переменные окружения)

    Args:
        file_path: Путь к файлу для определения размера (опционально).
        file_size_bytes: Размер файла в байтах (опционально).

    Returns:
        Оптимальный размер буфера в байтах.

    Пример:
        >>> _calculate_optimal_buffer_size(file_size_bytes=150_000_000)
        1048576  # 1MB для файлов >100MB
        >>> _calculate_optimal_buffer_size(file_size_bytes=50_000_000)
        262144  # 256KB для файлов <=100MB
    """
    # Проверяем переменную окружения для переопределения размера буфера
    env_buffer_size = os.getenv("PARSER_CSV_BUFFER_SIZE")
    if env_buffer_size is not None:
        try:
            custom_buffer = int(env_buffer_size)
            if custom_buffer > 0:
                logger.debug("Используется пользовательский размер буфера: %d байт", custom_buffer)
                return custom_buffer
        except ValueError:
            logger.warning("Некорректное значение PARSER_CSV_BUFFER_SIZE: %s", env_buffer_size)

    # Определяем размер файла если не предоставлен
    if file_size_bytes is None and file_path is not None:
        try:
            file_size_bytes = os.path.getsize(file_path)
        except OSError:
            # Если не удалось получить размер, используем дефолтное значение
            file_size_bytes = 0

    # Если размер файла неизвестен, используем дефолтное значение
    if file_size_bytes is None:
        return DEFAULT_BUFFER_SIZE

    # Рассчитываем оптимальный размер буфера
    threshold_bytes = LARGE_FILE_THRESHOLD_MB * 1024 * 1024  # 100 MB

    if file_size_bytes > threshold_bytes:
        # Для больших файлов используем увеличенный буфер
        optimal_size = min(
            DEFAULT_BUFFER_SIZE * LARGE_FILE_BUFFER_MULTIPLIER,
            MAX_BUFFER_SIZE
        )
        logger.debug(
            "Файл большой (%.2f MB), используется увеличенный буфер: %d байт",
            file_size_bytes / (1024 * 1024),
            optimal_size
        )
        return optimal_size
    else:
        # Для обычных файлов используем стандартный буфер
        logger.debug(
            "Файл стандартного размера (%.2f MB), используется стандартный буфер: %d байт",
            file_size_bytes / (1024 * 1024),
            DEFAULT_BUFFER_SIZE
        )
        return DEFAULT_BUFFER_SIZE


def _safe_move_file(src: str, dst: str) -> bool:
    """
    Безопасное перемещение файла с fallback на copy+delete.
    - Обрабатывает ошибку shutil.move() с fallback на copy+delete
    - Проверяет существование файла после move
    - Удаляет source файл если move успешен но source остался

    Args:
        src: Путь к исходному файлу
        dst: Путь к целевому файлу

    Returns:
        True если перемещение успешно, False иначе
    """
    try:
        # Пытаемся атомарное перемещение
        shutil.move(src, dst)

        # Проверяем что целевой файл существует
        if not os.path.exists(dst):
            logger.error("Файл не был перемещён: %s -> %s", src, dst)
            return False

        # Если source файл всё ещё существует - удаляем его
        # Это может произойти если shutil.move использовал copy+unlink вместо rename
        if os.path.exists(src):
            try:
                os.remove(src)
                logger.debug("Source файл удалён после move: %s", src)
            except OSError as remove_error:
                logger.warning(
                    "Не удалось удалить source файл %s после move: %s",
                    src,
                    remove_error,
                )

        return True

    except Exception as move_error:
        # Fallback на copy+delete
        logger.warning(
            "shutil.move не удался (%s: %s), используем fallback copy+delete",
            type(move_error).__name__,
            move_error,
        )
        try:
            # Копируем файл с сохранением метаданных
            shutil.copy2(src, dst)

            # Проверяем что копия успешна
            if os.path.exists(dst):
                # Удаляем оригинал
                os.remove(src)
                logger.info(
                    "Файл перемещён через fallback copy+delete: %s -> %s", src, dst
                )
                return True
            else:
                logger.error("Fallback copy+delete не удался: файл %s не создан", dst)
                return False

        except Exception as fallback_error:
            logger.error(
                "Fallback copy+delete не удался: %s (%s)",
                fallback_error,
                type(fallback_error).__name__,
            )
            return False


class CSVWriter(FileWriter):
    """Писатель в CSV-таблицу.

    Предназначен для записи данных парсинга в файлы формата CSV.
    Поддерживает постобработку: удаление пустых колонок и дубликатов.
    """

    @property
    def _type_names(self) -> dict[str, str]:
        """Возвращает отображение типов на русские названия.

        Returns:
            Словарь с маппингом типов: 'parking' -> 'Парковка' и т.д.
        """
        return {
            "parking": "Парковка",
            "street": "Улица",
            "road": "Дорога",
            "crossroad": "Перекрёсток",
            "station": "Остановка",
        }

    @property
    def _complex_mapping(self) -> dict[str, Any]:
        """Возвращает отображение сложных полей с несколькими значениями.

        Сложное отображение означает, что его содержимое может содержать несколько сущностей,
        связанных пользовательскими настройками.
        Например: phone -> phone_1, phone_2, ..., phone_n

        Returns:
            Словарь с маппингом полей: 'phone' -> 'Телефон' и т.д.
        """
        # Сложное отображение означает, что его содержимое может содержать несколько сущностей,
        # связанных пользовательскими настройками.
        # Например: phone -> phone_1, phone_2, ..., phone_n
        return {
            "phone": "Телефон",
            "email": "E-mail",
            "website": "Веб-сайт",
            "instagram": "Instagram",
            "twitter": "Twitter",
            "facebook": "Facebook",
            "vkontakte": "ВКонтакте",
            "whatsapp": "WhatsApp",
            "viber": "Viber",
            "telegram": "Telegram",
            "youtube": "YouTube",
            "skype": "Skype",
        }

    @property
    def _data_mapping(self) -> dict[str, Any]:
        """Возвращает полное отображение данных для CSV колонок.

        Формирует маппинг между полями данных и названиями колонок в CSV.
        Включает сложные поля (телефоны, email и т.д.) с учётом настройки
        columns_per_entity.

        Returns:
            Словарь с маппингом всех полей для CSV выгрузки.
        """
        data_mapping = {
            "name": "Наименование",
            "description": "Описание",
            "rubrics": "Рубрики",
            "address": "Адрес",
            "address_comment": "Комментарий к адресу",
            "postcode": "Почтовый индекс",
            "living_area": "Микрорайон",
            "district": "Район",
            "city": "Город",
            "district_area": "Округ",
            "region": "Регион",
            "country": "Страна",
            "schedule": "Часы работы",
            "timezone": "Часовой пояс",
            "general_rating": "Рейтинг",
            "general_review_count": "Количество отзывов",
        }

        # Расширяем сложное отображение
        for k, v in self._complex_mapping.items():
            for n in range(1, self._options.csv.columns_per_entity + 1):
                data_mapping[f"{k}_{n}"] = f"{v} {n}"

        if not self._options.csv.add_rubrics:
            data_mapping.pop("rubrics", None)

        return {
            **data_mapping,
            **{
                "point_lat": "Широта",
                "point_lon": "Долгота",
                "url": "2GIS URL",
                "type": "Тип",
            },
        }

    def _writerow(self, row: Dict[str, Any]) -> None:
        """Записывает `row` в CSV.

        Args:
            row: Словарь с данными для записи.
        """
        if self._options.verbose:
            logger.info(
                "Парсинг [%d] > %s", self._wrote_count + 1, row.get("name", "N/A")
            )

        try:
            self._writer.writerow(row)
        except Exception as e:
            logger.error("Ошибка во время записи строки: %s", e)

    def __enter__(self) -> CSVWriter:
        super().__enter__()
        self._writer = csv.DictWriter(self._file, self._data_mapping.keys())
        self._writer.writerow(self._data_mapping)  # Запись заголовка
        self._wrote_count = 0
        return self

    def __exit__(self, *exc_info: Any) -> None:
        super().__exit__(*exc_info)

        # Постобработка: удаление пустых колонок
        if self._options.csv.remove_empty_columns:
            try:
                logger.info("Удаление пустых колонок CSV.")
                self._remove_empty_columns()
            except Exception as e:
                logger.error("Ошибка при удалении пустых колонок: %s", e)

        # Постобработка: удаление дубликатов
        if self._options.csv.remove_duplicates:
            try:
                logger.info("Удаление повторяющихся записей CSV.")
                self._remove_duplicates()
            except Exception as e:
                logger.error("Ошибка при удалении дубликатов: %s", e)

    def _remove_empty_columns(self) -> None:
        """Постобработка: Удаление пустых колонок.

        Оптимизация:
        - Увеличенная буферизация чтения/записи (128KB)
        - Пакетная запись строк для снижения накладных расходов
        - Предварительное вычисление regex паттерна

        Примечание:
            Функция анализирует все строки CSV и удаляет колонки,
            которые не содержат данных (за исключением сложных колонок,
            таких как phone_1, phone_2 и т.д.).
        """
        complex_columns = list(self._complex_mapping.keys())

        # Словарь для подсчёта непустых значений в сложных колонках
        complex_columns_count: Dict[str, int] = {}

        # Оптимизация: компилируем regex паттерн один раз
        complex_columns_pattern = None
        if complex_columns:
            # Группируем паттерны для корректной работы regex
            pattern_str = (
                r"^(?:" + "|".join(rf"{x}_\d+" for x in complex_columns) + r")$"
            )
            complex_columns_pattern = re.compile(pattern_str)
            for c in self._data_mapping.keys():
                if complex_columns_pattern.match(c):
                    complex_columns_count[c] = 0

        try:
            optimal_buffer = _calculate_optimal_buffer_size(file_path=self._file_path)

            # Первый проход: подсчёт непустых значений в сложных колонках

            with self._open_file(
                self._file_path, "r", encoding="utf-8-sig", buffering=optimal_buffer
            ) as f_csv:
                csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore

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
                "Подсчёт заполненности колонок завершён (обработано пакетов: %d, буфер: %d байт)",
                batch_count,
                optimal_buffer,
            )

        except Exception as e:
            logger.error("Ошибка при чтении CSV для анализа колонок: %s", e)
            raise

        # Генерация нового маппинга данных
        new_data_mapping: Dict[str, Any] = {}
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
                new_data_mapping[col_1] = re.sub(
                    r"\s+\d+$", "", new_data_mapping[col_1]
                )

        # Создание временного файла
        file_root, file_ext = os.path.splitext(self._file_path)
        tmp_csv_name = f"{file_root}.removed-columns{file_ext}"

        # ВАЖНО: Флаг для отслеживания создания временного файла
        temp_created = False

        try:
            optimal_read_buffer = _calculate_optimal_buffer_size(
                file_path=self._file_path
            )
            file_size = (
                os.path.getsize(self._file_path)
                if os.path.exists(self._file_path)
                else None
            )
            optimal_write_buffer = _calculate_optimal_buffer_size(
                file_size_bytes=file_size
            )

            # Чтение исходного файла и запись нового с увеличенной буферизацией
            with (
                self._open_file(
                    self._file_path, "r", buffering=optimal_read_buffer
                ) as f_csv,
                self._open_file(
                    tmp_csv_name, "w", newline="", buffering=optimal_write_buffer
                ) as f_tmp_csv,
            ):
                # ВАЖНО: Помечаем что временный файл создан
                temp_created = True

                csv_writer = csv.DictWriter(f_tmp_csv, new_data_mapping.keys())  # type: ignore
                csv_reader = csv.DictReader(f_csv, self._data_mapping.keys())  # type: ignore

                # Запись нового заголовка
                csv_writer.writerow(new_data_mapping)

                batch = []
                batch_size = (
                    CSV_BATCH_SIZE  # Используем увеличенный размер пакета (1000 строк)
                )
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
                    "Запись CSV завершена (всего пакетов: %d, размер пакета: %d, буфер чтения: %d, буфер записи: %d)",
                    total_batches,
                    batch_size,
                    optimal_read_buffer,
                    optimal_write_buffer,
                )

            # Замена оригинального файла новым с безопасной обработкой
            move_success = _safe_move_file(tmp_csv_name, self._file_path)
            if move_success:
                logger.info("Удалены пустые колонки из CSV")
                temp_created = False  # Файл успешно перемещён, очистка не требуется
            else:
                logger.error("Не удалось переместить файл с удалёнными колонками")
                raise RuntimeError("Failed to move file with removed columns")

        except Exception as e:
            logger.error("Ошибка при записи CSV без пустых колонок: %s", e)
            raise

        finally:
            # ВАЖНО: Гарантированная очистка временного файла в любом случае
            # finally выполняется даже при KeyboardInterrupt и sys.exit()
            if temp_created and os.path.exists(tmp_csv_name):
                try:
                    os.remove(tmp_csv_name)
                    logger.debug(
                        "Временный файл удалён в блоке finally: %s", tmp_csv_name
                    )
                except OSError as cleanup_error:
                    logger.warning(
                        "Не удалось удалить временный файл %s: %s",
                        tmp_csv_name,
                        cleanup_error,
                    )

    def _remove_duplicates(self) -> None:
        """Постобработка: Удаление дубликатов.

        Оптимизация:
        - Увеличенная буферизация чтения/записи (128KB)
        - Предварительное выделение множества хешей
        - Использование bytes для хеширования вместо str
        - Пакетная запись строк для снижения накладных расходов

        Примечание:
            Использует хеширование строк с Unicode-нормализацией для надёжного сравнения.
            SHA256 используется вместо MD5 для большей безопасности.
            Включает улучшенную обработку ошибок и очистку временных файлов.
        """
        file_root, file_ext = os.path.splitext(self._file_path)
        tmp_csv_name = f"{file_root}.deduplicated{file_ext}"
        seen_hashes: Set[str] = set()
        duplicates_count = 0

        # ВАЖНО: Флаг для отслеживания создания временного файла
        temp_created = False

        # Проверка существования файла
        if not os.path.exists(self._file_path):
            logger.error("Файл CSV не найден: %s", self._file_path)
            return

        try:
            optimal_read_buffer = _calculate_optimal_buffer_size(file_path=self._file_path)
            file_size = os.path.getsize(self._file_path) if os.path.exists(self._file_path) else None
            optimal_write_buffer = _calculate_optimal_buffer_size(file_size_bytes=file_size)

            # Чтение исходного файла и запись нового без дубликатов
            # Используем увеличенную буферизацию для улучшения производительности
            with (
                self._open_file(
                    self._file_path,
                    "r",
                    encoding="utf-8-sig",
                    buffering=optimal_read_buffer,
                ) as f_csv,
                self._open_file(
                    tmp_csv_name,
                    "w",
                    encoding=self._options.encoding,
                    newline="",
                    buffering=optimal_write_buffer,
                ) as f_tmp_csv,
            ):
                # ВАЖНО: Помечаем что временный файл создан
                temp_created = True

                # Оптимизация: читаем и записываем пакетно
                batch = []
                batch_size = HASH_BATCH_SIZE

                for line_num, line in enumerate(f_csv, 1):
                    try:
                        # Нормализуем строку: удаляем завершающие пробелы и newlines
                        normalized_line = line.rstrip("\r\n")

                        # Unicode-нормализация для корректного сравнения
                        # NFKD разлагает символы на базовые символы + диакритические знаки
                        normalized = unicodedata.normalize("NFKD", normalized_line)

                        # Вычисляем хеш с использованием SHA256 для большей безопасности
                        # Оптимизация: используем bytes напрямую для снижения конверсий
                        line_hash = hashlib.sha256(
                            normalized.encode("utf-8")
                        ).hexdigest()

                        if line_hash in seen_hashes:
                            duplicates_count += 1
                            continue

                        seen_hashes.add(line_hash)
                        batch.append(line)

                        # Пакетная запись для снижения накладных расходов
                        if len(batch) >= batch_size:
                            f_tmp_csv.writelines(batch)
                            batch.clear()

                    except Exception as line_error:
                        logger.warning(
                            "Ошибка обработки строки %d: %s",
                            line_num,
                            line_error
                        )
                        # Пропускаем проблемную строку и продолжаем

                # Записываем оставшиеся строки
                if batch:
                    f_tmp_csv.writelines(batch)

            if duplicates_count > 0:
                logger.info("Удалено дубликатов: %d", duplicates_count)
            else:
                logger.debug(
                    "Дубликаты не найдены (буфер чтения: %d, буфер записи: %d)",
                    optimal_read_buffer,
                    optimal_write_buffer
                )

            # Замена оригинального файла новым с безопасной обработкой
            move_success = _safe_move_file(tmp_csv_name, self._file_path)
            if move_success:
                temp_created = False  # Файл успешно перемещён, очистка не требуется
            else:
                logger.error("Не удалось переместить файл с удалёнными дубликатами")
                raise RuntimeError("Failed to move deduplicated file")

        except (OSError, IOError) as e:
            logger.error("Ошибка при удалении дубликатов: %s", e)
            raise

        except KeyboardInterrupt:
            logger.info("Операция удаления дубликатов прервана пользователем")
            raise

        except Exception as e:
            logger.error("Непредвиденная ошибка при удалении дубликатов: %s", e)
            raise

        finally:
            # ВАЖНО: Гарантированная очистка временного файла в любом случае
            # finally выполняется даже при KeyboardInterrupt и sys.exit()
            if temp_created and os.path.exists(tmp_csv_name):
                try:
                    os.remove(tmp_csv_name)
                    logger.debug(
                        "Временный файл удалён в блоке finally: %s", tmp_csv_name
                    )
                except OSError as cleanup_error:
                    logger.warning(
                        "Не удалось удалить временный файл %s: %s",
                        tmp_csv_name,
                        cleanup_error,
                    )

    def write(self, catalog_doc: Any) -> None:
        """Записывает JSON-документ Catalog Item API в CSV-таблицу.

        Args:
            catalog_doc: JSON-документ Catalog Item API.
        """
        if not self._check_catalog_doc(catalog_doc):
            return

        row = self._extract_raw(catalog_doc)
        if row:
            self._writerow(row)
            self._wrote_count += 1

    def _extract_raw(self, catalog_doc: Any) -> Dict[str, Any]:
        """Извлекает данные из JSON-документа Catalog Item API.

        Args:
            catalog_doc: JSON-документ Catalog Item API.

        Returns:
            Словарь для строки CSV или пустой словарь при ошибке.
        """
        data: Dict[str, Any] = {k: None for k in self._data_mapping.keys()}

        # Проверка структуры документа
        try:
            result = catalog_doc.get("result")
            if not result or "items" not in result:
                logger.error(
                    "Некорректная структура документа: отсутствует result.items"
                )
                return {}

            items = result.get("items", [])
            if not items:
                logger.error("Пустой список items в документе")
                return {}

            item = items[0]
        except (KeyError, TypeError, IndexError) as e:
            logger.error("Ошибка при извлечении элемента из документа: %s", e)
            return {}

        try:
            catalog_item = CatalogItem(**item)
        except ValidationError as e:
            errors = []
            errors_report = report_from_validation_error(e, item)
            for path, description in errors_report.items():
                arg = description["invalid_value"]
                error_msg = description["error_message"]
                errors.append(f"[*] Поле: {path}, значение: {arg}, ошибка: {error_msg}")

            # Безопасность: не раскрываем полную структуру документа API
            item_type = item.get("type", "неизвестно")
            item_id = item.get("id", "неизвестно")
            error_str = "Ошибка парсинга:\n" + "\n".join(errors)
            error_str += f"\nДокумент каталога (тип: {item_type}, ID: {item_id})"
            logger.error(error_str)

            # Возвращаем пустой словарь для индикации ошибки
            return {}

        # Наименование и описание объекта
        if catalog_item.name_ex:
            data["name"] = catalog_item.name_ex.primary
            data["description"] = catalog_item.name_ex.extension
        elif catalog_item.name:
            data["name"] = catalog_item.name
        elif catalog_item.type in self._type_names:
            data["name"] = self._type_names[catalog_item.type]

        # Тип объекта
        data["type"] = catalog_item.type

        # Адрес объекта
        data["address"] = catalog_item.address_name

        # Рейтинг и отзывы
        if catalog_item.reviews:
            data["general_rating"] = catalog_item.reviews.general_rating
            data["general_review_count"] = catalog_item.reviews.general_review_count

        # Географические координаты объекта
        if catalog_item.point:
            data["point_lat"] = catalog_item.point.lat  # Широта объекта
            data["point_lon"] = catalog_item.point.lon  # Долгота объекта

        # Дополнительный комментарий к адресу
        data["address_comment"] = catalog_item.address_comment

        # Почтовый индекс
        if catalog_item.address:
            data["postcode"] = catalog_item.address.postcode

        # Часовой пояс объекта
        if catalog_item.timezone is not None:
            data["timezone"] = catalog_item.timezone

        # Административно-территориальные детали (страна, регион, округ и т.д.)
        for div in catalog_item.adm_div:
            for t in (
                "country",
                "region",
                "district_area",
                "city",
                "district",
                "living_area",
            ):
                if div.type == t:
                    data[t] = div.name

        # URL объекта на сайте 2GIS
        data["url"] = catalog_item.url

        # Контактные данные (телефоны, email, сайты, соцсети)
        for contact_group in catalog_item.contact_groups:

            def append_contact(
                contact_type: str,
                priority_fields: List[str],
                formatter: Optional[Callable[[str], str]] = None,
            ) -> None:
                """Добавляет контакт в `data`.

                Args:
                    contact_type: Тип контакта (см. `Contact` в `catalog_item.py`)
                    priority_fields: Поля контакта для добавления, сортированные по приоритету
                    formatter: Форматировщик значения поля
                """
                contacts = [x for x in contact_group.contacts if x.type == contact_type]
                for i, contact in enumerate(contacts, 1):
                    contact_value = None

                    for field in priority_fields:
                        if hasattr(contact, field):
                            contact_value = getattr(contact, field)
                            break

                    # Отсутствующие значения контакта - пропускаем
                    if not contact_value:
                        return

                    data_name = f"{contact_type}_{i}"
                    if data_name in data:
                        data[data_name] = (
                            formatter(contact_value) if formatter else contact_value
                        )

                        # Добавляем комментарий к контакту при наличии
                        if self._options.csv.add_comments and contact.comment:
                            data[data_name] += " (%s)" % contact.comment

            # Интернет-адреса (веб-сайты, соцсети)
            for t in [
                "website",
                "vkontakte",
                "whatsapp",
                "viber",
                "telegram",
                "instagram",
                "facebook",
                "twitter",
                "youtube",
                "skype",
            ]:
                append_contact(t, ["url"])

            # Удаляем параметры из URL WhatsApp
            for field in data:
                if field.startswith("whatsapp") and data[field]:
                    data[field] = data[field].split("?")[0]

            # Текстовые значения (email, skype и т.д.)
            for t in ["email", "skype"]:
                append_contact(t, ["value"])

            # Телефоны (поле `value` иногда содержит нерелевантные данные,
            # поэтому предпочитаем парсить поле `text`.
            # Если в контакте нет `text` - используем атрибут `value`)
            append_contact(
                "phone",
                ["text", "value"],
                formatter=lambda x: re.sub(r"^\+7", "8", re.sub(r"[^0-9+]", "", x)),
            )

        # Режим работы объекта
        if catalog_item.schedule:
            data["schedule"] = catalog_item.schedule.to_str(
                self._options.csv.join_char, self._options.csv.add_comments
            )

        # Рубрики (категории) объекта
        if self._options.csv.add_rubrics:
            data["rubrics"] = self._options.csv.join_char.join(
                x.name for x in catalog_item.rubrics
            )

        return data
