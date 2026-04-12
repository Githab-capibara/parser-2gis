"""Протоколы и EventEmitter для подсистемы параллельного парсинга.

ISSUE 112: Добавлен ConnectionPoolProtocol для альтернативных бэкендов пула соединений.
ISSUE 115: Добавлен EventEmitter для системы событий вместо ad-hoc callbacks.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any, Protocol, runtime_checkable

type UrlTuple = tuple[str, str, str]  # (url, category_name, city_name)


# =============================================================================
# CONNECTION POOL PROTOCOL (ISSUE 112)
# =============================================================================


@runtime_checkable
class ConnectionPoolProtocol(Protocol):
    """Протокол пула соединений для альтернативных бэкендов.

    ISSUE 112: Определяет интерфейс пула соединений, позволяя использовать
    различные реализации (SQLite, PostgreSQL, Redis и т.д.)
    вместо привязки к конкретной реализации ConnectionPool.

    Example:
        >>> class RedisConnectionPool:
        ...     def get_connection(self) -> Any: ...
        ...     def return_connection(self, conn: Any) -> None: ...
        ...     def close(self) -> None: ...
        >>> pool: ConnectionPoolProtocol = RedisConnectionPool()

    """

    def get_connection(self) -> Any:
        """Получает соединение из пула."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def return_connection(self, conn: Any) -> None:
        """Возвращает соединение в пул."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def close(self) -> None:
        """Закрывает все соединения в пуле."""
        # pylint: disable=unnecessary-ellipsis
        ...


# =============================================================================
# EVENT TYPES FOR PARALLEL PARSING (ISSUE 115)
# =============================================================================


class ParsingEvents:
    """Константы событий для параллельного парсинга.

    ISSUE 115: Стандартизированные имена событий для EventEmitter.
    """

    URL_STARTED = "url_started"
    URL_COMPLETED = "url_completed"
    URL_FAILED = "url_failed"
    PROGRESS_UPDATE = "progress_update"
    PARSING_STARTED = "parsing_started"
    PARSING_COMPLETED = "parsing_completed"
    PARSING_CANCELLED = "parsing_cancelled"
    PARSING_ERROR = "parsing_error"
    MERGE_STARTED = "merge_started"
    MERGE_COMPLETED = "merge_completed"
    MERGE_FILE_PROCESSED = "merge_file_processed"
    MEMORY_LOW = "memory_low"
    CLEANUP_COMPLETED = "cleanup_completed"


# =============================================================================
# EVENT EMITTER (ISSUE 115)
# =============================================================================


class EventEmitter:
    """Система событий для параллельного парсинга.

    ISSUE 115: Заменяет ad-hoc callbacks на полноценную систему событий
    с поддержкой множественных подписчиков, фильтрации и приоритетов.

    Example:
        >>> emitter = EventEmitter()
        >>> @emitter.on("progress_update")
        ... def on_progress(data: dict) -> None:
        ...     print(f"Прогресс: {data}")
        >>> emitter.emit("progress_update", {"success": 10, "failed": 2})

    """

    def __init__(self) -> None:
        """Инициализирует систему событий."""
        self._listeners: dict[str, list[tuple[int, Callable[..., Any]]]] = defaultdict(list)
        self._lock = Lock()
        self._once_listeners: dict[str, list[tuple[int, Callable[..., Any]]]] = defaultdict(list)

    def on(
        self, event: str, priority: int = 0,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Декоратор для подписки на событие.

        Args:
            event: Имя события.
            priority: Приоритет обработчика (больше = раньше).

        Returns:
            Декоратор для функции-обработчика.

        Example:
            >>> @emitter.on("progress_update", priority=10)
            ... def handler(data: dict) -> None:
            ...     print(data)

        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self.add_listener(event, func, priority)
            return func

        return decorator

    def once(
        self, event: str, priority: int = 0,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Декоратор для однократной подписки на событие.

        Args:
            event: Имя события.
            priority: Приоритет обработчика.

        Returns:
            Декоратор для функции-обработчика.

        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            with self._lock:
                self._once_listeners[event].append((priority, func))
            return func

        return decorator

    def add_listener(self, event: str, callback: Callable[..., Any], priority: int = 0) -> None:
        """Добавляет слушателя к событию.

        Args:
            event: Имя события.
            callback: Функция-обработчик.
            priority: Приоритет (больше = раньше).

        """
        with self._lock:
            self._listeners[event].append((priority, callback))
            # Сортируем по приоритету (по убыванию)
            self._listeners[event].sort(key=lambda x: x[0], reverse=True)

    def remove_listener(self, event: str, callback: Callable[..., Any]) -> None:
        """Удаляет слушателя от события.

        Args:
            event: Имя события.
            callback: Функция-обработчик для удаления.

        """
        with self._lock:
            self._listeners[event] = [
                (p, cb) for p, cb in self._listeners[event] if cb is not callback
            ]

    def remove_all_listeners(self, event: str | None = None) -> None:
        """Удаляет всех слушателей.

        Args:
            event: Имя события (None для удаления всех).

        """
        with self._lock:
            if event is None:
                self._listeners.clear()
                self._once_listeners.clear()
            else:
                self._listeners.pop(event, None)
                self._once_listeners.pop(event, None)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> list[Any]:
        """Генерирует событие.

        Args:
            event: Имя события.
            *args: Позиционные аргументы для обработчиков.
            **kwargs: Именованные аргументы для обработчиков.

        Returns:
            Список результатов выполнения обработчиков.

        """
        with self._lock:
            # Получаем слушателей и перемещаем once-слушателей
            listeners = list(self._listeners.get(event, []))

            # Добавляем once-слушателей и удаляем их из очереди
            once_listeners = self._once_listeners.pop(event, [])
            listeners.extend(once_listeners)

        # Сортируем по приоритету
        listeners.sort(key=lambda x: x[0], reverse=True)

        results: list[Any] = []
        for _priority, callback in listeners:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except (OSError, RuntimeError, TypeError, ValueError) as e:
                # Логируем ошибку, но не прерываем выполнение других обработчиков
                from parser_2gis.logger.logger import logger

                logger.warning("Ошибка в обработчике события '%s': %s", event, e)

        return results

    def has_listeners(self, event: str | None = None) -> bool:
        """Проверяет наличие слушателей.

        Args:
            event: Имя события (None для проверки всех).

        Returns:
            True если есть слушатели.

        """
        with self._lock:
            if event is None:
                return bool(self._listeners) or bool(self._once_listeners)
            return bool(self._listeners.get(event)) or bool(self._once_listeners.get(event))

    def listener_count(self, event: str) -> int:
        """Возвращает количество слушателей события.

        Args:
            event: Имя события.

        Returns:
            Количество слушателей.

        """
        with self._lock:
            return len(self._listeners.get(event, [])) + len(self._once_listeners.get(event, []))


@runtime_checkable
class CoordinatorProtocol(Protocol):
    """Протокол координатора параллельного парсинга.

    ISSUE 071: Определяет интерфейс координатора для устранения
    прямой зависимости от конкретной реализации.
    """

    def run(
        self,
        output_file: str,
        progress_callback: Callable[[int, int, str], None] | None = None,
        merge_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Запускает параллельный парсинг всех городов и категорий."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def stop(self) -> None:
        """Останавливает парсинг."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def get_statistics(self) -> dict[str, Any]:
        """Возвращает статистику парсинга."""
        # pylint: disable=unnecessary-ellipsis
        ...


