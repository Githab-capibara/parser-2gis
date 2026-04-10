"""Общий обработчик сигналов для координаторов параллельного парсинга.

Вынесен из coordinator.py и thread_coordinator.py для устранения дублирования (#62).
"""

from __future__ import annotations

import types
from typing import Any

from parser_2gis.logger import logger


def create_signal_handler(context_getter: Any) -> Any:
    """Создаёт обработчик сигналов SIGINT для координатора.

    Args:
        context_getter: Функция, возвращающая объект с методом get_coordinator().

    Returns:
        Функция обработчика сигнала (signum, frame) -> None.

    """

    def _signal_handler(_signum: int, _frame: types.FrameType | None) -> None:
        """Глобальный обработчик сигналов SIGINT (Ctrl+C).

        Args:
            _signum: Номер сигнала.
            _frame: Текущий фрейм.

        """
        coordinator = context_getter().get_coordinator()
        if coordinator is not None:
            logger.warning("Получен сигнал прерывания (SIGINT), остановка парсинга...")
            coordinator.stop()

    return _signal_handler
