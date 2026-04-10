"""Модуль логирования.

Предоставляет функции для настройки логгера:
- setup_logger - базовая настройка
- setup_cli_logger - настройка для CLI
- setup_gui_logger - настройка для GUI с очередью
- QueueHandler - обработчик очереди логирования
"""

from __future__ import annotations

import logging
import os
import threading
import warnings
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    import queue

    from .options import LogOptions


class _ThirdPartyLoggingState:
    """H018: Класс для управления состоянием логирования сторонних библиотек.

    ISSUE-054: Обёрнуто глобальное состояние в класс вместо модульной переменной.
    """

    _urllib3_level_set: bool = False

    @classmethod
    def is_urllib3_level_set(cls) -> bool:
        """Проверяет установлен ли уровень для urllib3."""
        return cls._urllib3_level_set

    @classmethod
    def set_urllib3_level_set(cls) -> None:
        """Устанавливает флаг urllib3 уровня."""
        cls._urllib3_level_set = True


def _setup_third_party_logging_once() -> None:
    """H018: Устанавливает уровень логирования для сторонних библиотек один раз."""
    if not _ThirdPartyLoggingState.is_urllib3_level_set():
        logging.getLogger("urllib3").setLevel(logging.ERROR)
        logging.getLogger("pychrome").setLevel(logging.ERROR)
        warnings.filterwarnings(action="ignore", module="pychrome")
        _ThirdPartyLoggingState.set_urllib3_level_set()


# H018: Убрано выполнение _setup_third_party_logging_once() при импорте модуля.
# Теперь вызывается лениво при первом использовании логгера (см. _get_logger()).

_LOGGER_NAME = "parser-2gis"


class _LazyLogger:
    """Прокси-обёртка для ленивой инициализации логгера с настройкой сторонних библиотек.

    ISSUE-028: Вызывает _setup_third_party_logging_once() только при первом
    реальном обращении к логгеру, а не при импорте модуля.
    """

    _initialized: bool = False
    _logger: logging.Logger | None = None

    @classmethod
    def _ensure_initialized(cls) -> logging.Logger:
        """Гарантирует ленивую инициализацию логгера."""
        if cls._logger is None:
            cls._logger = logging.getLogger(_LOGGER_NAME)
        if not cls._initialized:
            _setup_third_party_logging_once()
            cls._initialized = True
        return cls._logger

    def __getattr__(self, name: str) -> Any:
        """Делегирует все атрибуты внутреннему логгеру.

        Args:
            name: Имя атрибута для делегирования.

        Returns:
            Атрибут внутреннего логгера.

        """
        return getattr(self._ensure_initialized(), name)


# Глобальный экземпляр ленивого логгера
logger = _LazyLogger()
Logger = logging.Logger


