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

from concurrent.futures import Future
from typing import Any, Callable, Iterator, Protocol, runtime_checkable


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

    def execute_js(self, js_code: str, timeout: int | None = None) -> Any:
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


# =============================================================================
# PROTOCOL ДЛЯ КЭШИРОВАНИЯ
# =============================================================================


@runtime_checkable
class CacheBackend(Protocol):
    """Абстракция бэкенда кэширования.

    Определяет интерфейс для всех бэкендов кэширования (Redis, SQLite, in-memory).
    Позволяет легко переключаться между различными реализациями кэша.

    Example:
        >>> from parser_2gis.cache import CacheManager
        >>> cache: CacheBackend = CacheManager(...)  # type: check
        >>> cache.set("key", "value", ttl=3600)
        >>> value = cache.get("key")
        >>> cache.delete("key")
    """

    def get(self, key: str) -> Any | None:
        """Получает значение из кэша по ключу.

        Args:
            key: Ключ для получения.

        Returns:
            Значение из кэша или None если ключ не найден.
        """
        pass

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Устанавливает значение в кэш.

        Args:
            key: Ключ для установки.
            value: Значение для кэширования.
            ttl: Время жизни кэша в секундах.
        """
        pass

    def delete(self, key: str) -> None:
        """Удаляет значение из кэша.

        Args:
            key: Ключ для удаления.
        """
        pass

    def exists(self, key: str) -> bool:
        """Проверяет наличие ключа в кэше.

        Args:
            key: Ключ для проверки.

        Returns:
            True если ключ существует.
        """
        pass


# =============================================================================
# PROTOCOL ДЛЯ ПАРАЛЛЕЛЬНОГО ВЫПОЛНЕНИЯ
# =============================================================================


@runtime_checkable
class ExecutionBackend(Protocol):
    """Абстракция бэкенда для параллельного выполнения.

    Определяет интерфейс для всех бэкендов выполнения (ThreadPoolExecutor,
    ProcessPoolExecutor, asyncio). Позволяет легко переключаться между
    различными стратегиями параллелизма.

    Example:
        >>> from concurrent.futures import ThreadPoolExecutor
        >>> executor: ExecutionBackend = ThreadPoolExecutor(max_workers=10)  # type: check
        >>> future = executor.submit(my_function, arg1, arg2)
        >>> results = list(executor.map(process_function, items))
        >>> executor.shutdown(wait=True)
    """

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Future:
        """Отправляет функцию на выполнение.

        Args:
            fn: Функция для выполнения.
            *args: Позиционные аргументы для функции.
            **kwargs: Именованные аргументы для функции.

        Returns:
            Future объект для получения результата.
        """
        pass

    def map(self, fn: Callable, *iterables: Any, timeout: float | None = None) -> Iterator[Any]:
        """Выполняет функцию для каждого элемента итерации.

        Args:
            fn: Функция для выполнения.
            *iterables: Итерируемые объекты с аргументами.
            timeout: Таймаут выполнения в секундах (опционально).

        Returns:
            Итератор с результатами выполнения.
        """
        pass

    def shutdown(self, wait: bool = True, cancel_futures: bool = False) -> None:
        """Останавливает executor и освобождает ресурсы.

        Args:
            wait: Ждать завершения всех задач.
            cancel_futures: Отменить незавершённые задачи (Python 3.9+).
        """
        pass


# =============================================================================
# PROTOCOL ДЛЯ ФАБРИК
# =============================================================================


@runtime_checkable
class ParserFactory(Protocol):
    """Абстракция фабрики парсеров.

    Определяет интерфейс для создания парсеров различных типов.
    Позволяет легко добавлять новые типы парсеров без изменения кода.

    Example:
        >>> from parser_2gis.parser import ParserFactoryImpl
        >>> factory: ParserFactory = ParserFactoryImpl()  # type: check
        >>> parser = factory.get_parser("firm", browser=browser)
        >>> results = parser.parse()
    """

    def get_parser(self, parser_type: str, **kwargs: Any) -> Any:
        """Создаёт парсер указанного типа.

        Args:
            parser_type: Тип парсера ("firm", "in_building", "main").
            **kwargs: Дополнительные аргументы для парсера.

        Returns:
            Экземпляр парсера.
        """
        pass


@runtime_checkable
class WriterFactory(Protocol):
    """Абстракция фабрики писателей.

    Определяет интерфейс для создания писателей различных форматов.
    Позволяет легко добавлять новые форматы вывода без изменения кода.

    Example:
        >>> from parser_2gis.writer import WriterFactoryImpl
        >>> factory: WriterFactory = WriterFactoryImpl(output_dir=Path("./output"))  # type: check
        >>> writer = factory.get_writer("csv", filename="results.csv")
        >>> writer.write(records)
        >>> writer.close()
    """

    def get_writer(self, format: str, **kwargs: Any) -> Any:
        """Создаёт писатель указанного формата.

        Args:
            format: Формат писателя ("csv", "xlsx", "json").
            **kwargs: Дополнительные аргументы для писателя.

        Returns:
            Экземпляр писателя.
        """
        pass


@runtime_checkable
class ModelProvider(Protocol):
    """Абстракция провайдера языковой модели для AI-функций.

    Определяет интерфейс для взаимодействия с различными LLM провайдерами
    (Ollama, OpenAI, и т.д.). Позволяет легко переключаться между
    различными реализациями без изменения кода.

    Example:
        >>> from parser_2gis.services.ollama_client import OllamaClient
        >>> provider: ModelProvider = OllamaClient()  # type: check
        >>> response = provider.generate("Привет!")
    """

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """Генерирует ответ на запрос.

        Args:
            prompt: Входной запрос.
            **kwargs: Дополнительные параметры генерации.

        Returns:
            Сгенерированный ответ.
        """
        pass

    def is_available(self) -> bool:
        """Проверяет доступность провайдера.

        Returns:
            True если провайдер доступен.
        """
        pass


__all__ = [
    # Callback Protocol
    "LoggerProtocol",
    "ProgressCallback",
    "LogCallback",
    "CleanupCallback",
    "CancelCallback",
    # Data Protocol
    "Writer",
    "Parser",
    "BrowserService",
    # Backend Protocol
    "CacheBackend",
    "ExecutionBackend",
    # Factory Protocol
    "ParserFactory",
    "WriterFactory",
    # AI Protocol
    "ModelProvider",
]
