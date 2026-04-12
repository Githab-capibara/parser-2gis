"""Модуль обработки ошибок для параллельного парсинга.

Предоставляет класс ParallelErrorHandler для обработки ошибок:
- Обработка ошибок Chrome и таймаутов
- Управление временными файлами при ошибках
- Повторные попытки при ошибках инициализации
- Логирование и статистика ошибок
"""

from __future__ import annotations

import gc
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from parser_2gis.chrome.exceptions import ChromeException
from parser_2gis.constants import MAX_UNIQUE_NAME_ATTEMPTS
from parser_2gis.logger import logger
from parser_2gis.parallel.cleanup_utils import cleanup_temp_file

if TYPE_CHECKING:
    from parser_2gis.config import Configuration

# Константы для повторных попыток по умолчанию
DEFAULT_BASE_DELAY: float = 5.0
"""Базовая задержка между попытками в секундах."""

DEFAULT_MAX_RETRIES: int = 10
"""Максимальное количество повторных попыток."""


class ParallelErrorHandler:
    """Класс для обработки ошибок в параллельном парсинге.

    Предоставляет функциональность для:
    - Обработки ошибок Chrome и таймаутов
    - Управления временными файлами при ошибках
    - Повторных попыток при ошибках инициализации
    - Логирования и статистики ошибок

    Attributes:
        output_dir: Директория для выходных файлов.
        config: Конфигурация парсера.
        stats: Словарь со статистикой ошибок.

    """

    def __init__(self, output_dir: Path, config: Configuration) -> None:
        """Инициализация обработчика ошибок.

        Args:
            output_dir: Директория для выходных файлов.
            config: Конфигурация парсера.

        """
        self.output_dir = output_dir
        self.config = config
        self.stats = {
            "chrome_errors": 0,
            "timeout_errors": 0,
            "init_errors": 0,
            "memory_errors": 0,
            "other_errors": 0,
        }

    def log(self, message: str, level: str = "info") -> None:
        """Логгирование сообщения.

        Args:
            message: Текст сообщения.
            level: Уровень логирования.

        """
        log_func = getattr(logger, level)
        log_func(message)

    def handle_chrome_error(
        self,
        chrome_error: ChromeException,
        temp_filepath: Path,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> tuple[bool, str]:
        """Обрабатывает ошибку Chrome.

        Args:
            chrome_error: Исключение Chrome.
            temp_filepath: Путь к временному файлу.
            max_retries: Максимальное количество попыток.

        Returns:
            Кортеж (success, message).

        """
        self.stats["chrome_errors"] += 1
        self.log(f"Ошибка Chrome после {max_retries} попыток: {chrome_error}", "error")
        self._cleanup_temp_file(temp_filepath)
        return False, f"Ошибка Chrome: {chrome_error}"

    def handle_init_error(
        self, init_error: Exception, temp_filepath: Path, url: str
    ) -> tuple[bool, str]:
        """Обрабатывает ошибку инициализации.

        Args:
            init_error: Исключение инициализации.
            temp_filepath: Путь к временному файлу.
            url: URL, на котором произошла ошибка.

        Returns:
            Кортеж (success, message).

        """
        self.stats["init_errors"] += 1
        self.log(f"Ошибка инициализации для {url}: {init_error}", "error")
        self._cleanup_temp_file(temp_filepath)
        return False, f"Ошибка инициализации: {init_error}"

    def handle_timeout_error(
        self, temp_filepath: Path, city_name: str, category_name: str, timeout: int
    ) -> tuple[bool, str]:
        """Обрабатывает ошибку таймаута.

        Args:
            temp_filepath: Путь к временному файлу.
            city_name: Название города.
            category_name: Название категории.
            timeout: Таймаут в секундах.

        Returns:
            Кортеж (success, message).

        """
        self.stats["timeout_errors"] += 1
        self.log(f"Таймаут парсинга {city_name} - {category_name} ({timeout} сек)", "error")
        self._cleanup_temp_file(temp_filepath)
        return False, f"Таймаут: {timeout} сек"

    def handle_memory_error(
        self, memory_error: MemoryError, temp_filepath: Path, url: str
    ) -> tuple[bool, str]:
        """Обрабатывает ошибку памяти.

        Args:
            memory_error: Исключение памяти.
            temp_filepath: Путь к временному файлу.
            url: URL, на котором произошла ошибка.

        Returns:
            Кортеж (success, message).

        """
        self.stats["memory_errors"] += 1
        self.log(f"Memory error while parsing {url}: {memory_error}", "error")
        # Принудительный GC через memory_manager если доступен
        if hasattr(self, "_memory_manager"):
            self._memory_manager.force_gc()
        else:
            gc.collect()
        self._cleanup_temp_file(temp_filepath)
        return False, f"Ошибка памяти: {memory_error}"

    def handle_other_error(
        self, error: Exception, temp_filepath: Path, city_name: str, category_name: str
    ) -> tuple[bool, str]:
        """Обрабатывает прочие ошибки.

        Args:
            error: Исключение.
            temp_filepath: Путь к временному файлу.
            city_name: Название города.
            category_name: Название категории.

        Returns:
            Кортеж (success, message).

        """
        self.stats["other_errors"] += 1
        self.log(f"Ошибка парсинга {city_name} - {category_name}: {error}", "error")
        self._cleanup_temp_file(temp_filepath)
        return False, str(error)

    def _cleanup_temp_file(self, temp_filepath: Path) -> None:
        """Очищает временный файл.

        Args:
            temp_filepath: Путь к временному файлу.

        """
        # #63: Использует общую утилиту из cleanup_utils.py
        cleanup_temp_file(
            temp_filepath, log_func=self.log, description="Временный файл удалён после ошибки"
        )

    def create_unique_temp_file(self, city_name: str, category_name: str) -> Path:
        """Создаёт уникальный временный файл.

        #191: Добавлена валидация city_name.

        Args:
            city_name: Название города.
            category_name: Название категории.

        Returns:
            Путь к временному файлу.

        Raises:
            ValueError: Если city_name пустой.
            RuntimeError: Если не удалось создать уникальный файл.

        """
        # #191: Валидация city_name
        if not city_name or not city_name.strip():
            raise ValueError("city_name не может быть пустым")

        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{id(self)}.tmp"
        temp_filepath = self.output_dir / temp_filename

        for attempt in range(MAX_UNIQUE_NAME_ATTEMPTS):
            try:
                # Атомарное создание файла
                fd = os.open(str(temp_filepath), os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode=0o644)
                os.close(fd)
                logger.log(5, "Временный файл атомарно создан: %s", temp_filename)
                return temp_filepath
            except FileExistsError as e:
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.log(5, "Коллизия имён (попытка %d): генерация нового имени", attempt + 1)
                    temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{id(self)}.tmp"
                    temp_filepath = self.output_dir / temp_filename
                else:
                    logger.error(
                        "Не удалось создать уникальный временный файл после %d попыток: %s",
                        MAX_UNIQUE_NAME_ATTEMPTS,
                        temp_filename,
                    )
                    msg = (
                        "Не удалось создать уникальный временный файл "
                        f"после {MAX_UNIQUE_NAME_ATTEMPTS} попыток"
                    )
                    raise RuntimeError(
                        msg
                    ) from e
            except OSError:
                if attempt < MAX_UNIQUE_NAME_ATTEMPTS - 1:
                    logger.log(
                        5, "Ошибка создания файла (попытка %d): повторная попытка", attempt + 1
                    )
                    temp_filename = f"{safe_city}_{safe_category}_{os.getpid()}_{id(self)}.tmp"
                    temp_filepath = self.output_dir / temp_filename
                else:
                    logger.error(
                        "Не удалось создать временный файл после %d попыток: %s",
                        MAX_UNIQUE_NAME_ATTEMPTS,
                        temp_filename,
                    )
                    raise

        # Должно быть выброшено в цикле выше
        raise RuntimeError("Не удалось создать временный файл")

    def retry_with_backoff(
        self,
        func: Callable[[], Any],
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
    ) -> Any:
        """Выполняет функцию с повторными попытками и экспоненциальной задержкой.

        Args:
            func: Функция для выполнения.
            max_retries: Максимальное количество попыток.
            base_delay: Базовая задержка в секундах.

        Returns:
            Результат выполнения функции.

        Raises:
            Exception: Последнее исключение, если все попытки не удались.

        """
        # Явная проверка edge case: max_retries=0
        # #186: При max_retries=0 выполняем функцию один раз и возвращаем результат
        if max_retries <= 0:
            return func()

        retry_delay = base_delay

        for attempt in range(max_retries):
            try:
                return func()
            except ChromeException as chrome_error:
                if attempt < max_retries - 1:
                    self.log(
                        f"Попытка {attempt + 1}/{max_retries} не удалась: {chrome_error}. "
                        f"Повтор через {retry_delay:.1f} сек...",
                        "warning",
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise

        # Должно быть выброшено в цикле выше — явная защита от непредвиденного завершения
        raise RuntimeError("Цикл повторных попыток исчерпан без результата или исключения")
