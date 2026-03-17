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

import fcntl
import os
import shutil
import signal
import tempfile
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

# =============================================================================
# КОНСТАНТЫ ВАЛИДАЦИИ ПАРАМЕТРОВ
# =============================================================================

# Минимальное количество рабочих потоков (минимум 1)
MIN_WORKERS: int = 1

# Максимальное количество рабочих потоков (ограничение для стабильности)
MAX_WORKERS: int = 20

# Минимальный таймаут на один URL в секундах (1 минута)
MIN_TIMEOUT: int = 60

# Максимальный таймаут на один URL в секундах (1 час)
MAX_TIMEOUT: int = 3600

# Таймаут по умолчанию на один URL в секундах (5 минут)
DEFAULT_TIMEOUT: int = 300

# =============================================================================
# КОНСТАНТЫ ПРОГРЕССА И ОТОБРАЖЕНИЯ
# =============================================================================

# Интервал обновления прогресс-бара в секундах
PROGRESS_UPDATE_INTERVAL: int = 3

# =============================================================================
# КОНСТАНТЫ ДЛЯ СЛИЯНИЯ ФАЙЛОВ И БУФЕРИЗАЦИИ
# =============================================================================

# Размер буфера для чтения/записи файлов в байтах (128 KB)
# Увеличенный буфер улучшает производительность при работе с большими файлами
MERGE_BUFFER_SIZE: int = 131072

# Размер пакета строк для пакетной записи в CSV
# Оптимальное значение для баланса между памятью и производительностью
MERGE_BATCH_SIZE: int = 500

# =============================================================================
# КОНСТАНТЫ ДЛЯ УНИКАЛЬНЫХ ИМЁН ФАЙЛОВ
# =============================================================================

# Максимальное количество попыток создания уникального имени файла
# Защищает от бесконечного цикла при коллизиях имён
MAX_UNIQUE_NAME_ATTEMPTS: int = 10

# =============================================================================
# КОНСТАНТЫ ДЛЯ БЛОКИРОВОК И ЗАЩИТЫ ОТ CONCURRENT OPERATIONS
# =============================================================================

# Таймаут ожидания блокировки merge операции в секундах
MERGE_LOCK_TIMEOUT: int = 300

