"""
Модуль для обработки сигналов операционной системы.

Предоставляет класс SignalHandler для безопасной обработки сигналов
SIGINT (Ctrl+C) и SIGTERM с гарантированной очисткой ресурсов.
- Устранено глобальное состояние (_interrupted и _is_cleaning_up)
- Создан класс SignalHandler с инкапсулированным состоянием
- Thread-safe реализация с использованием Lock

Пример использования:
    >>> from .signal_handler import SignalHandler
    >>> handler = SignalHandler(cleanup_callback=my_cleanup_function)
    >>> handler.setup()  # Установить обработчики сигналов
    >>> # ... работа приложения ...
    >>> handler.cleanup()  # Очистка ресурсов
"""

from __future__ import annotations

import signal
import sys
import threading
from typing import Any, Callable, Optional

from .logger import logger


class SignalHandler:
    """
    Обработчик сигналов для безопасной очистки ресурсов приложения.

    Этот класс предоставляет централизованную обработку сигналов SIGINT (Ctrl+C)
    и SIGTERM с гарантированной очисткой ресурсов. Использует флаг для
    предотвращения рекурсивных вызовов обработчика.
    - Инкапсулированное состояние вместо глобальных переменных
    - Thread-safe реализация с использованием threading.Lock
    - Поддержка callback функции для очистки ресурсов

    Attributes:
        _interrupted: Флаг прерывания работы приложения.
        _is_cleaning_up: Флаг текущей очистки для предотвращения рекурсии.
        _cleanup_callback: Callback функция для очистки ресурсов.
        _lock: Блокировка для потокобезопасности.
        _original_handlers: Сохранённые оригинальные обработчики сигналов.

    Пример использования:
        >>> def my_cleanup():
        ...     print("Очистка ресурсов...")
        >>> handler = SignalHandler(cleanup_callback=my_cleanup)
        >>> handler.setup()
        >>> # Работа приложения
        >>> if handler.is_interrupted():
        ...     handler.cleanup()
    """

    def __init__(self, cleanup_callback: Optional[Callable[[], None]] = None) -> None:
        """
        Инициализация обработчика сигналов.

        Args:
            cleanup_callback: Функция обратного вызова для очистки ресурсов.
                              Вызывается при получении сигнала прерывания.
        """
        self._interrupted = False
        self._is_cleaning_up = False
        self._cleanup_completed = False  # Флаг завершения очистки
        self._cleanup_callback = cleanup_callback
        self._lock = threading.Lock()
        self._original_handlers: dict[int, Any] = {}
        # Для совместимости с тестами
        self._original_handler_sigint: Any = None
        self._original_handler_sigterm: Any = None

    def setup(self) -> None:
        """
        Устанавливает обработчики сигналов SIGINT и SIGTERM.

        Примечание:
            - SIGINT (Ctrl+C) - прерывание пользователем
            - SIGTERM - сигнал завершения от системы
            - Обработчики устанавливаются только для основного потока

        Важно:
            Вызывайте этот метод только в основном потоке приложения.
        """
        with self._lock:
            # Сохраняем оригинальные обработчики
            self._original_handlers[signal.SIGINT] = signal.getsignal(signal.SIGINT)
            self._original_handlers[signal.SIGTERM] = signal.getsignal(signal.SIGTERM)
            # Для совместимости с тестами
            self._original_handler_sigint = self._original_handlers[signal.SIGINT]
            self._original_handler_sigterm = self._original_handlers[signal.SIGTERM]

            # Устанавливаем наши обработчики
            signal.signal(signal.SIGINT, self._handle_signal)
            signal.signal(signal.SIGTERM, self._handle_signal)

            logger.debug("Обработчики сигналов SIGINT и SIGTERM установлены")

    def cleanup(self) -> None:
        """
        Выполняет очистку ресурсов и восстанавливает обработчики сигналов.

        Метод вызывает callback функцию очистки (если указана) и
        восстанавливает оригинальные обработчики сигналов.
        """
        with self._lock:
            # Предотвращаем повторную очистку
            if self._is_cleaning_up or self._cleanup_completed:
                logger.warning("Очистка уже выполняется или завершена")
                return

            self._is_cleaning_up = True

            try:
                # Вызываем callback очистки
                if self._cleanup_callback:
                    try:
                        self._cleanup_callback()
                    except Exception as cleanup_error:
                        logger.error("Ошибка при очистке ресурсов: %s", cleanup_error)

                # Восстанавливаем оригинальные обработчики
                for sig_num, handler in self._original_handlers.items():
                    try:
                        signal.signal(sig_num, handler)
                    except Exception as restore_error:
                        logger.error(
                            "Ошибка при восстановлении обработчика сигнала %d: %s",
                            sig_num,
                            restore_error,
                        )

                logger.info("Очистка ресурсов завершена")

            finally:
                self._is_cleaning_up = False
                self._cleanup_completed = True

    def _handle_signal(self, signum: int, frame: Any) -> None:
        """
        Внутренний обработчик сигналов.

        Args:
            signum: Номер полученного сигнала.
            frame: Текущий фрейм выполнения.

        Примечание:
            Метод использует флаг _is_cleaning_up для предотвращения
            рекурсивных вызовов во время очистки ресурсов.
        """
        with self._lock:
            # Проверяем флаг перед обработкой сигнала
            if self._is_cleaning_up:
                logger.warning(
                    "Получен повторный сигнал %d во время очистки ресурсов. Игнорируется.",
                    signum,
                )
                return

            self._interrupted = True
            self._is_cleaning_up = True

            logger.warning(
                "Получен сигнал %d. Начинается безопасная очистка ресурсов...", signum
            )

            # Игнорируем повторные сигналы во время cleanup
            original_sigint = signal.getsignal(signal.SIGINT)
            original_sigterm = signal.getsignal(signal.SIGTERM)

            try:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                signal.signal(signal.SIGTERM, signal.SIG_IGN)

                # Немедленная очистка ресурсов
                if self._cleanup_callback:
                    try:
                        self._cleanup_callback()
                    except Exception as cleanup_error:
                        logger.error(
                            "Ошибка при очистке ресурсов в signal handler: %s",
                            cleanup_error,
                        )

                logger.info("Очистка ресурсов завершена. Выход из приложения...")
                sys.exit(128 + signum)

            finally:
                # Восстанавливаем оригинальные обработчики
                try:
                    signal.signal(signal.SIGINT, original_sigint)
                    signal.signal(signal.SIGTERM, original_sigterm)
                except Exception as restore_error:
                    logger.error(
                        "Ошибка при восстановлении обработчиков сигналов: %s",
                        restore_error,
                    )
                # Сбрасываем флаг только если очистка завершена
                self._is_cleaning_up = False

    def is_interrupted(self) -> bool:
        """
        Проверяет, был ли получен сигнал прерывания.

        Returns:
            True если был получен сигнал прерывания, False иначе.

        Пример:
            >>> handler = SignalHandler()
            >>> handler.setup()
            >>> if handler.is_interrupted():
            ...     print("Приложение было прервано")
        """
        with self._lock:
            return self._interrupted

    def reset(self) -> None:
        """
        Сбрасывает флаг прерывания.

        Позволяет продолжить работу приложения после обработки сигнала.
        """
        with self._lock:
            self._interrupted = False
            logger.debug("Флаг прерывания сброшен")

    def __enter__(self) -> "SignalHandler":
        """Контекстный менеджер: устанавливает обработчики сигналов."""
        self.setup()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Контекстный менеджер: выполняет очистку ресурсов."""
        self.cleanup()
