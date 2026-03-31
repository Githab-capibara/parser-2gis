"""
Модуль обработки сигналов для парсера.

Предоставляет класс SignalHandler для обработки сигналов:
- Обработка SIGINT (Ctrl+C)
- Обработка SIGTERM
- Graceful shutdown
"""

from __future__ import annotations

import logging
import signal
import threading
from typing import Callable, Optional

logger = logging.getLogger("parser_2gis.utils.signal_handler")


class SignalHandler:
    """Обработчик сигналов для graceful shutdown.

    Обрабатывает сигналы прерывания (SIGINT, SIGTERM) и обеспечивает
    корректное завершение работы парсера.

    Attributes:
        cleanup_callback: Функция обратного вызова для очистки ресурсов.
        cancel_event: Событие для сигнализации об отмене операции.
    """

    def __init__(
        self,
        cleanup_callback: Optional[Callable[[], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> None:
        """Инициализация обработчика сигналов.

        Args:
            cleanup_callback: Функция для очистки ресурсов при завершении.
            cancel_event: Событие для сигнализации об отмене.
        """
        self._cleanup_callback = cleanup_callback
        self._cancel_event = cancel_event or threading.Event()
        self._old_sigint_handler: Optional[Callable] = None
        self._old_sigterm_handler: Optional[Callable] = None
        self._registered = False

    def register(self) -> None:
        """Регистрирует обработчики сигналов."""
        if self._registered:
            return

        def handler(signum: int, frame) -> None:
            """Обработчик сигналов прерывания."""
            logger.warning("Получен сигнал %d, инициализация завершения...", signum)
            self._cancel_event.set()
            if self._cleanup_callback:
                self._cleanup_callback()

        self._old_sigint_handler = signal.signal(signal.SIGINT, handler)
        self._old_sigterm_handler = signal.signal(signal.SIGTERM, handler)
        self._registered = True
        logger.debug("Обработчики сигналов зарегистрированы")

    def unregister(self) -> None:
        """Восстанавливает оригинальные обработчики сигналов."""
        if not self._registered:
            return

        if self._old_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._old_sigint_handler)
        if self._old_sigterm_handler is not None:
            signal.signal(signal.SIGTERM, self._old_sigterm_handler)

        self._registered = False
        logger.debug("Обработчики сигналов восстановлены")

    def is_cancelled(self) -> bool:
        """Проверяет флаг отмены.

        Returns:
            True если операция отменена.
        """
        return self._cancel_event.is_set()

    def cancel(self) -> None:
        """Устанавливает флаг отмены."""
        self._cancel_event.set()
        logger.debug("Флаг отмены установлен")