class LoggerProvider:
    """Провайдер для создания и получения именованных логгеров.

    ISSUE 062: Заменяет модульный singleton logger на класс LoggerProvider,
    который создаёт/получает логгеры с чётким API.
    """

    _loggers: ClassVar[dict[str, logging.Logger]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def get_logger(cls, name: str = _LOGGER_NAME) -> logging.Logger:
        """Получает или создаёт именованный логгер.

        Args:
            name: Имя логгера. По умолчанию используется имя приложения.

        Returns:
            Настроенный экземпляр logging.Logger.

        """
        with cls._lock:
            if name not in cls._loggers:
                log_instance = logging.getLogger(name)
                if not log_instance.handlers:
                    handler = logging.StreamHandler()
                    formatter = _create_formatter(
                        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S",
                    )
                    handler.setFormatter(formatter)
                    log_instance.addHandler(handler)
                    log_instance.setLevel(logging.INFO)
                cls._loggers[name] = log_instance
            return cls._loggers[name]

    @classmethod
    def configure_logger(
        cls,
        name: str = _LOGGER_NAME,
        level: str | int = logging.INFO,
        fmt: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
    ) -> logging.Logger:
        """Настраивает логгер с заданными параметрами.

        Args:
            name: Имя логгера.
            level: Уровень логирования.
            fmt: Строка формата логов.
            datefmt: Строка формата даты.

        Returns:
            Настроенный экземпляр logging.Logger.

        """
        with cls._lock:
            log_instance = logging.getLogger(name)
            if not log_instance.handlers:
                handler = logging.StreamHandler()
                formatter = _create_formatter(fmt, datefmt)
                handler.setFormatter(formatter)
                log_instance.addHandler(handler)
                log_instance.setLevel(level)
            cls._loggers[name] = log_instance
            return log_instance

    @classmethod
    def clear(cls) -> None:
        """Очищает кэш логгеров (полезно для тестирования)."""
        with cls._lock:
            cls._loggers.clear()


def _create_formatter(fmt: str, datefmt: str) -> logging.Formatter:
    """Создаёт объект Formatter с заданными параметрами.

    Вынесено для устранения дублирования кода создания formatter.

    Args:
        fmt: Строка формата логов.
        datefmt: Строка формата даты.

    Returns:
        Настроенный экземпляр logging.Formatter.

    """
    return logging.Formatter(fmt, datefmt)


def _setup_base_logger(
    level: str | int = logging.INFO,
    fmt: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
    logger_instance: logging.Logger | None = None,
) -> logging.Logger:
    """Базовая настройка логгера с устранением дублирования.

    ISSUE-015: Централизованная функция для настройки логгера.

    Args:
        level: Уровень логирования (строка или int).
        fmt: Строка формата логов.
        datefmt: Строка формата даты.
        logger_instance: Опциональный экземпляр логгера.
                        По умолчанию используется logger из этого модуля.

    Returns:
        Настроенный экземпляр logging.Logger.

    """
    target_logger = (
        logger_instance if logger_instance is not None else logging.getLogger(_LOGGER_NAME)
    )

    if not target_logger.handlers:
        handler = logging.StreamHandler()
        formatter = _create_formatter(fmt, datefmt)
        handler.setFormatter(formatter)

        target_logger.addHandler(handler)
        target_logger.setLevel(level)

    return target_logger


class QueueHandler(logging.Handler):
    """Обработчик логирования через очередь.

    Перенаправляет записи логов в очередь для безопасной передачи
    между потоками. Используется в GUI для отображения логов
    в пользовательском интерфейсе.

    Args:
        log_queue: Очередь для передачи записей логов.

    Example:
        >>> import queue
        >>> q: queue.Queue[tuple[str, str]] = queue.Queue()
        >>> handler = QueueHandler(q)
        >>> handler.emit(logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None))

    """

    def __init__(self, log_queue: queue.Queue[tuple[str, str]]) -> None:
        """Инициализирует обработчик очереди логирования.

        Args:
            log_queue: Очередь для передачи записей логов.

        """
        super().__init__()
        self._log_queue: queue.Queue[tuple[str, str]] = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        """Отправляет запись лога в очередь.

        Args:
            record: Запись лога для обработки.

        """
        log_message = (record.levelname, self.format(record) + os.linesep)
        self._log_queue.put(log_message)


def setup_gui_logger(log_queue: queue.Queue[tuple[str, str]], options: LogOptions) -> None:
    """Добавляет обработчик очереди к существующему логгеру.

    Отправляет логи в указанную очередь для GUI-отображения.

    Args:
        log_queue: Очередь для размещения сообщений логирования.
        options: Опции логирования.

    """
    # ISSUE-015: Используем _setup_base_logger для базовой настройки
    _setup_base_logger(level=options.level, fmt=options.cli_format, datefmt=options.cli_datefmt)

    formatter = logging.Formatter(options.gui_format, options.gui_datefmt)
    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(formatter)
    logger.addHandler(queue_handler)


def setup_cli_logger(options: LogOptions) -> None:
    """Настраивает CLI логгер из конфигурации.

    Args:
        options: Опции логирования.

    """
    # ISSUE-015: Используем _setup_base_logger для устранения дублирования
    _setup_base_logger(level=options.level, fmt=options.cli_format, datefmt=options.cli_datefmt)


def setup_logger(level: str, fmt: str, datefmt: str) -> None:
    """Настраивает логгер.

    Args:
        level: Уровень логгера.
        fmt: Строка формата в процентном стиле.
        datefmt: Строка формата даты.

    """
    # ISSUE-015: Используем _setup_base_logger для устранения дублирования
    _setup_base_logger(level=level, fmt=fmt, datefmt=datefmt)


def log_parser_start(
    version: str, urls_count: int, output_path: str, output_format: str, config_summary: dict | None = None,
) -> None:
    """Логирует запуск парсера с подробной информацией.

    ISSUE 106: Делегирует LoggerPresentationBridge вместо прямого вызова visual_logger.

    Args:
        version: Версия парсера.
        urls_count: Количество URL для парсинга.
        output_path: Путь к выходному файлу.
        output_format: Формат выходного файла.
        config_summary: Краткая сводка конфигурации.

    """
    from .presentation_bridge import logger_presentation_bridge

    # ISSUE 106: Делегируем мосту вместо прямого вызова visual_logger
    logger_presentation_bridge.log_parser_start(
        version=version,
        urls_count=urls_count,
        output_path=output_path,
        output_format=output_format,
        config_summary=config_summary,
    )


def log_parser_finish(
    *, success: bool = True, stats: dict | None = None, duration: str | None = None,
) -> None:
    """Логирует завершение парсера.

    ISSUE 106: Делегирует LoggerPresentationBridge вместо прямого вызова visual_logger.

    Args:
        success: Успешно ли завершено.
        stats: Статистика работы.
        duration: Продолжительность работы.

    """
    from .presentation_bridge import logger_presentation_bridge

    # ISSUE 106: Делегируем мосту вместо прямого вызова visual_logger
    logger_presentation_bridge.log_parser_finish(success=success, stats=stats, duration=duration)
