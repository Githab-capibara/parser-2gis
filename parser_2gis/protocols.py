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

from typing_extensions import TypeAlias

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

UrlTuple: TypeAlias = tuple[str, str, str]  # (url, category_name, city_name)
UrlGeneratorResult: TypeAlias = list[UrlTuple]
ParserResult: TypeAlias = list[dict[str, Any]]
ParserStats: TypeAlias = dict[str, Any]
FutureResult: TypeAlias = Future[Any]

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
ProgressCallbackType: TypeAlias = Callable[[int, int, str], None]
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

    def __enter__(self) -> "Writer":
        """Контекстный менеджер для входа."""

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
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

    def update_progress(self, success: bool, filename: str) -> None:
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


__all__ = [
    # Callback Protocols
    "LoggerProtocol",
    "ProgressCallback",
    "CleanupCallback",
    # Data Protocols
    "Writer",
    "Parser",
    # Browser Protocols
    "BrowserNavigation",
    "BrowserContentAccess",
    "BrowserJSExecution",
    "BrowserScreenshot",
    "BrowserService",
    # Cache Protocols
    "CacheReader",
    "CacheWriter",
    # Parallel Parsing Protocols
    "ErrorHandlerProtocol",
    "MergerProtocol",
    "ProgressReporterProtocol",
    "UrlGeneratorProtocol",
    "ThreadCoordinatorProtocol",
    # Path Validation Protocol (ISSUE-034)
    "PathValidatorProtocol",
    # Memory Manager Protocol (ISSUE-019)
    "MemoryManagerProtocol",
]