# Максимальный возраст lock файла в секундах (5 минут)
# Lock файлы старше этого возраста считаются осиротевшими
MAX_LOCK_FILE_AGE: int = 300


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
            raise ValueError(
                f"timeout_per_url должен быть от {MIN_TIMEOUT} до {MAX_TIMEOUT} секунд"
            )

        self.cities = cities
        self.categories = categories
        self.output_dir = Path(output_dir)
        self.config = config
        self.max_workers = max_workers
        self.timeout_per_url = timeout_per_url

        # Проверка существования output_dir и прав на запись
        if self.output_dir.exists():
            if not self.output_dir.is_dir():
                raise ValueError(f"output_dir существует, но не является директорией: {output_dir}")
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
                            "Не удалось удалить тестовый файл %s: %s", test_file, cleanup_error
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
                            "Не удалось удалить тестовый файл %s: %s", test_file, cleanup_error
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

        # Список для отслеживания временных файлов merge операции (используется вместо глобальной переменной)
        self._merge_temp_files: List[Path] = []
        # Блокировка для потокобезопасного доступа к временным файлам
        self._merge_lock = threading.Lock()

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

        # Исправление проблемы 11: добавляем обработку timeout_per_url
        # Используем signal.alarm для установки таймаута на парсинг (только Unix)
        timeout_occurred = False
        use_signal_timeout = hasattr(signal, 'alarm')  # Проверяем поддержку signal.alarm

        # Формируем целевое имя файла
        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_city}_{safe_category}.csv"
        filepath = self.output_dir / filename

        # Создаём уникальное временное имя файла
        # ВАЖНО: Используем PID процесса для уникальности и предотвращения race condition
        # uuid.uuid4() + pid гарантирует уникальность даже при параллельном запуске
        temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
        temp_filepath = self.output_dir / temp_filename

        # ВАЖНО: Атомарное создание временного файла для предотвращения race condition
        # Используем os.open() с флагами O_CREAT | O_EXCL для атомарного создания
        # Это гарантирует, что между проверкой и созданием файла не будет гонки условий
        temp_fd = None
        for attempt in range(MAX_UNIQUE_NAME_ATTEMPTS):
            try:
                # Атомарное создание файла через os.open с O_CREAT | O_EXCL
                # O_CREAT - создать файл если не существует
                # O_EXCL - выбросить ошибку если файл уже существует (вместе с O_CREAT)
                # O_WRONLY - открыть для записи
                # O_CREAT | O_EXCL гарантирует атомарное создание
                temp_fd = os.open(
                    str(temp_filepath),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    mode=0o644  # Права доступа: владелец чтение/запись, остальные чтение
                )
                # Закрываем файловый дескриптор - файл создан
                os.close(temp_fd)
                temp_fd = None
                logger.debug("Временный файл атомарно создан через os.open: %s", temp_filename)
                break  # Успех - выходим из цикла
            except FileExistsError:
                # Файл уже существует (race condition) - генерируем новое имя
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.debug(
                        "Временный файл уже существует (попытка %d): %s. Генерация нового имени...",
                        attempt + 1,
                        temp_filename,
                    )
                    temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
                    temp_filepath = self.output_dir / temp_filename
                else:
                    logger.error(
                        "Не удалось создать уникальный временный файл после %d попыток: %s",
                        MAX_UNIQUE_NAME_ATTEMPTS,
                        temp_filename,
                    )
                    raise
            except OSError as os_error:
                # Ошибка при создании файла
                if temp_fd is not None:
                    try:
                        os.close(temp_fd)
                    except OSError:
                        pass
                    temp_fd = None
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.debug(
                        "Ошибка при создании временного файла (попытка %d): %s. Повторная попытка...",
                        attempt + 1,
                        os_error,
                    )
                    temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{uuid.uuid4().hex}.tmp"
                    temp_filepath = self.output_dir / temp_filename
                else:
                    logger.error(
                        "Не удалось создать временный файл после %d попыток: %s",
                        MAX_UNIQUE_NAME_ATTEMPTS,
                        temp_filename,
                    )
                    raise

        # Исправление проблемы 11: устанавливаем таймаут на парсинг через signal.alarm
        # Сохраняем старый обработчик SIGALRM для восстановления
        old_handler = None
        if use_signal_timeout:
            def timeout_handler(signum, frame):
                """Обработчик сигнала таймаута."""
                nonlocal timeout_occurred
                timeout_occurred = True
                raise TimeoutError(f"Превышен таймаут парсинга ({self.timeout_per_url} сек)")

            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(self.timeout_per_url)  # Устанавливаем таймаут

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
                # Writer создаст свой файл, заменив пустой временный файл
                with get_writer(str(temp_filepath), "csv", self.config.writer) as writer:
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
                self.log(
                    f"Не удалось переименовать файл (OSError): {replace_error}. Используем shutil.move",
                    "debug",
                )
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
                self.log(f"Временный файл переименован: {temp_filename} → {filename}", "debug")

            self.log(f"Завершён парсинг: {city_name} - {category_name} → {filepath}", "info")

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats["success"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, filepath.name)

            return True, str(filepath)

        except TimeoutError as timeout_error:
            # Исправление проблемы 11: обработка таймаута парсинга
            self.log(
                f"Таймаут парсинга {city_name} - {category_name} ({self.timeout_per_url} сек): {timeout_error}",
                "error",
            )

            # Удаляем временный файл при таймауте
            try:
                if temp_filepath.exists():
                    temp_filepath.unlink()
                    self.log(f"Временный файл удалён после таймаута: {temp_filename}", "debug")
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

            return False, f"Таймаут: {timeout_error}"

        except Exception as e:
            self.log(f"Ошибка парсинга {city_name} - {category_name}: {e}", "error")

            # Удаляем временный файл при ошибке
            try:
                if temp_filepath.exists():
                    temp_filepath.unlink()
                    self.log(f"Временный файл удалён после ошибки: {temp_filename}", "debug")
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

        finally:
            # Исправление проблемы 11: отменяем таймаут и восстанавливаем обработчик
            if use_signal_timeout and old_handler is not None:
                signal.alarm(0)  # Отменяем таймаут
                signal.signal(signal.SIGALRM, old_handler)  # Восстанавливаем обработчик

    def merge_csv_files(
        self,
        output_file: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Объединяет все CSV файлы в один с добавлением колонки "Категория".

        Оптимизация:
        - Увеличенная буферизация чтения/записи (128KB вместо 32KB)
        - Предварительное вычисление категории для снижения операций в цикле
        - Увеличенный размер пакета для записи (500 строк вместо 100)
        - Использование list comprehension для быстрой фильтрации
        - Предварительное резервирование места на диске

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
        import io

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

        # Сортируем файлы по имени для детерминированного порядка
        csv_files.sort(key=lambda x: x.name)

        # Список файлов для удаления (заполняется после успешного объединения)
        files_to_delete: list[Path] = []

        # Создаём временный файл для результата объединения
        temp_output = self.output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"
        temp_file_created = False  # Флаг для отслеживания создания временного файла

        # Lock file для защиты от concurrent merge операций
        lock_file_path = self.output_dir / ".merge.lock"
        lock_file_handle = None
        lock_acquired = False

        # Оптимизация 19: используем увеличенную буферизацию и пакетную обработку
        output_encoding = self.config.writer.encoding
        # Используем предопределённые константы для буферизации и размера пакета
        buffer_size = MERGE_BUFFER_SIZE  # 128KB буфер для чтения/записи
        batch_size = MERGE_BATCH_SIZE  # Размер пакета для записи (500 строк)

        # =====================================================================
        # БЛОКИРОВКА 1: Получаем lock file для предотвращения concurrent merge
        # =====================================================================
        try:
            # Проверяем возраст существующего lock файла
            if lock_file_path.exists():
                try:
                    lock_age = time.time() - lock_file_path.stat().st_mtime
                    if lock_age > MAX_LOCK_FILE_AGE:
                        # Lock файл осиротевший - удаляем
                        self.log(
                            f"Удаление осиротевшего lock файла (возраст: {lock_age:.0f} сек)",
                            "debug",
                        )
                        lock_file_path.unlink()
                    else:
                        self.log(
                            f"Lock файл существует (возраст: {lock_age:.0f} сек), ожидаем...",
                            "warning",
                        )
                except OSError:
                    pass

            # Пытаемся получить блокировку с таймаутом
            start_time = time.time()
            while not lock_acquired:
                try:
                    # Атомарное создание lock файла с эксклюзивной блокировкой
                    lock_file_handle = open(lock_file_path, 'w')
                    fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # Записываем PID процесса для отладки
                    lock_file_handle.write(f"{os.getpid()}\n")
                    lock_file_handle.flush()
                    lock_acquired = True
                    self.log("Lock file получен успешно", "debug")
                except (IOError, OSError):
                    # Блокировка занята другим процессом
                    if lock_file_handle:
                        try:
                            lock_file_handle.close()
                        except Exception:
                            pass
                        lock_file_handle = None

                    # Проверяем таймаут ожидания
                    if time.time() - start_time > MERGE_LOCK_TIMEOUT:
                        self.log(
                            f"Таймаут ожидания lock файла ({MERGE_LOCK_TIMEOUT} сек)",
                            "error",
                        )
                        return False

                    # Ждём перед следующей попыткой
                    time.sleep(1)

        except Exception as lock_error:
            self.log(f"Ошибка при получении lock файла: {lock_error}", "error")
            if lock_file_handle:
                try:
                    lock_file_handle.close()
                except Exception:
                    pass
            return False

        # =====================================================================
        # БЛОКИРОВКА 2: Signal handler для очистки при KeyboardInterrupt
        # =====================================================================
        # Сохраняем старые обработчики сигналов
        old_sigint_handler = signal.getsignal(signal.SIGINT)
        old_sigterm_handler = signal.getsignal(signal.SIGTERM)

        def cleanup_temp_files():
            """Функция очистки временных файлов при прерывании."""
            with self._merge_lock:
                for temp_file in self._merge_temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                            self.log(f"Временный файл удалён при прерывании: {temp_file}", "debug")
                    except Exception:
                        pass

        def signal_handler(signum, frame):
            """Обработчик сигналов прерывания."""
            self.log(f"Получен сигнал {signum}, очистка временных файлов...", "warning")
            cleanup_temp_files()
            # Вызываем старый обработчик
            if callable(old_sigint_handler):
                old_sigint_handler(signum, frame)

        # Устанавливаем наши обработчики
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Регистрируем временный файл для очистки при прерывании
            with self._merge_lock:
                self._merge_temp_files.append(temp_output)

            # Открываем с увеличенной буферизацией для улучшения производительности
            with open(
                temp_output, "w", encoding=output_encoding, newline="", buffering=buffer_size
            ) as outfile:
                temp_file_created = True  # Файл создан успешно
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
                        category_name = stem[last_underscore_idx + 1 :].replace("_", " ")
                    else:
                        category_name = stem.replace("_", " ")
                        self.log(
                            f"Предупреждение: файл {csv_file.name} не содержит категорию в имени",
                            "warning",
                        )

                    # Читаем исходный файл с увеличенной буферизацией
                    with open(
                        csv_file, "r", encoding="utf-8-sig", newline="", buffering=buffer_size
                    ) as infile:
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

                        # Оптимизация 19: пакетная обработка строк (по 500 строк)
                        # Уменьшаем количество операций записи через буферизацию
                        batch = []
                        batch_total = 0

                        for row in reader:
                            # Оптимизация 19: создаём новую строку сразу с категорией
                            # Избегаем мутации исходного словаря, создаём копию
                            row_with_category = {
                                "Категория": category_name,
                                **row
                            }
                            batch.append(row_with_category)

                            # Записываем пакет при достижении размера
                            if len(batch) >= batch_size:
                                writer.writerows(batch)
                                batch_total += len(batch)
                                batch.clear()

                        # Записываем оставшиеся строки (неполный пакет)
                        if batch:
                            writer.writerows(batch)
                            batch_total += len(batch)

                        total_rows += batch_total
                        self.log(
                            "Файл %s обработан (строк: %d, пакетов: %d)",
                            csv_file.name,
                            batch_total,
                            (batch_total // batch_size) + (1 if batch_total % batch_size else 0),
                            level="debug"
                        )

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

                    # Удаляем lock файл
                    try:
                        if lock_file_handle:
                            fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
                            lock_file_handle.close()
                            lock_file_path.unlink()
                    except Exception:
                        pass

                    return False

                self.log(f"Объединение завершено. Всего записей: {total_rows}", "info")

            # Переименовываем временный файл в целевой
            # Используем shutil.move как fallback для cross-device перемещения
            rename_success = False
            try:
                temp_output.replace(output_file_path)
                rename_success = True
            except OSError as replace_error:
                # Fallback для перемещения между разными файловыми системами
                self.log(
                    f"Не удалось переименовать файл (OSError): {replace_error}. Используем shutil.move",
                    "debug",
                )
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
            temp_file_created = False  # Файл успешно перемещён, не нужно удалять

            # Удаляем lock файл
            try:
                if lock_file_handle:
                    fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
                    lock_file_handle.close()
                    lock_file_path.unlink()
                    self.log("Lock файл удалён", "debug")
            except Exception as lock_error:
                self.log(f"Ошибка при удалении lock файла: {lock_error}", "debug")

            return True

        except KeyboardInterrupt:
            # Обработка прерывания пользователем (Ctrl+C)
            self.log("Объединение прервано пользователем (KeyboardInterrupt)", "warning")
            cleanup_temp_files()
            return False

        except Exception as e:
            self.log(f"Ошибка при объединении CSV: {e}", "error")
            return False

        finally:
            # Восстанавливаем старые обработчики сигналов
            try:
                signal.signal(signal.SIGINT, old_sigint_handler)
                signal.signal(signal.SIGTERM, old_sigterm_handler)
            except Exception:
                pass

            # Гарантированная очистка временного файла если он ещё существует
            # Это защищает от утечек файлов при KeyboardInterrupt или других исключениях
            if temp_file_created and temp_output.exists():
                try:
                    temp_output.unlink()
                    self.log(
                        "Временный файл удалён в блоке finally (защита от утечек)",
                        "debug",
                    )
                except Exception as cleanup_error:
                    self.log(
                        f"Не удалось удалить временный файл в finally: {cleanup_error}",
                        "warning",
                    )

            # Освобождаем блокировку и удаляем lock файл если ещё существует
            try:
                if lock_file_handle:
                    try:
                        fcntl.flock(lock_file_handle.fileno(), fcntl.LOCK_UN)
                        lock_file_handle.close()
                    except Exception:
                        pass
                if lock_file_path.exists():
                    lock_file_path.unlink()
            except Exception:
                pass

            # Удаляем временный файл из списка экземпляра
            with self._merge_lock:
                if temp_output in self._merge_temp_files:
                    self._merge_temp_files.remove(temp_output)

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
                    if current_time - last_progress_time >= PROGRESS_UPDATE_INTERVAL or idx == len(
                        futures
                    ):
                        progress_bar = print_progress(
                            success_count + failed_count, len(futures), prefix="   Прогресс"
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
            output_file = self._output_file or str(self.output_dir / "merged_result.csv")
            # Вызываем метод родительского класса ParallelCityParser.run
            self._result = ParallelCityParser.run(self, output_file=output_file)
        except Exception as e:
            # Используем self.log() вместо прямого вызова logger для потокобезопасности
            self.log(f"Ошибка в потоке параллельного парсинга: {e}", "error")
            self._result = False

    def get_result(self) -> Optional[bool]:
        """Возвращает результат парсинга."""
        return self._result
