"""Protocol для callback и интерфейсов проекта parser-2gis.

Определяет стандартные интерфейсы для различных компонентов системы:
- Callback протоколы для обратных вызовов
- Протоколы данных для writer/parser
- Протоколы браузера для навигации и выполнения JS
- Протоколы кэширования
- Протоколы выполнения
- Протоколы параллельного парсинга

Пример использования:
    >>> from parser_2gis.protocols import LoggerProtocol, ProgressCallback
    >>> def my_logger(msg: str) -> None:
    ...     print(msg)
    >>> logger: LoggerProtocol = my_logger  # type: ignore[arg-type]
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future
from typing import Any, Protocol, runtime_checkable

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

type UrlTuple = tuple[str, str, str]  # (url, category_name, city_name)
type UrlGeneratorResult = list[UrlTuple]
type ParserResult = list[dict[str, Any]]
type ParserStats = dict[str, Any]
type FutureResult = Future[Any]

# =============================================================================
# CALLBACK PROTOCOLS
# =============================================================================


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol для логгера (разрыв циклических зависимостей).

    Определяет стандартный интерфейс для логгеров, позволяя использовать
    различные реализации (logging.Logger, кастомные логгеры и т.д.).

    Example:
        >>> import logging
        >>> logger: LoggerProtocol = logging.getLogger(__name__)
        >>> logger.info("Test message")

    """

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование debug сообщения."""

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование info сообщения."""

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование warning сообщения."""

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование error сообщения."""

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Логирование critical сообщения."""


@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol для callback прогресса параллельного парсинга.

    ISSUE-112, ISSUE-113: Добавлены полные type hints.

    Вызывается при обновлении прогресса выполнения парсинга.

    Example:
        >>> def on_progress(success: int, failed: int, filename: str) -> None:
        ...     print(f"Успешно: {success}, Ошибок: {failed}, Файл: {filename}")
        >>> callback: ProgressCallback = on_progress

    """

    def __call__(self, success: int, failed: int, filename: str) -> None:
        """Вызывается при обновлении прогресса.

        Args:
            success: Количество успешных операций.
            failed: Количество неудачных операций.
            filename: Имя текущего файла.

        """


# ISSUE-112: Type alias для Callable с полными type hints
type ProgressCallbackType = Callable[[int, int, str], None]
"""Type alias для callback прогресса с полными type hints."""


@runtime_checkable
class CleanupCallback(Protocol):
    """Protocol для callback очистки ресурсов.

    Example:
        >>> def cleanup() -> None:
        ...     print("Очистка ресурсов")
        >>> callback: CleanupCallback = cleanup

    """

    def __call__(self) -> None:
        """Вызывается для очистки ресурсов."""


# =============================================================================
# DATA PROTOCOLS
# =============================================================================


@runtime_checkable
class Writer(Protocol):
    """Protocol для записи данных (CSV, XLSX, JSON).

    ISSUE-031: Объединён с FileWriterProtocol для устранения дублирования.
    """

    def write(self, records: list[dict[str, Any]]) -> None:
        """Записывает данные в файл.

        Args:
            records: Список записей для записи.

        """

    def close(self) -> None:
        """Закрывает writer и освобождает ресурсы."""

    def __enter__(self) -> Writer:
        """Контекстный менеджер для входа."""

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Контекстный менеджер для выхода."""


@runtime_checkable
class Parser(Protocol):
    """Protocol для парсеров."""

    def parse(self) -> list[dict[str, Any]]:
        """Выполняет парсинг данных."""

    def get_stats(self) -> dict:
        """Возвращает статистику парсинга."""


# =============================================================================
# BROWSER SERVICE PROTOCOLS
# =============================================================================


@runtime_checkable
class BrowserNavigation(Protocol):
    """Protocol для навигации браузера."""

    def navigate(self, url: str, **kwargs: Any) -> None:
        """Перейти на URL."""


@runtime_checkable
class BrowserContentAccess(Protocol):
    """Protocol для доступа к содержимому страницы."""

    def get_html(self) -> str:
        """Получить HTML страницы."""

    def get_document(self) -> Any:
        """Получить DOM дерево страницы."""


@runtime_checkable
class BrowserJSExecution(Protocol):
    """Protocol для выполнения JavaScript."""

    def execute_js(self, js_code: str, timeout: int | None = None) -> Any:
        """Выполнить JavaScript код."""


@runtime_checkable
class BrowserScreenshot(Protocol):
    """Protocol для создания скриншотов."""

    def screenshot(self, path: str) -> None:
        """Сделать скриншот."""


@runtime_checkable
class BrowserService(
    BrowserNavigation, BrowserContentAccess, BrowserJSExecution, BrowserScreenshot, Protocol
):
    """Абстракция браузера для разрыва связи между chrome/ и parser/."""

    def close(self) -> None:
        """Закрыть браузер и освободить ресурсы."""


# =============================================================================
# CACHE PROTOCOLS
# =============================================================================


@runtime_checkable
class CacheReader(Protocol):
    """Protocol для чтения из кэша."""

    def get(self, key: str) -> Any | None:
        """Получает значение из кэша по ключу."""

    def exists(self, key: str) -> bool:
        """Проверяет наличие ключа в кэше."""


@runtime_checkable
class CacheWriter(Protocol):
    """Protocol для записи в кэш."""

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Устанавливает значение в кэш."""

    def delete(self, key: str) -> None:
        """Удаляет значение из кэша."""


