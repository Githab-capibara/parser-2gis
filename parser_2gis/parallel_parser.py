"""
Модуль для параллельного парсинга городов.

Этот модуль предоставляет возможность одновременного парсинга нескольких URL
с использованием нескольких экземпляров браузера Chrome.

Оптимизации:
- Буферизация при работе с CSV файлами
- Улучшенная обработка прогресса
- Оптимизация памяти при слиянии файлов
"""

from __future__ import annotations

import shutil
import threading
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional, Dict, List

from .common import generate_category_url
from .logger import logger, log_parser_finish, print_progress
from .parser import get_parser
from .writer import get_writer

# Константы для валидации параметров
MIN_WORKERS = 1
MAX_WORKERS = 20
MIN_TIMEOUT = 60  # секунд
MAX_TIMEOUT = 3600  # секунд
DEFAULT_TIMEOUT = 300  # секунд

# Константы для прогресса
PROGRESS_UPDATE_INTERVAL = 3  # секунд

if TYPE_CHECKING:
    from .config import Configuration


class ParallelCityParser:
    """
    Параллельный парсер для парсинга городов по категориям.

    Запускает несколько браузеров одновременно для парсинга разных URL.
    Результаты сохраняются в отдельную папку output/, затем объединяются.

    Args:
        cities: Список городов для парсинга.
        categories: Список категорий для парсинга.
        output_dir: Папка для сохранения результатов.
        config: Конфигурация.
        max_workers: Максимальное количество одновременных браузеров.
        timeout_per_url: Таймаут на один URL в секундах (по умолчанию 300).
    """

    def __init__(
        self,
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
    ) -> None:
        # Валидация входных данных: проверка списка городов
        if not cities:
            raise ValueError("Список городов не может быть пустым")

        # Валидация входных данных: проверка списка категорий
        if not categories:
            raise ValueError("Список категорий не может быть пустым")

        # Валидация входных данных: ограничение max_workers (1-20)
        if not MIN_WORKERS <= max_workers <= MAX_WORKERS:
            raise ValueError(f"max_workers должен быть от {MIN_WORKERS} до {MAX_WORKERS}")

        # Валидация timeout_per_url (60-3600 секунд)
        if not MIN_TIMEOUT <= timeout_per_url <= MAX_TIMEOUT:
            raise ValueError(f"timeout_per_url должен быть от {MIN_TIMEOUT} до {MAX_TIMEOUT} секунд")

        self.cities = cities
        self.categories = categories
        self.output_dir = Path(output_dir)
        self.config = config
        self.max_workers = max_workers
        self.timeout_per_url = timeout_per_url

        # Проверка существования output_dir и прав на запись
        if self.output_dir.exists():
            if not self.output_dir.is_dir():
                raise ValueError(
                    f"output_dir существует, но не является директорией: {output_dir}"
                )
            # EAFP подход: проверяем права попыткой записи тестового файла
            # Это защищает от race condition между проверкой и фактической записью
            test_file: Optional[Path] = None
            try:
                test_file = self.output_dir / ".write_test"
                test_file.touch()
            except (OSError, PermissionError) as e:
                raise ValueError(f"Нет прав на запись в директорию: {output_dir}. Ошибка: {e}")
            finally:
                # Гарантируем удаление тестового файла
                if test_file is not None and test_file.exists():
                    try:
                        test_file.unlink()
                    except Exception as cleanup_error:
                        logger.warning(
                            "Не удалось удалить тестовый файл %s: %s",
                            test_file,
                            cleanup_error
                        )
        else:
            # Попытка создать директорию
            test_file = None
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                # EAFP проверка прав после создания
                test_file = self.output_dir / ".write_test"
                test_file.touch()
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Не удалось создать директорию output_dir: {output_dir}. Ошибка: {e}"
                )
            finally:
                # Гарантируем удаление тестового файла
                if test_file is not None and test_file.exists():
                    try:
                        test_file.unlink()
                    except Exception as cleanup_error:
                        logger.warning(
                            "Не удалось удалить тестовый файл %s: %s",
                            test_file,
                            cleanup_error
                        )

        # Статистика (все операции защищены _lock)
        self._stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }
        # Блокировка для потокобезопасного доступа к _stats и логгирования
        self._lock = threading.Lock()

        # Флаг отмены
        self._cancel_event = threading.Event()

        # Логирование успешной инициализации
        self.log(
            f"Инициализирован парсер: {len(cities)} городов, {len(categories)} категорий, max_workers={max_workers}",
            "info",
        )

    def log(self, message: str, level: str = "info") -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def generate_all_urls(self) -> list[tuple[str, str, str]]:
        """
        Генерирует все URL для парсинга.

        Returns:
            Список кортежей (url, category_name, city_name).
        """
        all_urls = []

        for city in self.cities:
            for category in self.categories:
                try:
                    # Используем общую функцию генерации URL
                    url = generate_category_url(city, category)
                    all_urls.append((url, category["name"], city["name"]))
                except Exception as e:
                    self.log(
                        f"Ошибка генерации URL для {city['name']} - {category['name']}: {e}",
                        "error",
                    )
                    continue

        with self._lock:
            self._stats["total"] = len(all_urls)

        self.log(f"Сгенерировано {len(all_urls)} URL для парсинга", "info")

        return all_urls

    def parse_single_url(
        self,
        url: str,
        category_name: str,
        city_name: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> tuple[bool, str]:
        """
        Парсит один URL и сохраняет результат в отдельный файл.

        Использует временный файл для защиты от race condition:
        - Запись происходит во временный файл с уникальным именем
        - После успешного завершения файл переименовывается в целевое имя
        - При ошибке временный файл удаляется

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            Кортеж (успех, сообщение).
        """
        # Проверяем флаг отмены
        if self._cancel_event.is_set():
            return False, "Отменено пользователем"

        # Формируем целевое имя файла
        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_city}_{safe_category}.csv"
        filepath = self.output_dir / filename

        # Создаём уникальное временное имя файла
        # uuid.uuid4() гарантирует уникальность, поэтому проверка на коллизии не требуется
        temp_filename = f"{safe_city}_{safe_category}_{uuid.uuid4().hex}.tmp"
        temp_filepath = self.output_dir / temp_filename

        try:
            self.log(
                f"Начало парсинга: {city_name} - {category_name} (временный файл: {temp_filename})",
                "info",
            )

            # Создаем парсер
            with get_parser(
                url,
                chrome_options=self.config.chrome,
                parser_options=self.config.parser,
            ) as parser:
                # Создаем writer для этого URL (запись во временный файл)
                with get_writer(
                    str(temp_filepath), "csv", self.config.writer
                ) as writer:
                    # Парсим с гарантированной очисткой ресурсов
                    try:
                        parser.parse(writer)
                    finally:
                        # Гарантируем очистку даже при исключении
                        # контекстные менеджеры вызовут __exit__, но явно указываем на важность
                        pass

            # После успешного парсинга переименовываем временный файл в целевой
            # Это атомарная операция на большинстве файловых систем
            # Используем shutil.move как fallback для cross-device перемещения
            move_success = False
            try:
                temp_filepath.replace(filepath)
                move_success = True
            except OSError as replace_error:
                # Fallback для перемещения между разными файловыми системами
                try:
                    shutil.move(str(temp_filepath), str(filepath))
                    move_success = True
                except Exception as move_error:
                    # Очистка временного файла при ошибке перемещения
                    self.log(
                        f"Не удалось переместить временный файл {temp_filename}: {move_error}",
                        "error",
                    )
                    try:
                        if temp_filepath.exists():
                            temp_filepath.unlink()
                            self.log(
                                f"Временный файл удалён после ошибки перемещения: {temp_filename}",
                                "debug",
                            )
                    except Exception as cleanup_error:
                        self.log(
                            f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                            "warning",
                        )
                    raise move_error
            
            if move_success:
                self.log(
                    f"Временный файл переименован: {temp_filename} → {filename}", "debug"
                )

            self.log(
                f"Завершён парсинг: {city_name} - {category_name} → {filepath}", "info"
            )

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats["success"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, filepath.name)

            return True, str(filepath)

        except Exception as e:
            self.log(f"Ошибка парсинга {city_name} - {category_name}: {e}", "error")

            # Удаляем временный файл при ошибке
            try:
                if temp_filepath.exists():
                    temp_filepath.unlink()
                    self.log(
                        f"Временный файл удалён после ошибки: {temp_filename}", "debug"
                    )
            except Exception as cleanup_error:
                self.log(
                    f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                    "warning",
                )

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats["failed"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, "N/A")

            return False, str(e)

    def merge_csv_files(
        self,
        output_file: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Объединяет все CSV файлы в один с добавлением колонки "Категория".
        
        Оптимизация:
        - Буферизация чтения/записи для снижения накладных расходов
        - Предварительное вычисление категории для снижения операций в цикле
        - Пакетная запись строк для улучшения производительности

        Важно: Сначала объединяются ВСЕ файлы, и ТОЛЬКО ПОСЛЕ успешного
        объединения удаляются все исходные файлы. Это предотвращает потерю
        данных при ошибке в середине процесса.

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            True если успешно.
        """
        import csv

        self.log("Начало объединения CSV файлов...", "info")

        # Находим все CSV файлы в output_dir
        csv_files = list(self.output_dir.glob("*.csv"))

        # Исключаем объединенный файл если он уже существует (повторный запуск)
        output_file_path = Path(output_file)
        if output_file_path.exists():
            csv_files = [f for f in csv_files if f != output_file_path]
            self.log(
                f"Исключен объединенный файл из списка: {output_file_path.name}",
                "debug",
            )

        if not csv_files:
            self.log("Не найдено CSV файлов для объединения", "warning")
            return False

        self.log(f"Найдено {len(csv_files)} CSV файлов для объединения", "info")

        # Сортируем файлы по имени
        csv_files.sort(key=lambda x: x.name)

        # Список файлов для удаления (заполняется после успешного объединения)
        files_to_delete: list[Path] = []

        # Создаём временный файл для результата объединения
        temp_output = self.output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"

        # Оптимизация: используем буферизацию для улучшения производительности
        output_encoding = self.config.writer.encoding
        
        try:
            # Открываем с буферизацией для улучшения производительности
            with open(temp_output, "w", encoding=output_encoding, newline="", buffering=32768) as outfile:
                writer = None
                total_rows = 0
                fieldnames_cache: Dict[str, List[str]] = {}  # Кэш полей для файлов

                for csv_file in csv_files:
                    if self._cancel_event.is_set():
                        self.log("Объединение отменено пользователем", "warning")
                        try:
                            temp_output.unlink()
                        except Exception as e:
                            self.log(f"Не удалось удалить временный файл при отмене: {e}", "debug")
                        return False

                    if progress_callback:
                        progress_callback(f"Обработка: {csv_file.name}")

                    # Оптимизация: быстрое извлечение категории из имени файла
                    # Используем rfind для поиска последнего подчёркивания
                    stem = csv_file.stem
                    last_underscore_idx = stem.rfind("_")
                    
                    if last_underscore_idx > 0:
                        category_name = stem[last_underscore_idx + 1:].replace("_", " ")
                    else:
                        category_name = stem.replace("_", " ")
                        self.log(
                            f"Предупреждение: файл {csv_file.name} не содержит категорию в имени",
                            "warning",
                        )

                    # Читаем исходный файл с буферизацией
                    with open(csv_file, "r", encoding="utf-8-sig", newline="", buffering=32768) as infile:
                        reader = csv.DictReader(infile)

                        # Проверяем наличие заголовков
                        if not reader.fieldnames:
                            self.log(
                                f"Файл {csv_file} пуст или не имеет заголовков",
                                "warning",
                            )
                            continue

                        # Оптимизация: кэшируем fieldnames для файлов с одинаковой структурой
                        fieldnames_key = tuple(reader.fieldnames)
                        if fieldnames_key not in fieldnames_cache:
                            fieldnames = list(reader.fieldnames)
                            if "Категория" not in fieldnames:
                                fieldnames.insert(0, "Категория")
                            fieldnames_cache[fieldnames_key] = fieldnames
                        else:
                            fieldnames = fieldnames_cache[fieldnames_key]

                        # Создаем writer если ещё не создан
                        if writer is None:
                            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                            writer.writeheader()

                        # Оптимизация: пакетная запись строк
                        batch = []
                        batch_size = 100
                        
                        for row in reader:
                            if "Категория" not in row:
                                row["Категория"] = category_name
                            batch.append(row)
                            
                            # Записываем пакет при достижении размера
                            if len(batch) >= batch_size:
                                writer.writerows(batch)
                                total_rows += len(batch)
                                batch.clear()
                        
                        # Записываем оставшиеся строки
                        if batch:
                            writer.writerows(batch)
                            total_rows += len(batch)

                    # Добавляем файл в список на удаление
                    files_to_delete.append(csv_file)

                # Проверка: если writer остался None, значит все файлы были пустыми
                if writer is None:
                    self.log(
                        "Все CSV файлы пустые или не имеют заголовков. Объединение невозможно.",
                        "warning",
                    )
                    # Очищаем временный файл
                    try:
                        temp_output.unlink()
                        self.log("Временный файл удалён (все файлы пустые)", "debug")
                    except Exception as e:
                        self.log(f"Не удалось удалить временный файл: {e}", "debug")
                    return False

                self.log(f"Объединение завершено. Всего записей: {total_rows}", "info")

            # Переименовываем временный файл в целевой
            # Используем shutil.move как fallback для cross-device перемещения
            rename_success = False
            try:
                temp_output.replace(output_file_path)
                rename_success = True
            except OSError as replace_error:
                try:
                    shutil.move(str(temp_output), str(output_file_path))
                    rename_success = True
                except Exception as move_error:
                    # Очистка временного файла при ошибке перемещения
                    self.log(
                        f"Не удалось переместить временный файл в {output_file}: {move_error}",
                        "error",
                    )
                    try:
                        if temp_output.exists():
                            temp_output.unlink()
                            self.log(
                                "Временный файл удалён после ошибки перемещения",
                                "debug",
                            )
                    except Exception as cleanup_error:
                        self.log(
                            f"Не удалось удалить временный файл: {cleanup_error}",
                            "debug",
                        )
                    raise move_error

            # Удаляем исходные файлы после успешного переименования
            for csv_file in files_to_delete:
                try:
                    csv_file.unlink()
                    self.log(f"Исходный файл удалён: {csv_file.name}", "debug")
                except Exception as e:
                    self.log(f"Не удалось удалить файл {csv_file}: {e}", "warning")

            self.log(
                f"Объединение завершено. Файлы удалены ({len(files_to_delete)} шт.)",
                "info",
            )
            return True

        except Exception as e:
            self.log(f"Ошибка при объединении CSV: {e}", "error")
            try:
                if temp_output.exists():
                    temp_output.unlink()
                    self.log("Временный файл удалён после ошибки", "debug")
            except Exception as e:
                self.log(f"Не удалось удалить временный файл после ошибки: {e}", "debug")
            self.log(
                "Исходные файлы НЕ были удалены (ошибка до завершения объединения)",
                "warning",
            )
            return False

    def run(
        self,
        output_file: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        merge_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Запускает параллельный парсинг всех городов и категорий.

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса парсинга.
            merge_callback: Функция обратного вызова для обновления прогресса объединения.

        Returns:
            True если успешно.
        """
        start_time = time.time()
        total_tasks = len(self.cities) * len(self.categories)

        self.log(f"🚀 Запуск параллельного парсинга ({self.max_workers} потока)", "info")
        self.log(f'📍 Города: {[c["name"] for c in self.cities]}', "info")
        self.log(f"📑 Категории: {len(self.categories)}", "info")
        self.log(f"📊 Всего задач: {total_tasks}", "info")

        # Генерируем все URL
        all_urls = self.generate_all_urls()

        if not all_urls:
            self.log("❌ Нет URL для парсинга", "error")
            return False

        # Запускаем параллельный парсинг
        success_count = 0
        failed_count = 0
        last_progress_time = time.time()

        # Используем таймаут из конфигурации объекта
        self.log(f"⏱️ Таймаут на один URL: {self.timeout_per_url} секунд", "info")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Создаём futures
            futures = {
                executor.submit(
                    self.parse_single_url,
                    url,
                    category_name,
                    city_name,
                    progress_callback,
                ): (url, category_name, city_name)
                for url, category_name, city_name in all_urls
            }

            # Обрабатываем результаты
            for idx, future in enumerate(as_completed(futures), 1):
                url, category_name, city_name = futures[future]

                try:
                    # Получаем результат с таймаутом
                    success, result = future.result(timeout=self.timeout_per_url)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        self.log(
                            f"❌ Не удалось: {city_name} - {category_name}: {result}",
                            "error",
                        )

                    # Выводим прогресс каждые 3 секунды
                    current_time = time.time()
                    if current_time - last_progress_time >= PROGRESS_UPDATE_INTERVAL or idx == len(futures):
                        progress_bar = print_progress(
                            success_count + failed_count,
                            len(futures),
                            prefix="   Прогресс"
                        )
                        self.log(progress_bar, "info")
                        last_progress_time = current_time

                except FuturesTimeoutError:
                    failed_count += 1
                    self.log(
                        f"❌ Таймаут при парсинге {city_name} - {category_name} ({self.timeout_per_url} сек)",
                        "error",
                    )

                except Exception as e:
                    failed_count += 1
                    self.log(
                        f"❌ Исключение при парсинге {city_name} - {category_name}: {e}",
                        "error",
                    )

        # Вычисляем длительность
        duration = time.time() - start_time
        duration_str = f"{duration:.2f} сек."

        self.log(
            f"🏁 Парсинг завершён. Успешно: {success_count}, Ошибок: {failed_count}",
            "info",
        )

        # Объединяем CSV файлы
        if success_count > 0:
            self.log("📁 Начало объединения результатов...", "info")
            merge_success = self.merge_csv_files(output_file, merge_callback)

            if not merge_success:
                self.log("❌ Не удалось объединить CSV файлы", "error")
                log_parser_finish(
                    success=False,
                    stats={
                        "Городов": len(self.cities),
                        "Категорий": len(self.categories),
                        "Успешно": success_count,
                        "Ошибки": failed_count,
                    },
                    duration=duration_str,
                )
                return False
        else:
            self.log("⚠️ Нет успешных результатов для объединения", "warning")
            log_parser_finish(
                success=False,
                stats={
                    "Городов": len(self.cities),
                    "Категорий": len(self.categories),
                    "Успешно": 0,
                    "Ошибки": failed_count,
                },
                duration=duration_str,
            )
            return False

        # Финальный отчёт
        stats = {
            "Городов": len(self.cities),
            "Категорий": len(self.categories),
            "Всего URL": total_tasks,
            "Успешно": success_count,
            "Ошибки": failed_count,
        }
        log_parser_finish(success=True, stats=stats, duration=duration_str)

        return True

    def stop(self) -> None:
        """Останавливает парсинг."""
        self._cancel_event.set()
        self.log("Получена команда остановки парсинга", "warning")


class ParallelCityParserThread(ParallelCityParser, threading.Thread):
    """
    Поток для параллельного парсинга городов.

    Наследуется от ParallelCityParser и threading.Thread для запуска в отдельном потоке.
    """

    def __init__(
        self,
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        timeout_per_url: int = DEFAULT_TIMEOUT,
        output_file: Optional[str] = None,
    ) -> None:
        ParallelCityParser.__init__(
            self,
            cities,
            categories,
            output_dir,
            config,
            max_workers,
            timeout_per_url,
        )
        threading.Thread.__init__(self)

        self._result: Optional[bool] = None
        self._output_file = output_file

    def run(self) -> None:  # type: ignore[override]
        """Точка входа потока."""
        try:
            # Используем переданный output_file или путь по умолчанию
            output_file = self._output_file or str(
                self.output_dir / "merged_result.csv"
            )
            # Вызываем метод родительского класса ParallelCityParser.run
            self._result = ParallelCityParser.run(self, output_file=output_file)
        except Exception as e:
            # Используем self.log() вместо прямого вызова logger для потокобезопасности
            self.log(f"Ошибка в потоке параллельного парсинга: {e}", "error")
            self._result = False

    def get_result(self) -> Optional[bool]:
        """Возвращает результат парсинга."""
        return self._result
