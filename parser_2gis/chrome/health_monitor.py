"""Модуль для мониторинга здоровья браузера.

Этот модуль предоставляет логику для проверки состояния браузера,
автоматического перезапуска при критических ошибках и
контроля использования ресурсов.

DEPRECATED: Класс BrowserHealthMonitor не используется в проекте и будет удалён
в будущей версии. Не рекомендуется использовать этот класс в новом коде.
"""

from __future__ import annotations


import threading
import time
from typing import TYPE_CHECKING, TypedDict

import psutil

from parser_2gis.logger import logger

if TYPE_CHECKING:
    from .browser import ChromeBrowser


class HealthStatusDict(TypedDict, total=False):
    """Словарь состояния здоровья браузера."""

    healthy: bool
    memory_mb: float
    cpu_percent: float
    time_since_activity: float
    critical_errors: int
    recommendation: str | None


class BrowserHealthMonitor:
    """Монитор здоровья браузера.

    Отслеживает состояние браузера, использование памяти и CPU,
    автоматически перезапускает браузер при критических ошибках.

    DEPRECATED: Этот класс не используется в проекте и будет удалён.
    """

    # Пороги для автоматического перезапуска
    # Память: 2 ГБ — порог превышения использования RAM
    MEMORY_THRESHOLD_MB = 2048
    # CPU: 95% — порег перегрузки процессора
    CPU_THRESHOLD_PERCENT = 95
    # Stall: 120 секунд (2 минуты) — порог зависания браузера
    STALL_THRESHOLD_SEC = 120
    # Максимальное количество критических ошибок до рекомендации перезапуска
    MAX_CRITICAL_ERRORS_BEFORE_RESTART = 3

    def __init__(self, browser: ChromeBrowser, enable_auto_restart: bool = True) -> None:
        """Инициализирует монитор.

        Args:
            browser: Экземпляр браузера ChromeBrowser.
            enable_auto_restart: Включить автоматический перезапуск.

        """
        self._browser = browser
        self._enable_auto_restart = enable_auto_restart
        self._last_activity_time = time.time()
        self._critical_errors_count = 0
        # ИСПОЛЬЗУЕМ RLock (Reentrant Lock) для предотвращения deadlock
        # RLock позволяет одному и тому же потоку захватывать
        # блокировку несколько раз. Это важно для методов, которые
        # могут вызываться рекурсивно или из других методов с блокировкой
        self._lock = threading.RLock()
        self._monitoring_active = False

        logger.info(
            "Инициализирован BrowserHealthMonitor с RLock (auto_restart=%s)", enable_auto_restart
        )

    def record_activity(self) -> None:
        """Записывает активность браузера."""
        with self._lock:
            self._last_activity_time = time.time()

    def check_health(self) -> HealthStatusDict:
        """Проверяет здоровье браузера.

        Returns:
            Словарь с состоянием здоровья.

        """
        health_status: HealthStatusDict = {
            "healthy": True,
            "memory_mb": 0.0,
            "cpu_percent": 0.0,
            "time_since_activity": 0.0,
            "critical_errors": self._critical_errors_count,
            "recommendation": None,
        }

        try:
            # Проверяем процесс браузера
            if hasattr(self._browser, "_proc") and self._browser._proc:
                proc = self._browser._proc

                try:
                    # Получаем информацию о процессе
                    p = psutil.Process(proc.pid)

                    # Проверяем память
                    memory_info = p.memory_info()
                    memory_mb = memory_info.rss / 1024 / 1024
                    health_status["memory_mb"] = memory_mb

                    # Проверяем CPU
                    cpu_percent = p.cpu_percent(interval=None)
                    health_status["cpu_percent"] = cpu_percent

                    # Проверяем время активности
                    time_since_activity = time.time() - self._last_activity_time
                    health_status["time_since_activity"] = time_since_activity

                    # Анализируем проблемы
                    issues = []

                    if memory_mb > self.MEMORY_THRESHOLD_MB:
                        issues.append(
                            f"Память превышена: {memory_mb:.1f} МБ > {self.MEMORY_THRESHOLD_MB} МБ"
                        )
                        health_status["healthy"] = False

                    if cpu_percent > self.CPU_THRESHOLD_PERCENT:
                        issues.append(
                            f"CPU перегружен: {cpu_percent:.1f}% > {self.CPU_THRESHOLD_PERCENT}%"
                        )
                        health_status["healthy"] = False

                    if time_since_activity > self.STALL_THRESHOLD_SEC:
                        issues.append(
                            f"Браузер завис: {time_since_activity:.1f} сек > {self.STALL_THRESHOLD_SEC} сек"
                        )
                        health_status["healthy"] = False

                    # Формируем рекомендацию
                    if issues:
                        health_status["recommendation"] = "; ".join(issues)
                        logger.warning(
                            "Обнаружены проблемы с браузером: %s", health_status["recommendation"]
                        )

                        # Увеличиваем счетчик критических ошибок
                        with self._lock:
                            self._critical_errors_count += 1

                        # Рекомендуем перезапуск
                        if self._enable_auto_restart and health_status["recommendation"]:
                            health_status["recommendation"] += ". Рекомендуется перезапуск."

                except psutil.NoSuchProcess:
                    logger.error("Процесс браузера не найден")
                    health_status["healthy"] = False
                    health_status["recommendation"] = "Процесс браузера завершен"

                except Exception as e:
                    logger.error("Ошибка при проверке здоровья: %s", e)
                    health_status["healthy"] = False
                    health_status["recommendation"] = f"Ошибка проверки: {e}"
            else:
                logger.debug("Браузер не имеет процесса для мониторинга")

        except Exception as e:
            logger.error("Критическая ошибка при проверке здоровья: %s", e)
            health_status["healthy"] = False
            health_status["recommendation"] = f"Критическая ошибка: {e}"

        return health_status

    def should_restart(self) -> bool:
        """Определяет, нужно ли перезапустить браузер.

        Returns:
            True если нужен перезапуск, False если нет.

        """
        if not self._enable_auto_restart:
            return False

        health = self.check_health()

        # Перезапуск если браузер нездоров
        if not health["healthy"]:
            # Атомарно читаем счётчик критических ошибок под блокировкой
            with self._lock:
                errors_count = self._critical_errors_count

            # Перезапуск если много критических ошибок
            if errors_count >= self.MAX_CRITICAL_ERRORS_BEFORE_RESTART:
                logger.warning(
                    "Превышен порог критических ошибок (%d). Рекомендуется перезапуск браузера.",
                    errors_count,
                )
                return True

            # Перезапуск если браузер завис
            if health["time_since_activity"] > self.STALL_THRESHOLD_SEC:
                logger.warning(
                    "Браузер не отвечает %.1f сек. Рекомендуется перезапуск.",
                    health["time_since_activity"],
                )
                return True

        return False

    def restart_browser(self) -> bool:
        """Перезапускает браузер.

        Returns:
            True если перезапуск успешен, False если нет.

        """
        try:
            logger.info("Начало перезапуска браузера...")

            # Закрываем текущий браузер
            self._browser.close()
            logger.debug("Браузер закрыт")

            # Ждем немного
            time.sleep(0.5)

            # Сбрасываем счетчики
            with self._lock:
                self._critical_errors_count = 0
                self._last_activity_time = time.time()

            logger.info("Браузер успешно перезапущен")
            return True

        except Exception as e:
            logger.error("Ошибка при перезапуске браузера: %s", e)
            return False

    def get_critical_errors_count(self) -> int:
        """Возвращает количество критических ошибок.

        Returns:
            Количество критических ошибок.

        """
        with self._lock:
            return self._critical_errors_count

    def reset(self) -> None:
        """Сбрасывает состояние монитора."""
        with self._lock:
            self._critical_errors_count = 0
            self._last_activity_time = time.time()
        logger.debug("BrowserHealthMonitor сброшен")

    def enable_auto_restart(self, enabled: bool) -> None:
        """Включает или отключает автоматический перезапуск.

        Args:
            enabled: True для включения, False для отключения.

        """
        self._enable_auto_restart = enabled
        logger.info("Автоматический перезапуск: %s", "включен" if enabled else "отключен")
