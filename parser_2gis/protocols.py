"""
Protocol для callback и интерфейсов проекта parser-2gis.

Этот модуль предоставляет Protocol для типизации callback функций
и других интерфейсов используемых в проекте.

Пример использования:
    >>> from parser_2gis.protocols import ProgressCallback, LogCallback, LoggerProtocol
    >>> def my_progress(success: int, failed: int, filename: str) -> None:
    ...     print(f"Прогресс: {success}/{failed}")
    >>> callback: ProgressCallback = my_progress  # type: check
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol для логгера.

    Используется для разрыва циклической зависимости между
    common.py и logger.py.
    """

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Логирование debug сообщения."""
        pass

    def info(self, msg: str, *args, **kwargs) -> None:
        """Логирование info сообщения."""
        pass

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Логирование warning сообщения."""
        pass

    def error(self, msg: str, *args, **kwargs) -> None:
        """Логирование error сообщения."""
        pass

    def critical(self, msg: str, *args, **kwargs) -> None:
        """Логирование critical сообщения."""
        pass


@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol для callback прогресса параллельного парсинга.

    Используется для уведомления о прогрессе выполнения задач.

    Example:
        >>> def progress_handler(success: int, failed: int, filename: str) -> None:
        ...     print(f"Успешно: {success}, Ошибок: {failed}, Файл: {filename}")
        >>> callback: ProgressCallback = progress_handler
    """

    def __call__(self, success: int, failed: int, filename: str) -> None:
        """Вызывается при обновлении прогресса.

        Args:
            success: Количество успешных операций.
            failed: Количество операций с ошибками.
            filename: Имя текущего файла (если применимо).
        """
        pass


@runtime_checkable
class LogCallback(Protocol):
    """Protocol для callback логирования.

    Используется для передачи сообщений логов между компонентами.

    Example:
        >>> def logger(message: str, level: str = "INFO") -> None:
        ...     print(f"[{level}] {message}")
        >>> callback: LogCallback = logger
    """

    def __call__(self, message: str, level: str = "INFO") -> None:
        """Вызывается для логирования сообщения.

        Args:
            message: Текст сообщения.
            level: Уровень логирования (DEBUG, INFO, WARNING, ERROR).
        """
        pass


@runtime_checkable
class CleanupCallback(Protocol):
    """Protocol для callback очистки ресурсов.

    Используется для вызова процедур очистки.

    Example:
        >>> def cleanup() -> None:
        ...     print("Очистка ресурсов")
        >>> callback: CleanupCallback = cleanup
    """

    def __call__(self) -> None:
        """Вызывается для очистки ресурсов."""
        pass


@runtime_checkable
class CancelCallback(Protocol):
    """Protocol для callback проверки отмены операции.

    Используется для проверки флага отмены в длительных операциях.

    Example:
        >>> def should_cancel() -> bool:
        ...     return False  # или проверка внешнего флага
        >>> callback: CancelCallback = should_cancel
    """

    def __call__(self) -> bool:
        """Проверяет необходимость отмены операции.

        Returns:
            True если операция должна быть отменена.
        """
        pass


@runtime_checkable
class Writer(Protocol):
    """Protocol для записи данных.

    Определяет интерфейс для всех writers (CSV, XLSX, JSON).

    Example:
        >>> class CSVWriter:
        ...     def write(self, records: list[dict]) -> None:
        ...         pass
        ...     def close(self) -> None:
        ...         pass
        >>> writer: Writer = CSVWriter(...)
    """

    def write(self, records: list[dict]) -> None:
        """Записывает данные.

        Args:
            records: Список записей для записи.
        """
        pass

    def close(self) -> None:
        """Закрывает writer и освобождает ресурсы."""
        pass


@runtime_checkable
class Parser(Protocol):
    """Protocol для парсеров.

    Определяет интерфейс для всех парсеров.

    Example:
        >>> class FirmParser:
        ...     def parse(self) -> list[dict]:
        ...         pass
        ...     def get_stats(self) -> dict:
        ...         pass
        >>> parser: Parser = FirmParser(...)
    """

    def parse(self) -> list[dict]:
        """Выполняет парсинг данных.

        Returns:
            Список спарсенных записей.
        """
        pass

    def get_stats(self) -> dict:
        """Возвращает статистику парсинга.

        Returns:
            Словарь со статистикой.
        """
        pass


@runtime_checkable
class BrowserService(Protocol):
    """Абстракция браузера для разрыва связи между chrome/ и parser/.

    Определяет минимальный интерфейс для работы с браузером:
    - Навигация по URL
    - Получение HTML
    - Выполнение JavaScript
    - Создание скриншотов
    - Закрытие браузера

    Example:
        >>> from parser_2gis.chrome import ChromeRemote
        >>> browser: BrowserService = ChromeRemote(...)  # type: check
    """

    def navigate(self, url: str) -> None:
        """Перейти на URL.

        Args:
            url: URL для навигации.
        """
        pass

    def get_html(self) -> str:
        """Получить HTML страницы.

        Returns:
            HTML содержимое текущей страницы.
        """
        pass

    def execute_js(self, js_code: str, timeout: Optional[int] = None) -> Any:
        """Выполнить JavaScript код.

        Args:
            js_code: JavaScript код для выполнения.
            timeout: Таймаут выполнения в секундах (опционально).

        Returns:
            Результат выполнения JavaScript.
        """
        pass

    def screenshot(self, path: str) -> None:
        """Сделать скриншот.

        Args:
            path: Путь для сохранения скриншота.
        """
        pass

    def close(self) -> None:
        """Закрыть браузер и освободить ресурсы."""
        pass


__all__ = [
    "LoggerProtocol",
    "ProgressCallback",
    "LogCallback",
    "CleanupCallback",
    "CancelCallback",
    "Writer",
    "Parser",
    "BrowserService",
]
