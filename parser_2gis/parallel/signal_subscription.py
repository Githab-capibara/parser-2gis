"""Система подписки на сигналы для координаторов параллельного парсинга.

ISSUE 116: Заменяет ad-hoc lambda closures на SignalSubscriptionSystem
с чётким API для управления подписками на системные сигналы.

Пример использования:
    >>> system = SignalSubscriptionSystem()
    >>> system.subscribe("SIGINT", coordinator.stop)
    >>> system.subscribe("SIGTERM", coordinator.cleanup)
    >>> system.install_handlers()
"""

from __future__ import annotations

import signal
import types
from collections.abc import Callable
from typing import Any

from parser_2gis.logger import logger


class SignalSubscriptionSystem:
    """Система подписки на системные сигналы.

    ISSUE 116: Заменяет модульные lambda closures на класс с чётким API
    для управления подписками на сигналы (SIGINT, SIGTERM и т.д.).

    Example:
        >>> system = SignalSubscriptionSystem()
        >>> system.subscribe(signal.SIGINT, coordinator.stop, "Остановка парсинга")
        >>> system.install_handlers()
        >>> # ... работа ...
        >>> system.uninstall_handlers()

    """

    # Сигналы, обрабатываемые по умолчанию
    DEFAULT_SIGNALS: tuple[int, ...] = (signal.SIGINT, signal.SIGTERM)

    def __init__(self) -> None:
        """Инициализирует систему подписки на сигналы."""
        self._subscriptions: dict[int, list[tuple[Callable[[], Any], str]]] = {}
        self._original_handlers: dict[int, Any] = {}
        self._installed: bool = False

    def subscribe(
        self, signal_num: int, callback: Callable[[], Any], description: str = ""
    ) -> SignalSubscriptionSystem:
        """Добавляет подписку на сигнал.

        Args:
            signal_num: Номер сигнала (например, signal.SIGINT).
            callback: Функция-обработчик без аргументов.
            description: Описание действия для логирования.

        Returns:
            Этот же экземпляр для цепочки вызовов.

        """
        if signal_num not in self._subscriptions:
            self._subscriptions[signal_num] = []
        self._subscriptions[signal_num].append((callback, description))
        return self

    def unsubscribe(self, signal_num: int, callback: Callable[[], Any]) -> SignalSubscriptionSystem:
        """Удаляет подписку на сигнал.

        Args:
            signal_num: Номер сигнала.
            callback: Функция-обработчик для удаления.

        Returns:
            Этот же экземпляр для цепочки вызовов.

        """
        if signal_num in self._subscriptions:
            self._subscriptions[signal_num] = [
                (cb, desc) for cb, desc in self._subscriptions[signal_num] if cb is not callback
            ]
        return self

    def install_handlers(self) -> None:
        """Устанавливает обработчики для всех подписанных сигналов.

        Сохраняет оригинальные обработчики для последующего восстановления.

        """
        if self._installed:
            logger.debug("Обработчики сигналов уже установлены")
            return

        signals_to_handle = set(self._subscriptions.keys()) or set(self.DEFAULT_SIGNALS)

        for sig_num in signals_to_handle:
            try:
                # Сохраняем оригинальный обработчик
                self._original_handlers[sig_num] = signal.getsignal(sig_num)
                signal.signal(sig_num, self._create_handler(sig_num))
                self._installed = True
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning("Не удалось установить обработчик сигнала %d: %s", sig_num, e)

    def uninstall_handlers(self) -> None:
        """Восстанавливает оригинальные обработчики сигналов."""
        if not self._installed:
            return

        for sig_num, original_handler in self._original_handlers.items():
            try:
                signal.signal(sig_num, original_handler)
            except (OSError, RuntimeError, ValueError) as e:
                logger.warning("Не удалось восстановить обработчик сигнала %d: %s", sig_num, e)

        self._original_handlers.clear()
        self._installed = False

    def clear(self) -> None:
        """Очищает все подписки."""
        self._subscriptions.clear()
        self.uninstall_handlers()

    @property
    def is_installed(self) -> bool:
        """Возвращает True если обработчики установлены."""
        return self._installed

    def get_subscription_count(self, signal_num: int) -> int:
        """Возвращает количество подписок на сигнал.

        Args:
            signal_num: Номер сигнала.

        Returns:
            Количество подписок.

        """
        return len(self._subscriptions.get(signal_num, []))

    def _create_handler(self, _signal_num: int) -> Callable[[int, types.FrameType | None], None]:
        """Создаёт обработчик сигнала для заданного номера.

        Args:
            _signal_num: Номер сигнала.

        Returns:
            Функция-обработчик сигнала.

        """

        def handler(signum: int, _frame: types.FrameType | None) -> None:
            signal_name = signal.Signals(signum).name if hasattr(signal, "Signals") else str(signum)
            logger.info("Получен сигнал %s, выполняются обработчики...", signal_name)

            for callback, description in self._subscriptions.get(signum, []):
                try:
                    if description:
                        logger.info("Выполняется: %s", description)
                    callback()
                except (OSError, RuntimeError, TypeError, ValueError) as e:
                    logger.error(
                        "Ошибка в обработчике сигнала %s (%s): %s",
                        signal_name,
                        description or "без описания",
                        e,
                    )

        return handler

    def __enter__(self) -> SignalSubscriptionSystem:
        """Контекстный менеджер: установка обработчиков."""
        self.install_handlers()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Контекстный менеджер: восстановление обработчиков."""
        self.uninstall_handlers()


__all__ = ["SignalSubscriptionSystem"]
