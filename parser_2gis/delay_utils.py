"""Общие утилиты для управления задержками при запуске.

Вынесены из coordinator.py, strategies.py, url_parser.py (#65-#67).
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable


def apply_startup_delay(
    config: object, phase: str = "initial", log_func: Callable[[str, str], None] | None = None,
) -> float:
    """Применяет задержку перед запуском парсинга.

    Читает параметры задержки из конфигурации, выполняет ``random.uniform``
    и ``time.sleep``.

    Args:
        config: Объект конфигурации с атрибутом ``parallel``.
        phase: Фаза задержки — ``"initial"`` или ``"launch"``.
        log_func: Функция логирования ``(message, level) -> None``.

    Returns:
        Фактическая величина задержки в секундах.

    """
    parallel_cfg = getattr(config, "parallel", None)

    # Проверяем глобальный флаг use_delays
    if parallel_cfg is not None and not getattr(parallel_cfg, "use_delays", True):
        return 0.0

    if phase == "launch":
        min_val = getattr(parallel_cfg, "launch_delay_min", 0.0) if parallel_cfg else 0.0
        max_val = getattr(parallel_cfg, "launch_delay_max", 0.05) if parallel_cfg else 0.05
    else:
        min_val = getattr(parallel_cfg, "initial_delay_min", 0.0) if parallel_cfg else 0.0
        max_val = getattr(parallel_cfg, "initial_delay_max", 0.1) if parallel_cfg else 0.1

    delay = random.uniform(max(0.1, min_val), max_val) if max_val > 0 else 0.0
    if delay > 0:
        time.sleep(delay)

    if log_func is not None and delay > 0 and phase == "launch":
        log_func(f"Задержка перед запуском Chrome: {delay:.2f} сек", "debug")
    elif log_func is not None and delay > 0:
        log_func(f"Начальная задержка: {delay:.2f} сек", "debug")

    return delay
