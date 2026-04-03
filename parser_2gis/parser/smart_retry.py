"""Модуль для интеллектуального механизма повторных попыток.

Этот модуль предоставляет логику для принятия решений о том,
нужно ли выполнять повторную попытку или лучше завершить парсинг.
"""

from __future__ import annotations

from typing import Any

from parser_2gis.logger import logger


class SmartRetryManager:
    """Менеджер интеллектуальных повторных попыток.

    Анализирует ситуацию и принимает решение о необходимости
    повторных попыток на основе контекста (количество записей,
    тип ошибки, история попыток).
    """

    def __init__(self, max_retries: int = 3, max_delay: float = 30.0) -> None:
        """Инициализирует менеджер повторных попыток.

        Args:
            max_retries: Максимальное количество повторных попыток.
            max_delay: Максимальная задержка между попытками в секундах (H020).

        """
        self._max_retries = max_retries
        self._max_delay = max_delay  # H020: Ограничение максимальной задержки
        self._retry_count = 0
        self._total_records_collected = 0
        self._records_on_last_page = 0
        self._last_error: str | None = None

        logger.debug(
            "Инициализирован SmartRetryManager с max_retries=%d, max_delay=%.1fсек",
            max_retries,
            max_delay,
        )

    def should_retry(self, error: str, records_on_page: int = 0) -> bool:
        """Определяет, нужно ли выполнять повторную попытку.

        Args:
            error: Описание ошибки.
            records_on_page: Количество записей на последней странице.

        Returns:
            True если нужна повторная попытка, False если лучше завершить.

        Примечание:
            Счётчик попыток увеличивается только после принятия решения
            о необходимости повторной попытки для корректного подсчёта.

        """
        self._last_error = error
        self._records_on_last_page = records_on_page

        # Проверяем, не превышен ли лимит попыток
        if self._retry_count >= self._max_retries:
            logger.warning("Превышен лимит повторных попыток (%d)", self._max_retries)
            return False

        # Анализируем тип ошибки
        error_lower = error.lower()

        # Сетевые ошибки (502, 503, 504, Timeout) - всегда retry
        if any(code in error_lower for code in ["502", "503", "504", "timeout"]):
            logger.info("Сетевая ошибка: %s. Требуется повторная попытка", error)
            return True

        # 404 ошибки - зависит от контекста
        if "404" in error_lower:
            # Если были записи до 404 - возможно временная проблема, retry
            if self._total_records_collected > 0:
                logger.info(
                    "404 после %d записей. Требуется повторная попытка",
                    self._total_records_collected,
                )
                return True
            # Если не было записей - конец категории, не нужно retry
            else:
                logger.info("404 без записей. Завершаем парсинг.")
                return False

        # 403 ошибки (блокировка) - не retry, но логируем
        if "403" in error_lower:
            logger.warning("Ошибка 403 (блокировка). Повторные попытки не помогут.")
            return False

        # 500 ошибки (ошибка сервера) - retry
        if "500" in error_lower:
            logger.info("Ошибка сервера 500. Требуется повторная попытка")
            return True

        # По умолчанию - retry для других ошибок (с логированием)
        logger.debug("Неклассифицированная ошибка: %s. Требуется повторная попытка", error)
        return True

    def record_retry(self) -> None:
        """Записывает фактическую повторную попытку.

        Вызывается только после принятия решения о необходимости
        повторной попытки для корректного подсчёта.
        """
        self._retry_count += 1
        logger.debug("Записана повторная попытка %d/%d", self._retry_count, self._max_retries)

    def add_records(self, count: int) -> None:
        """Добавляет количество собранных записей.

        Args:
            count: Количество новых записей.

        """
        self._total_records_collected += count
        logger.debug("Добавлено %d записей (всего: %d)", count, self._total_records_collected)

    def get_retry_count(self) -> int:
        """Возвращает текущее количество попыток.

        Returns:
            Количество попыток.

        """
        return self._retry_count

    def get_retry_delay(self, base_delay: float = 1.0) -> float:
        """Вычисляет задержку перед следующей попыткой с ограничением.

        H020: Ограничивает максимальную задержку для предотвращения чрезмерного ожидания.

        Args:
            base_delay: Базовая задержка в секундах.

        Returns:
            Задержка в секундах (не более max_delay).

        """
        import random

        # Экспоненциальная задержка: base_delay * (1.5 ** retry_count)
        exponential_delay = base_delay * (1.5**self._retry_count)
        # H020: Ограничиваем максимальной задержкой
        capped_delay = min(exponential_delay, self._max_delay)
        # Добавляем jitter для предотвращения thundering herd
        jitter = random.uniform(0, 0.3)
        return capped_delay + jitter

    def get_total_records(self) -> int:
        """Возвращает общее количество собранных записей.

        Returns:
            Общее количество записей.

        """
        return self._total_records_collected

    def get_stats(self) -> dict[str, Any]:
        """Возвращает статистику повторных попыток.

        Returns:
            Словарь со статистикой.

        """
        return {
            "retry_count": self._retry_count,
            "max_retries": self._max_retries,
            "total_records": self._total_records_collected,
            "records_on_last_page": self._records_on_last_page,
            "last_error": self._last_error,
        }

    def reset(self) -> None:
        """Сбрасывает состояние менеджера для нового URL."""
        self._retry_count = 0
        self._total_records_collected = 0
        self._records_on_last_page = 0
        self._last_error = None
        logger.debug("SmartRetryManager сброшен")