# =============================================================================
# PARALLEL PARSING PROTOCOLS
# =============================================================================


@runtime_checkable
class ErrorHandlerProtocol(Protocol):
    """Protocol для обработчика ошибок параллельного парсинга."""

    def handle_memory_error(self, error: MemoryError, temp_file: Any, url: str) -> tuple[bool, str]:
        """Обрабатывает MemoryError."""

    def handle_timeout_error(
        self, temp_file: Any, city_name: str, category_name: str, timeout: int
    ) -> tuple[bool, str]:
        """Обрабатывает таймаут."""

    def handle_other_error(
        self, error: Exception, temp_file: Any, city_name: str, category_name: str
    ) -> tuple[bool, str]:
        """Обрабатывает другие ошибки."""


@runtime_checkable
class MergerProtocol(Protocol):
    """Protocol для объединителя файлов."""

    def merge_csv_files(
        self, output_file: str, progress_callback: Callable[[str], None] | None = None
    ) -> bool:
        """Объединяет CSV файлы."""


@runtime_checkable
class ProgressReporterProtocol(Protocol):
    """Protocol для репортёра прогресса."""

    def update_progress(self, *, success: bool, filename: str) -> None:
        """Обновляет прогресс."""

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику."""


@runtime_checkable
class UrlGeneratorProtocol(Protocol):
    """Protocol для генератора URL."""

    def generate_all_urls(self) -> list[tuple[str, str, str]]:
        """Генерирует все URL для парсинга."""


@runtime_checkable
class ThreadCoordinatorProtocol(Protocol):
    """Protocol для координатора потоков."""

    def run_parsing(
        self,
        all_urls: list[tuple[str, str, str]],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> bool:
        """Запускает параллельный парсинг."""

    def stop(self) -> None:
        """Останавливает парсинг."""

    @property
    def stats(self) -> dict[str, int]:
        """Возвращает статистику."""


@runtime_checkable
class PathValidatorProtocol(Protocol):
    """Protocol для валидатора путей.

    ISSUE-034: Абстракция для валидации путей и предотвращения path traversal атак.

    Example:
        >>> validator: PathValidatorProtocol = PathValidator()
        >>> validator.validate("/safe/path/file.txt", "output_path")

    """

    def validate(self, path: str, path_name: str = "Путь") -> None:
        """Валидирует путь на безопасность.

        Args:
            path: Путь для валидации.
            path_name: Имя параметра для сообщений об ошибках.

        Raises:
            ValueError: При обнаружении небезопасного пути.
            OSError: При ошибке работы с файловой системой.

        """

    def validate_multiple(self, paths: dict[str, str]) -> None:
        """Валидирует несколько путей одновременно.

        Args:
            paths: Словарь {имя_пути: значение_пути}.

        Raises:
            ValueError: При обнаружении небезопасного пути.
            OSError: При ошибке работы с файловой системой.

        """


@runtime_checkable
class MemoryManagerProtocol(Protocol):
    """Protocol для менеджера памяти.

    ISSUE-019: Абстракция для управления памятью и мониторинга.

    Example:
        >>> manager: MemoryManagerProtocol = MemoryManager()
        >>> if manager.is_memory_low():
        ...     manager.force_gc()

    """

    def get_available_memory(self) -> int:
        """Получает доступный объем памяти в байтах."""

    def is_memory_low(self) -> bool:
        """Проверяет, является ли доступная память низкой."""

    def force_gc(self) -> int:
        """Выполняет принудительный сбор мусора."""

    def handle_memory_error(
        self, error: MemoryError, context: str = "", cache_object: Any | None = None
    ) -> None:
        """Обрабатывает MemoryError."""

    def get_memory_stats(self) -> dict[str, Any]:
        """Получает статистику использования памяти."""


# =============================================================================
# RETRY STRATEGY PROTOCOL (ISSUE 075)
# =============================================================================


@runtime_checkable
class RetryStrategy(Protocol):
    """Протокол стратегии повторных попыток.

    ISSUE 075: Унифицированный протокол для различных стратегий retry.
    Позволяет использовать разные стратегии (fixed, exponential, linear)
    через единый интерфейс.

    Example:
        >>> strategy: RetryStrategy = ExponentialRetryStrategy(max_retries=3, base_delay=1.0)
        >>> for attempt in range(strategy.max_retries):
        ...     delay = strategy.get_delay(attempt)
        ...     if strategy.should_retry(attempt, error):
        ...         time.sleep(delay)

    """

    @property
    def max_retries(self) -> int:
        """Максимальное количество попыток."""
        ...

    def get_delay(self, attempt: int) -> float:
        """Возвращает задержку для данной попытки.

        Args:
            attempt: Номер текущей попытки (0-based).

        Returns:
            Задержка в секундах.

        """
        ...

    def should_retry(self, attempt: int, error: Exception | None = None) -> bool:
        """Определяет, следует ли выполнить повторную попытку.

        Args:
            attempt: Номер текущей попытки (0-based).
            error: Произошедшая ошибка (опционально).

        Returns:
            True если стоит повторить.

        """
        ...


# =============================================================================
# FILE LOCK STRATEGY PROTOCOL (ISSUE 076)
# =============================================================================


@runtime_checkable
class FileLockStrategy(Protocol):
    """Протокол стратегии файловой блокировки.

    ISSUE 076: Абстракция для управления файловыми блокировками.
    Позволяет использовать разные реализации (fcntl, flock, portable).

    Example:
        >>> strategy: FileLockStrategy = FcntlLockStrategy(Path("/tmp/lock"))
        >>> with strategy:
        ...     if strategy.is_acquired:
        ...         # Выполняем защищённую операцию
        ...         pass

    """

    def acquire(self) -> bool:
        """Получает блокировку.

        Returns:
            True если блокировка получена.

        """
        ...

    def release(self) -> None:
        """Освобождает блокировку."""
        ...

    @property
    def is_acquired(self) -> bool:
        """Проверяет, получена ли блокировка."""
        ...

    def __enter__(self) -> bool:
        """Контекстный менеджер: получает блокировку."""
        ...

    def __exit__(self, _exc_type: Any, _exc_val: Any, _exc_tb: Any) -> None:
        """Контекстный менеджер: освобождает блокировку."""
        ...


__all__ = [
    "BrowserContentAccess",
    "BrowserJSExecution",
    # Browser Protocols
    "BrowserNavigation",
    "BrowserScreenshot",
    "BrowserService",
    # Cache Protocols
    "CacheReader",
    "CacheWriter",
    "CleanupCallback",
    # Parallel Parsing Protocols
    "ErrorHandlerProtocol",
    # Retry Strategy Protocol (ISSUE 075)
    "FileLockStrategy",
    # Callback Protocols
    "LoggerProtocol",
    # Memory Manager Protocol (ISSUE-019)
    "MemoryManagerProtocol",
    "MergerProtocol",
    "Parser",
    # Path Validation Protocol (ISSUE-034)
    "PathValidatorProtocol",
    "ProgressCallback",
    "ProgressReporterProtocol",
    "RetryStrategy",
    "ThreadCoordinatorProtocol",
    "UrlGeneratorProtocol",
    # Data Protocols
    "Writer",
]