@runtime_checkable
class FileMergerProtocol(Protocol):
    """Протокол объединителя файлов.

    ISSUE 071: Определяет интерфейс для объединения выходных файлов.
    """

    def merge_csv_files(
        self, output_file: str, progress_callback: Callable[[str], None] | None = None,
    ) -> bool:
        """Объединяет CSV файлы в один выходной файл."""
        # pylint: disable=unnecessary-ellipsis
        ...


@runtime_checkable
class TempFileManagerProtocol(Protocol):
    """Протокол менеджера временных файлов.

    ISSUE 071: Определяет интерфейс для управления временными файлами.
    """

    def register(self, file_path: Path) -> None:
        """Регистрирует временный файл для последующей очистки."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def unregister(self, file_path: Path) -> None:
        """Удаляет файл из реестра."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def cleanup_all(self) -> tuple[int, int]:
        """Очищает все зарегистрированные временные файлы."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def get_count(self) -> int:
        """Возвращает количество зарегистрированных файлов."""
        # pylint: disable=unnecessary-ellipsis
        ...


@runtime_checkable
class SignalHandlerProtocol(Protocol):
    """Протокол обработчика сигналов.

    ISSUE 073: Определяет интерфейс для обработки системных сигналов
    (SIGINT, SIGTERM) в координаторах параллельного парсинга.
    """

    def __call__(self, signum: int, frame: Any | None) -> None:
        """Вызывается при получении сигнала."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def is_interrupt_requested(self) -> bool:
        """Проверяет, запрошена ли прерывание."""
        # pylint: disable=unnecessary-ellipsis
        ...

    def reset(self) -> None:
        """Сбрасывает состояние обработчика сигналов."""
        # pylint: disable=unnecessary-ellipsis
        ...


@runtime_checkable
class MemoryMonitorProtocol(Protocol):
    """Протокол мониторинга памяти.

    Определяет интерфейс для получения информации о памяти системы.
    """

    def get_available_memory(self) -> int:
        """Получает доступный объем памяти в байтах."""
        # pylint: disable=unnecessary-ellipsis
        ...


__all__ = [
    "ConnectionPoolProtocol",
    "CoordinatorProtocol",
    "EventEmitter",
    "FileMergerProtocol",
    "MemoryMonitorProtocol",
    "ParsingEvents",
    "SignalHandlerProtocol",
    "TempFileManagerProtocol",
    "UrlTuple",
]
