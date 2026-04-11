"""Модуль удалённого управления Chrome через DevTools Protocol.

Предоставляет класс ChromeRemote для взаимодействия с браузером Chrome:
- Управление браузером через WebSocket
- Выполнение JavaScript кода
- Работа с DOM деревом
- Перехват сетевых запросов

Композиция:
- BrowserManager - управление браузером
- JSExecutor - валидация и выполнение JavaScript
- RequestInterceptor - перехват запросов
- HTTPCache - кэширование HTTP запросов
- RateLimiter - rate limiting для запросов
- HealthMonitor - мониторинг здоровья

ISSUE-003: Рефакторинг - выделены компоненты для соблюдения SRP.
"""

from __future__ import annotations

import base64
import os
import re
import socket
import threading
import time
import types
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Literal

import pychrome
from websocket import WebSocketException

from parser_2gis.logger.logger import logger as app_logger

# ISSUE-043: Разрыв цикла chrome.remote -> utils.decorators -> constants -> parser
# wait_until_finished импортируется напрямую из utils.decorators
from parser_2gis.utils.decorators import wait_until_finished

from .browser import ChromeBrowser
from .constants import (
    CHROME_STARTUP_DELAY,
    EXTERNAL_RATE_LIMIT_CALLS,
    EXTERNAL_RATE_LIMIT_PERIOD,
    LOCALHOST_BASE_URL,
    MAX_PORT,
    MAX_RESPONSE_SIZE,
    MAX_TOTAL_JS_SIZE,
    MIN_PORT,
)
from .dom import DOMNode
from .exceptions import ChromeException
from .js_executor import _validate_js_code
from .patches import patch_all
from .rate_limiter import _safe_external_request
from .request_interceptor import Request, RequestInterceptor, Response

try:
    from ratelimit import limits, sleep_and_retry
except ImportError:
    limits = None
    sleep_and_retry = None

try:
    from requests.exceptions import RequestException
except ImportError:
    RequestException = Exception

# tenacity импортируется из utils.retry при необходимости


# Импорты для backward совместимости

if TYPE_CHECKING:
    from .options import ChromeOptions


# =============================================================================
# ЛОКАЛЬНЫЕ КОНСТАНТЫ И ПАТТЕРНЫ
# =============================================================================

# Задержка между проверками порта в секундах (максимально ускоренная проверка)
PORT_CHECK_RETRY_DELAY: float = 0.005

# ISSUE-096: Конфигурация запуска Chrome вынесена в класс
_DEFAULT_MAX_STARTUP_ATTEMPTS: int = 20


class ChromeStartupConfig:
    """Конфигурация запуска Chrome браузера.

    ISSUE-096: Заменяет чтение MAX_STARTUP_ATTEMPTS из env на уровне модуля.
    """

    @staticmethod
    def get_max_startup_attempts() -> int:
        """Получает максимальное количество попыток запуска Chrome.

        Returns:
            Количество попыток из env или значение по умолчанию (20).

        """
        try:
            value = os.environ.get("PARSER_CHROME_MAX_STARTUP_ATTEMPTS")
            if value is not None:
                return int(value)
        except ValueError:
            pass
        return _DEFAULT_MAX_STARTUP_ATTEMPTS


# Максимальное количество попыток проверки доступности порта при запуске Chrome.
# ISSUE-096: Использует ChromeStartupConfig для ленивого чтения env.
MAX_STARTUP_ATTEMPTS: int = ChromeStartupConfig.get_max_startup_attempts()

# Оптимизация: скомпилированный regex паттерн для проверки портов
_PORT_CHECK_PATTERN = re.compile(r"^http://127\.0\.0\.1:(\d+)$")

# =============================================================================
# TYPE ALIASES
# =============================================================================

# Тип возврата для методов завершения процесса
type ProcessStatus = tuple[bool, str]


# =============================================================================
# ФУНКЦИИ ПРОВЕРКИ ПОРТОВ
# =============================================================================


# C001: Увеличен размер кэша до 256 для поддержки 40+ параллельных браузеров
@lru_cache(maxsize=256)
def _check_port_cached(port: int) -> bool:
    """Проверяет доступность порта с кэшированием через lru_cache.

    C001: Кэширование для снижения накладных расходов при частых проверках портов.
    """
    return _check_port_available_internal(port, timeout=0.6, retries=1)


def get_port_cache_info() -> dict[str, int | None]:
    """Возвращает информацию о кэше проверки портов.

    Returns:
        Словарь с ключами 'hits', 'misses', 'size', 'maxsize'.

    """
    cache_info = _check_port_cached.cache_info()
    return {
        "hits": cache_info.hits,
        "misses": cache_info.misses,
        "size": cache_info.currsize,
        "maxsize": cache_info.maxsize,
    }


def _check_port_available_internal(port: int, timeout: float = 0.6, retries: int = 1) -> bool:
    """Внутренняя функция проверки порта без кэширования.

    Оптимизация: по умолчанию 1 попытка вместо 2 для снижения нагрузки
    при 40+ параллельных браузерах (k*2 -> k проверок).
    """
    result = True

    for attempt in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(timeout)
            connect_result = sock.connect_ex(("127.0.0.1", port))
            if connect_result == 0:
                result = False
                break
            if attempt < retries - 1:
                time.sleep(PORT_CHECK_RETRY_DELAY)
        except OSError as e:
            app_logger.debug("Ошибка при проверке порта %d: %s", port, e)
            result = False
            break
        finally:
            sock.close()

    return result


def _check_port_available(port: int, timeout: float = 0.6, retries: int = 1) -> bool:
    """Проверяет доступность порта для подключения.

    Примечание: Это публичный API, оставлен как обёртка над _check_port_available_internal
    для обеспечения стабильного внешнего интерфейса.

    """
    return _check_port_available_internal(port, timeout=timeout, retries=retries)


def _clear_port_cache() -> None:
    """Очищает кэш проверки портов.

    Примечание: Это публичный API для внешней инвалидации кэша.

    """
    _check_port_cached.cache_clear()


def invalidate_port_cache(_port: int) -> None:
    """Инвалидирует кэш для конкретного порта.

    ISSUE-003-#17: Поскольку lru_cache не поддерживает удаление отдельных записей,
    используем обходной путь — вызываем _check_port_cached с фиктивным результатом,
    чтобы перезаписать кэш. Если порт совпадает, следующая проверка будет реальной.
    """
    # lru_cache не поддерживает удаление отдельных записей.
    # Полная очистка кэша при запросе инвалидации конкретного порта —
    # безопасный вариант для предотвращения stale данных.
    _clear_port_cache()


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def _validate_remote_port(port: Any) -> int:
    """Валидирует remote_port как integer в допустимом диапазоне."""
    if isinstance(port, bool):
        raise ValueError(f"remote_port не должен быть bool, получен {type(port).__name__}")

    if not isinstance(port, int):
        raise ValueError(f"remote_port должен быть integer, получен {type(port).__name__}")

    if port < MIN_PORT:
        raise ValueError(
            f"remote_port должен быть >= {MIN_PORT} (зарезервированные порты), получен {port}"
        )

    if port > MAX_PORT:
        raise ValueError(f"remote_port должен быть <= {MAX_PORT}, получен {port}")

    return port


# Применяем все пользовательские патчи
patch_all()


class ChromeRemote:
    """Обёртка для Chrome DevTools Protocol Interface."""

    def __init__(self, chrome_options: ChromeOptions, response_patterns: list[str]) -> None:
        """Инициализирует ChromeRemote для управления браузером через CDP.

        Args:
            chrome_options: Опции Chrome для настройки браузера.
            response_patterns: Паттерны для фильтрации сетевых ответов.

        Raises:
            ValueError: Если response_patterns некорректен.

        """
        # ISSUE-102: Валидация response_patterns
        if not isinstance(response_patterns, list):
            raise ValueError(
                f"response_patterns должен быть списком, получен {type(response_patterns).__name__}"
            )

        # ISSUE-103: Валидация на пустые паттерны
        for idx, pattern in enumerate(response_patterns):
            if not isinstance(pattern, str):
                raise ValueError(
                    f"response_patterns[{idx}] должен быть строкой, "
                    f"получен {type(pattern).__name__}"
                )
            if not pattern.strip():
                raise ValueError(f"response_patterns[{idx}] не может быть пустой строкой")

        self._chrome_options: ChromeOptions = chrome_options
        self._chrome_browser: ChromeBrowser | None = None
        self._chrome_interface: pychrome.Browser | None = None
        self._chrome_tab: pychrome.Tab | None = None
        self._dev_url: str | None = None
        self._response_patterns: list[str] = response_patterns

        # ISSUE-003: Используем RequestInterceptor для перехвата запросов
        self._request_interceptor = RequestInterceptor()
        # Регистрируем паттерны
        for pattern in response_patterns:
            self._request_interceptor.register_response_pattern(pattern)

        # Счётчик общего размера всех JS скриптов для предотвращения DoS атак
        self._total_js_size: int = 0
        self._js_size_lock = threading.RLock()

    def _connect_interface(self) -> bool:
        """Устанавливает соединение с Chrome и открывает новую вкладку.

        Использует tenacity для retry логики с max_attempts=3.
        Общий таймаут на все попытки подключения не более 60 сек.

        Returns:
            True если подключение успешно, False иначе.

        """
        if self._dev_url is None:
            app_logger.error("dev_url не установлен при подключении")
            return False

        max_attempts = 3
        attempt_delay = 0.05
        total_timeout = 60.0
        start_time = time.time()

        # ID:111: Используем try/finally для гарантии очистки ресурсов
        try:
            for attempt in range(max_attempts):
                elapsed_time = time.time() - start_time
                if elapsed_time >= total_timeout:
                    app_logger.error("Превышен общий таймаут подключения (%.1f сек)", elapsed_time)
                    return False

                try:
                    self._attempt_connection()
                    return True
                except (RequestException, WebSocketException, ChromeException, OSError) as e:
                    app_logger.warning("Попытка %d/%d: %s", attempt + 1, max_attempts, e)
                    # Очистка только при ошибке, не в finally
                    self._cleanup_interface()
                    if attempt < max_attempts - 1:
                        time.sleep(attempt_delay)
                    else:
                        app_logger.error("Все попытки подключения исчерпаны: %s", e)
                        return False

            return False
        finally:
            # ID:111: Дополнительная проверка состояния после выхода из цикла
            if self._chrome_tab is None and self._chrome_interface is None:
                app_logger.debug("Интерфейс полностью очищен в finally")

    def _attempt_connection(self) -> None:
        """Выполняет одну попытку подключения.

        Raises:
            ChromeException: Если dev_url не установлен или порт свободен.
            RequestException, WebSocketException, ChromeException, OSError: При ошибке подключения.

        """
        from urllib.parse import urlparse

        parsed_url = urlparse(self._dev_url)
        port = int(parsed_url.port or 0)

        if _check_port_cached(port):
            raise ChromeException(f"Порт {port} свободен (Chrome ещё не слушает)")

        app_logger.debug("Подключение к Chrome DevTools Protocol: %s", self._dev_url)
        self._chrome_interface = pychrome.Browser(url=self._dev_url)
        self._chrome_tab = self._create_tab()
        self._start_tab_with_timeout(self._chrome_tab, timeout=600)

        if not self._verify_connection():
            self._cleanup_interface()
            # ISSUE-003-#4: Явно устанавливаем _chrome_tab = None после cleanup
            # для предотвращения обращения к уже очищенному объекту
            self._chrome_tab = None
            raise ChromeException("Проверка соединения не пройдена")

        app_logger.info("Успешное подключение к Chrome DevTools Protocol")

    def _cleanup_interface(self) -> None:
        """Очищает ресурсы Chrome interface при ошибке."""
        try:
            if self._chrome_tab is not None:
                try:
                    if self._chrome_tab.status == pychrome.Tab.status_started:
                        self._chrome_tab.stop()
                    if self._dev_url:
                        _safe_external_request(
                            "put",
                            f"{self._dev_url}/json/close/{self._chrome_tab.id}",
                            timeout=10,
                            verify=True,
                        )
                except (OSError, RuntimeError, KeyError, AttributeError) as e:
                    app_logger.debug("Ошибка при очистке вкладки: %s", e)
                finally:
                    self._chrome_tab = None

            if self._chrome_interface is not None:
                self._chrome_interface = None

        except (OSError, RuntimeError, AttributeError) as e:
            app_logger.warning("Непредвиденная ошибка при очистке ресурсов: %s", e)

    def _verify_connection(self) -> bool:
        """Проверяет работоспособность соединения с Chrome."""
        try:
            if self._chrome_tab is None:
                app_logger.error("Chrome tab не инициализирован при проверке соединения")
                return False

            result = self._chrome_tab.Runtime.evaluate(
                expression="1+1",
                returnByValue=True,
                timeout=2000,  # Увеличенный таймаут проверки соединения
            )

            # Устойчивая проверка: результат существует и содержит ожидаемое значение
            if result.get("result") and result["result"].get("value") == 2:
                app_logger.debug("Проверка соединения пройдена")
                return True
            app_logger.warning("Проверка соединения вернула неожиданный результат: %s", result)
            return False

        except (OSError, RuntimeError, AttributeError, KeyError) as e:
            app_logger.warning("Ошибка при проверке соединения: %s", e)
            return False

    def start(self) -> None:
        """Открывает браузер, создаёт новую вкладку, настраивает удалённый интерфейс."""
        try:
            self._chrome_browser = ChromeBrowser(self._chrome_options)

            remote_port = _validate_remote_port(self._chrome_browser.remote_port)
            # D001: Используем константу вместо хардкода
            self._dev_url = LOCALHOST_BASE_URL.format(port=remote_port)

            # Оптимизация: увеличены задержки для поддержки 40+ параллельных браузеров
            startup_delay = CHROME_STARTUP_DELAY
            max_startup_attempts = MAX_STARTUP_ATTEMPTS  # Используем именованную константу
            max_delay = 5.0  # Максимальная задержка между попытками

            for attempt in range(max_startup_attempts):
                app_logger.debug(
                    "Ожидание запуска Chrome (%.1f сек, попытка %d)...", startup_delay, attempt + 1
                )
                time.sleep(startup_delay)

                # C001: Используем кэшированную версию для проверки порта
                if not _check_port_cached(remote_port):
                    app_logger.debug(
                        "Порт %d занят (Chrome запущен), готов к подключению", remote_port
                    )
                    break

                # Увеличиваем задержку экспоненциально, но не более max_delay
                startup_delay = min(startup_delay * 1.5, max_delay)
            else:
                # C001: Очищаем кэш портов и пробуем ещё раз перед ошибкой
                _clear_port_cache()
                if _check_port_cached(remote_port):
                    # Порт всё ещё свободен - Chrome не запустился
                    raise ChromeException(
                        f"Chrome не запустился после {max_startup_attempts} попыток. "
                        f"Порт {remote_port} так и не был занят."
                    )
                # Если порт занят - Chrome запустился, продолжаем

            if not self._connect_interface():
                raise ChromeException("Не удалось подключиться к Chrome DevTools Protocol")

            self._setup_tab()
            self._init_tab_monitor()

        except (OSError, RuntimeError, ChromeException, TimeoutError) as e:
            app_logger.error("Ошибка запуска Chrome: %s", e)
            if self._chrome_browser:
                app_logger.warning("Закрытие браузера из-за ошибки при запуске")
                self._chrome_browser.close()
            raise

    def _start_tab_with_timeout(self, tab: pychrome.Tab, timeout: int = 300) -> None:  # 5 минут
        """Запускает вкладку с таймаутом."""
        result: dict[str, Exception | None] = {"error": None}

        def start_target() -> None:
            """Запускает вкладку Chrome в отдельном потоке.

            Note:
                Функция выполняется в daemon потоке с таймаутом.

            """
            try:
                tab.start()
            except (OSError, RuntimeError, AttributeError) as e:
                result["error"] = e

        thread = threading.Thread(target=start_target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            app_logger.error("Таймаут при запуске вкладки (%d секунд)", timeout)
            raise TimeoutError(f"Запуск вкладки превысил таймаут {timeout} секунд")

        if result["error"]:
            app_logger.error("Ошибка при запуске вкладки: %s", result["error"])
            raise RuntimeError(f"Ошибка при запуске вкладки: {result['error']}")

        app_logger.debug("Вкладка успешно запущена")

    def _create_tab(self) -> pychrome.Tab:
        """Создаёт Chrome-вкладку с повторными попытками.

        ID:115: Используем try/finally для закрытия вкладки при ошибке создания.
        """
        max_attempts = 10
        delay_seconds = 0.15  # Максимально ускоренное создание вкладки
        tab: pychrome.Tab | None = None
        tab_created = False

        # ID:115: Используем try/finally для гарантии закрытия вкладки при ошибке
        try:
            for attempt in range(max_attempts):
                try:
                    app_logger.debug(
                        "Попытка %d/%d: создание вкладки...", attempt + 1, max_attempts
                    )
                    resp = _safe_external_request(
                        "put", f"{self._dev_url}/json/new", json={}, timeout=60, verify=True
                    )

                    # Проверка на None перед вызовом raise_for_status()
                    if resp is None:
                        raise ChromeException("HTTP запрос вернул None")

                    resp.raise_for_status()
                    tab = pychrome.Tab(**resp.json())
                    tab_created = True
                    app_logger.debug("Вкладка успешно создана")
                    return tab

                except (RequestException, ValueError, KeyError) as e:
                    if attempt < max_attempts - 1:
                        app_logger.warning(
                            "Не удалось создать вкладку (попытка %d): %s. "
                            "Повторная попытка через %.1f сек...",
                            attempt + 1,
                            e,
                            delay_seconds,
                        )
                        time.sleep(delay_seconds)
                    else:
                        raise ChromeException(
                            f"Не удалось создать вкладку после {max_attempts} попыток: {e}"
                        ) from e

            raise ChromeException("Не удалось создать вкладку")
        finally:
            # ID:115: Закрываем вкладку если она была создана но не возвращена успешно
            if tab is not None and not tab_created:
                try:
                    self._close_tab(tab)
                    app_logger.debug("Вкладка закрыта в finally (ошибка создания)")
                except (OSError, RuntimeError, ChromeException) as cleanup_error:
                    app_logger.debug("Ошибка при закрытии вкладки в finally: %s", cleanup_error)

    def _close_tab(self, tab: pychrome.Tab) -> None:
        """Закрывает Chrome-вкладку."""
        if tab.status == pychrome.Tab.status_started:
            tab.stop()
        _safe_external_request("put", f"{self._dev_url}/json/close/{tab.id}", verify=True)

    def _setup_tab(self) -> None:
        """Скрывает следы webdriver, включает перехват запросов/ответов, исправляет UA.

        ISSUE-003: Делегирует перехват запросов RequestInterceptor.

        H9: Добавлена явная проверка на None перед использованием _chrome_tab.
        """
        # H9: Явная проверка на None перед использованием _chrome_tab
        if self._chrome_tab is None:
            error_msg = "Chrome tab не инициализирован в _setup_tab. Вкладка не была создана."
            app_logger.error(error_msg)
            # H9: Выбрасываем ChromeException вместо RuntimeError
            raise ChromeException(error_msg)

        original_useragent = self.execute_script("navigator.userAgent")

        if original_useragent:
            fixed_useragent = original_useragent.replace("Headless", "")
        else:
            fixed_useragent = (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            app_logger.warning("Не удалось получить user agent, используется запасной вариант")

        self._chrome_tab.Network.setUserAgentOverride(userAgent=fixed_useragent)

        self.add_start_script(r"""
            # Known limitation: may be detected by anti-bot systems
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        # ISSUE-003: Делегируем перехват запросов RequestInterceptor
        self._request_interceptor.setup_network_interceptors(self._chrome_tab)

        # Включаем остальные события
        self._chrome_tab.DOM.enable()
        self._chrome_tab.Page.enable()
        self._chrome_tab.Runtime.enable()
        self._chrome_tab.Log.enable()

    def _init_tab_monitor(self) -> None:
        """Мониторит здоровье вкладки Chrome."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в _init_tab_monitor")
            return
        if self._dev_url is None:
            app_logger.error("dev_url не установлен в _init_tab_monitor")
            return

        tab_detached = threading.Event()
        # ISSUE-083: Добавляем событие для graceful shutdown потока мониторинга
        shutdown_event = threading.Event()
        # H009: Увеличенный интервал мониторинга до 1 сек для снижения нагрузки на CPU
        monitor_interval = 1.0

        def monitor_tab() -> None:
            """Мониторинг вкладки с оптимизированным интервалом."""
            if self._chrome_tab is None:
                return

            last_check_time: float = 0.0

            try:
                while not self._chrome_tab._stopped.is_set() and not shutdown_event.is_set():
                    current_time = time.time()

                    if current_time - last_check_time >= monitor_interval:
                        try:
                            ret = _safe_external_request(
                                "get", f"{self._dev_url}/json", timeout=6, verify=True
                            )
                            # ИСПРАВЛЕНИЕ: Добавлена проверка на None перед вызовом json()
                            if ret is None:
                                app_logger.debug("HTTP запрос вернул None при мониторинге вкладки")
                                tab_detached.set()
                                self._chrome_tab._stopped.set()
                                break

                            tabs_data = ret.json()
                            tab_found = any(x["id"] == self._chrome_tab.id for x in tabs_data)
                            if not tab_found:
                                tab_detached.set()
                                self._chrome_tab._stopped.set()
                            last_check_time = current_time
                        except (ConnectionError, RequestException, TimeoutError):
                            break

                    # ISSUE-083: Используем shutdown_event.wait() вместо _stopped.wait()
                    # для поддержки graceful shutdown — поток завершится при установке события
                    shutdown_event.wait(monitor_interval)
            finally:
                # ISSUE-083: Гарантированная очистка ресурсов при завершении потока
                app_logger.debug("Поток мониторинга вкладки завершён")

        # ID:117: Используем daemon=True для предотвращения утечки ресурсов
        # daemon поток автоматически завершится при завершении основного приложения
        self._ping_thread = threading.Thread(target=monitor_tab, daemon=True)
        self._ping_thread.start()
        # ISSUE-083: Сохраняем событие shutdown для последующего использования при остановке
        self._tab_monitor_shutdown = shutdown_event

        if self._chrome_tab is None:
            return
        original_send = self._chrome_tab._send

        def wrapped_send(*args: Any, **kwargs: Any) -> Any:
            """Обёртка для отправки сообщений в CDP с обработкой UserAbortException.

            Args:
                *args: Позиционные аргументы для original_send.
                **kwargs: Именованные аргументы для original_send.

            Returns:
                Результат вызова original_send.

            Raises:
                pychrome.UserAbortException: Если вкладка была остановлена.
                pychrome.RuntimeException: Если вкладка была остановлена (преобразованное).

            """
            try:
                return original_send(*args, **kwargs)
            except pychrome.UserAbortException as e:
                if tab_detached.is_set():
                    app_logger.debug("Вкладка была остановлена: %s", e)
                    raise pychrome.RuntimeException("Вкладка была остановлена") from e
                app_logger.debug("UserAbortException при отправке: %s", e)
                raise

        self._chrome_tab._send = wrapped_send

    def navigate(self, url: str, referer: str = "", timeout: int = 3600) -> None:  # 1 час
        """Переходит по URL.

        D001: Санитизация URL для предотвращения WebSocket injection атак.

        Args:
            url: URL для навигации.
            referer: Referer заголовок.
            timeout: Таймаут навигации в секундах.

        Raises:
            ValueError: Если URL некорректен или содержит опасные конструкции.
            ChromeException: При ошибке навигации.

        """
        # D001: Валидация URL перед навигацией
        if not url or not isinstance(url, str):
            raise ValueError("URL должен быть непустой строкой")

        # D001: Проверка на наличие опасных конструкций в URL
        url_lower = url.lower()
        if "javascript:" in url_lower:
            raise ValueError("URL не может содержать javascript: протокол")
        if "data:" in url_lower and "<" in url:
            raise ValueError("URL не может содержать data: URI с HTML")
        if "vbscript:" in url_lower:
            raise ValueError("URL не может содержать vbscript: протокол")

        # D001: Проверка что URL начинается с безопасного протокола
        if not url.startswith(("http://", "https://")):
            raise ValueError(f"URL должен начинаться с http:// или https://, получено: {url[:50]}")

        # D001: Проверка на экранирование символов для предотвращения injection
        dangerous_chars = ["\x00", "\r", "\n", "\t"]
        for char in dangerous_chars:
            if char in url:
                raise ValueError(f"URL содержит недопустимый символ: {char!r}")

        if self._chrome_tab is None:
            # ISSUE-003-#6: Выбрасываем ChromeException вместо возврата None
            error_msg = "Chrome tab не инициализирован в navigate"
            app_logger.error(error_msg)
            raise ChromeException(error_msg)
        try:
            ret = self._chrome_tab.Page.navigate(url=url, _timeout=timeout, referrer=referer)
            error_message = ret.get("errorText", None)
            if error_message:
                raise ChromeException(error_message)
        except ValueError:
            # Пробрасываем ValueError дальше
            raise
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, ConnectionError) as e:
            app_logger.error("Ошибка навигации по URL %s: %s", url, e)
            raise

    @wait_until_finished(timeout=7200, throw_exception=False, poll_interval=0.005)  # 2 часа
    def wait_response(self, response_pattern: str) -> Response | None:
        """Ждёт указанный ответ с предопределённым паттерном.

        ISSUE-003: Делегирует RequestInterceptor.

        Args:
            response_pattern: Паттерн для ожидания ответа.

        Returns:
            Response или None если ответ не найден.

        Raises:
            ChromeException: Если паттерн не зарегистрирован.

        """
        try:
            if self._chrome_tab is None:
                app_logger.warning("Chrome tab не инициализирован")
                return None

            if self._chrome_tab._stopped.is_set():
                app_logger.warning("Вкладка Chrome была остановлена")
                return None

            # ISSUE-003: Делегируем RequestInterceptor
            return self._request_interceptor.get_response(response_pattern, block=False)

        except ChromeException:
            # Пробрасываем ChromeException дальше
            raise
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, ConnectionError) as e:
            app_logger.error("Ошибка при ожидании ответа: %s", e)
            return None

    def clear_requests(self) -> None:
        """Очищает все собранные запросы и очереди ответов.

        ISSUE-003: Делегирует RequestInterceptor.

        """
        self._request_interceptor.clear_requests()

    def _decode_response_body(self, response_data: dict[str, Any], request_id: str) -> str:
        """Декодирует тело ответа с поддержкой base64.

        Args:
            response_data: Данные ответа от CDP.
            request_id: Идентификатор запроса для логирования.

        Returns:
            Декодированное тело ответа в виде строки.

        """
        if response_data.get("base64Encoded"):
            try:
                encoded_body = response_data.get("body", "")
                if encoded_body:
                    decoded_bytes = base64.b64decode(encoded_body)
                    return decoded_bytes.decode("utf-8")
            except (UnicodeDecodeError, ValueError) as decode_error:
                app_logger.warning(
                    "Ошибка декодирования тела ответа (requestId: %s): %s", request_id, decode_error
                )
            return ""
        return response_data.get("body", "")  # type: ignore[no-any-return]

    @wait_until_finished(timeout=7200, throw_exception=False, poll_interval=0.005)  # 2 часа
    def get_response_body(self, response: Response) -> str:
        """Получает тело ответа.

        Args:
            response: Словарь с данными ответа.

        Returns:
            Тело ответа в виде строки или пустую строку при ошибке.

        Raises:
            ValueError: Если размер ответа превышает лимит.

        """
        # Guard Clause: проверка инициализации Chrome tab
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в get_response_body")
            return ""

        # Guard Clause: проверка наличия meta поля
        if "meta" not in response:
            app_logger.warning("Отсутствует поле meta в response")
            return ""

        # Guard Clause: проверка наличия requestId
        if "requestId" not in response["meta"]:
            app_logger.warning("Отсутствует поле requestId в response.meta")
            return ""

        request_id = response["meta"]["requestId"]
        response_data: dict[str, Any] | None = None

        try:
            # Получение тела ответа через CDP
            response_data = self._chrome_tab.call_method(
                "Network.getResponseBody", requestId=request_id
            )

            # Guard Clause: проверка пустого ответа
            if not response_data:
                app_logger.debug("Тело ответа пустое для requestId: %s", request_id)
                return ""

            # Декодирование тела ответа
            response_body = self._decode_response_body(response_data, request_id)

            # Guard Clause: проверка размера ответа
            if len(response_body) > MAX_RESPONSE_SIZE:
                app_logger.warning(
                    "Размер ответа превышает лимит (%d > %d байт) для requestId: %s. "
                    "Ответ отклонён.",
                    len(response_body),
                    MAX_RESPONSE_SIZE,
                    request_id,
                )
                raise ValueError(
                    f"Размер ответа превышает максимальный лимит "
                    f"({len(response_body)} > {MAX_RESPONSE_SIZE} байт). "
                    f"Это может быть DoS атака."
                )

            response["body"] = response_body
            return response_body

        except pychrome.CallMethodException as e:
            app_logger.debug("CallMethodException при получении тела ответа: %s", e)
            return ""
        except KeyError as e:
            app_logger.warning("Отсутствует поле в response при получении тела ответа: %s", e)
            return ""
        except ValueError:
            # Пробрасываем ValueError дальше (превышение размера)
            raise
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError) as e:
            app_logger.warning("Непредвиденная ошибка при получении тела ответа: %s", e)
            return ""
        finally:
            if response_data is not None:
                response_data.pop("body", None)
                response_data = None

    @wait_until_finished(timeout=None, throw_exception=False)
    def get_responses(self) -> list[Response]:
        """Получает собранные ответы."""
        with self._requests_lock:  # type: ignore[attr-defined]
            return [x["response"] for x in self._requests.values() if "response" in x]  # type: ignore[attr-defined]

    def get_requests(self) -> list[Request]:
        """Получает записанные запросы."""
        with self._requests_lock:  # type: ignore[attr-defined]
            return [*self._requests.values()]  # type: ignore[attr-defined]

    def get_document(self, *, full: bool = True) -> DOMNode:
        """Получает DOM-дерево документа."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в get_document")
            return DOMNode(
                nodeId=0, backendNodeId=0, nodeType=0, nodeName="", localName="", nodeValue=""
            )
        tree = self._chrome_tab.DOM.getDocument(depth=-1 if full else 1)
        return DOMNode(**tree["root"])

    def add_start_script(self, source: str) -> None:
        """Добавляет скрипт, выполняющийся на каждой новой странице.

        ISSUE-003-#5: Добавлена валидация типа source перед использованием.
        """
        # ISSUE-003-#5: Валидация source параметра
        if not isinstance(source, str):
            raise TypeError(f"source должен быть строкой, получен {type(source).__name__}")
        if not source or not source.strip():
            raise ValueError("source не может быть пустой строкой")

        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в add_start_script")
            return

        is_valid, error_msg = _validate_js_code(source)
        if not is_valid:
            app_logger.error("Валидация скрипта не пройдена: %s", error_msg)
            raise ValueError(f"Небезопасный JavaScript код: {error_msg}")

        js_code_size = len(source.encode("utf-8"))
        with self._js_size_lock:
            if self._total_js_size + js_code_size > MAX_TOTAL_JS_SIZE:
                raise RuntimeError(
                    f"Превышен максимальный общий размер JS скриптов "
                    f"({self._total_js_size + js_code_size} > {MAX_TOTAL_JS_SIZE} байт). "
                    f"Это может быть DoS атака."
                )
            self._total_js_size += js_code_size

        self._chrome_tab.Page.addScriptToEvaluateOnNewDocument(source=source)

    def add_blocked_requests(self, urls: list[str]) -> bool:
        """Блокирует нежелательные запросы."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в add_blocked_requests")
            return False
        try:
            self._chrome_tab.Network.setBlockedURLs(urls=urls)
            return True
        except pychrome.CallMethodException:
            return False

    def execute_script(self, expression: str, timeout: int = 300) -> Any:  # 5 минут
        """Выполняет скрипт."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в execute_script")
            return None

        app_logger.debug(
            "Выполнение JavaScript: %s",
            expression[:100] + "..." if len(expression) > 100 else expression,
        )

        is_valid, error_msg = _validate_js_code(expression)
        if not is_valid:
            app_logger.error("Валидация выражения не пройдена: %s", error_msg)
            raise ValueError(f"Небезопасный JavaScript код: {error_msg}")

        return self._execute_script_internal(expression, timeout)

    def execute_script_batch(self, expressions: list[str], timeout: int = 300) -> list[Any]:
        """Пакетное выполнение JavaScript выражений.

        C018: Оптимизация через выполнение нескольких выражений в одном CDP вызове.

        Args:
            expressions: Список JavaScript выражений для выполнения.
            timeout: Таймаут выполнения в секундах.

        Returns:
            Список результатов выполнения выражений.

        """
        if not expressions:
            return []

        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в execute_script_batch")
            return [None] * len(expressions)

        # C018: Объединяем выражения в одно для снижения количества CDP вызовов
        # Каждое выражение сохраняется в массиве результатов
        wrapped_expressions = []
        for i, expr in enumerate(expressions):
            is_valid, error_msg = _validate_js_code(expr)
            if not is_valid:
                app_logger.error("Валидация выражения %d не пройдена: %s", i, error_msg)
                wrapped_expressions.append(f"results[{i}] = null; // {error_msg}")
            else:
                wrapped_expressions.append(f"results[{i}] = {expr};")

        # Создаём обёрнутый скрипт
        combined_script = (
            f"var results = new Array({len(expressions)});\n"
            + "\n".join(wrapped_expressions)
            + "\nresults;"
        )

        app_logger.debug(
            "Пакетное выполнение %d JavaScript выражений (общий размер: %d байт)",
            len(expressions),
            len(combined_script),
        )

        return self._execute_script_internal(combined_script, timeout)  # type: ignore[no-any-return]

    def _execute_script_internal_impl(self, expression: str, timeout: int = 300) -> Any:  # 5 минут
        """Внутренний метод выполнения скрипта."""
        result = {"value": None, "error": None}

        def execute_target() -> None:
            """Внутренняя функция для выполнения скрипта."""
            try:
                eval_result = self._chrome_tab.Runtime.evaluate(  # type: ignore[union-attr]
                    expression=expression, returnByValue=True
                )
                result["value"] = eval_result["result"].get("value", None)
            except (KeyboardInterrupt, SystemExit):
                raise
            except (pychrome.CallMethodException, OSError, RuntimeError, KeyError) as e:
                result["error"] = e  # type: ignore[assignment]
                app_logger.warning("Ошибка при выполнении скрипта: %s", e)

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(execute_target)
                try:
                    future.result(timeout=timeout)
                except TimeoutError as timeout_err:
                    app_logger.error("Превышено время выполнения JavaScript (%d секунд)", timeout)
                    raise TimeoutError(
                        f"Выполнение скрипта превысило таймаут {timeout} секунд"
                    ) from timeout_err

            if result["error"]:
                return None

            return result["value"]

        except TimeoutError:
            raise
        except (KeyboardInterrupt, SystemExit):
            raise
        except (RuntimeError, OSError) as e:
            app_logger.warning("Непредвиденная ошибка при выполнении скрипта: %s", e)
            return None

    # D010: Rate limiting теперь обязательный для всех внешних запросов
    # Если ratelimit не установлен, используем fallback с предупреждением
    if sleep_and_retry is not None and limits is not None:
        _execute_script_internal = sleep_and_retry(
            limits(calls=EXTERNAL_RATE_LIMIT_CALLS, period=EXTERNAL_RATE_LIMIT_PERIOD)(
                _execute_script_internal_impl
            )
        )
        app_logger.debug(
            "Rate limiting включён: %d запросов за %d сек",
            EXTERNAL_RATE_LIMIT_CALLS,
            EXTERNAL_RATE_LIMIT_PERIOD,
        )
    else:
        # D010: Предупреждение об отсутствии rate limiting
        app_logger.warning(
            "Rate limiting недоступен (библиотека ratelimit не установлена). "
            "Рекомендуется установить: pip install ratelimit"
        )
        _execute_script_internal = _execute_script_internal_impl

    def perform_click(self, dom_node: DOMNode, timeout: int | None = None) -> None:
        """Выполняет клик мыши на DOM-узле.

        Оптимизировано: использует Input.dispatchMouseEvent для прямого клика
        по координатам элемента (быстрее чем resolveNode + callFunctionOn).
        Fallback на стандартный метод при ошибке.
        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в perform_click")
            return
        try:
            # Шаг 1: Получаем координаты элемента через DOM.getBoxModel
            box = self._chrome_tab.DOM.getBoxModel(backendNodeId=dom_node.backend_id)
            if box and "model" in box:
                content = box["model"]["content"]
                # content = [x1,y1, x2,y2, x3,y3, x4,y4] — углы прямоугольника
                # Вычисляем центр элемента
                cx = (content[0] + content[2] + content[4] + content[6]) / 4
                cy = (content[1] + content[3] + content[5] + content[7]) / 4

                # Шаг 2: Симулируем клик через Input.dispatchMouseEvent (2 вызова)
                self._chrome_tab.Input.dispatchMouseEvent(
                    type="mousePressed", x=int(cx), y=int(cy), button="left", clickCount=1
                )
                self._chrome_tab.Input.dispatchMouseEvent(
                    type="mouseReleased", x=int(cx), y=int(cy), button="left", clickCount=1
                )
                return
        except (ConnectionError, TimeoutError, OSError) as e:
            app_logger.debug("Подавлено исключение в click(): %s", e)

        # Fallback: стандартный метод через resolveNode + callFunctionOn
        try:
            resolved_node = self._chrome_tab.DOM.resolveNode(
                backendNodeId=dom_node.backend_id, _timeout=timeout
            )
            object_id = resolved_node["object"]["objectId"]
            self._chrome_tab.Runtime.callFunctionOn(
                objectId=object_id, functionDeclaration="(function(){this.click()})"
            )
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, ConnectionError) as e:
            app_logger.error("Ошибка при выполнении клика: %s", e)

    def wait(self, timeout: float | None = None) -> None:
        """Ожидает указанное время."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в wait")
            return
        self._chrome_tab.wait(timeout)

    def stop(self) -> None:
        """Закрывает браузер, отключает интерфейс.

        Использует Guard Clauses для уменьшения вложенности.
        """
        app_logger.info("Начало остановки ChromeRemote...")

        # ISSUE-083: Сигнализируем потоку мониторинга о необходимости завершиться
        if hasattr(self, "_tab_monitor_shutdown"):
            self._tab_monitor_shutdown.set()
            if hasattr(self, "_ping_thread") and self._ping_thread.is_alive():
                self._ping_thread.join(timeout=3.0)

        # Остановка вкладки Chrome
        self._stop_chrome_tab()

        # Остановка браузера Chrome
        self._stop_chrome_browser()

        # Отключение интерфейса Chrome
        if self._chrome_interface is not None:
            app_logger.debug("Отключение Chrome интерфейса...")
            self._chrome_interface = None
            app_logger.debug("_chrome_interface обнулён")

        # Финальная очистка ресурсов
        self._cleanup_after_stop()

        app_logger.info("Завершение остановки ChromeRemote - все ресурсы очищены")

    def _stop_chrome_tab(self) -> None:
        """Останавливает Chrome вкладку с обработкой ошибок.

        Guard Clause: если вкладка не инициализирована - метод завершается досрочно.
        """
        if self._chrome_tab is None:
            return

        try:
            app_logger.debug("Закрытие Chrome вкладки...")
            self._close_tab(self._chrome_tab)
            app_logger.info("Chrome вкладка успешно закрыта")
        except (pychrome.RuntimeException, RequestException) as close_tab_error:
            app_logger.error(
                "Ошибка при закрытии вкладки: %s (тип: %s)",
                close_tab_error,
                type(close_tab_error).__name__,
            )
        finally:
            self._chrome_tab = None
            app_logger.debug("_chrome_tab обнулён")

    def _stop_chrome_browser(self) -> None:
        """Останавливает Chrome браузер с обработкой ошибок.

        Guard Clause: если браузер не инициализирован - метод завершается досрочно.
        """
        if self._chrome_browser is None:
            return

        try:
            app_logger.debug("Закрытие Chrome браузера...")
            self._chrome_browser.close()
            app_logger.info("Chrome браузер успешно закрыт")
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, ChromeException) as close_browser_error:
            app_logger.error(
                "Ошибка при закрытии браузера: %s (тип: %s)",
                close_browser_error,
                type(close_browser_error).__name__,
            )
        finally:
            self._chrome_browser = None
            app_logger.debug("_chrome_browser обнулён")

    def _cleanup_after_stop(self) -> None:
        """Выполняет финальную очистку ресурсов после остановки.

        Очищает:
        - Очереди запросов и ответов
        - Кэш портов
        - Обнуляет все ресурсы
        """
        app_logger.debug("Выполнение финальной очистки ресурсов...")

        # Обнуление всех ресурсов
        self._chrome_tab = None
        self._chrome_browser = None
        self._chrome_interface = None

        # Очистка очереди запросов
        try:
            self.clear_requests()
            app_logger.debug("Очередь запросов очищена")
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, AttributeError) as clear_requests_error:
            app_logger.warning("Ошибка при очистке очереди запросов: %s", clear_requests_error)

        # Очистка кэша портов
        try:
            _clear_port_cache()
            app_logger.debug("Кэш портов очищен")
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError) as clear_cache_error:
            app_logger.warning("Ошибка при очистке кэша портов: %s", clear_cache_error)

    def __enter__(self) -> ChromeRemote:
        """Контекстный менеджер: вход.

        Returns:
            Экземпляр ChromeRemote.

        """
        self.start()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: types.TracebackType | None,
    ) -> Literal[False]:
        """Контекстный менеджер: выход.

        Args:
            _exc_type: Тип исключения (если произошло).
            _exc_val: Значение исключения (если произошло).
            _exc_tb: Трассировка исключения (если произошло).

        """
        self.stop()
        return False

    # =============================================================================
    # МЕТОДЫ ДЛЯ BrowserService PROTOCOL
    # =============================================================================
    # Эти методы предоставляют совместимость с Protocol BrowserService
    # для разрыва связи между chrome/ и parser/

    def execute_js(self, js_code: str, timeout: int | None = None) -> Any:
        """Выполнить JavaScript код (алиас для execute_script).

        Метод для совместимости с BrowserService Protocol.

        Args:
            js_code: JavaScript код для выполнения.
            timeout: Таймаут выполнения в секундах (по умолчанию 30).

        Returns:
            Результат выполнения JavaScript.

        Raises:
            ValueError: Если js_code не является строкой или небезопасен.

        """
        # D005: Дополнительная валидация JS кода
        if js_code is None:
            raise ValueError("JavaScript код не может быть None")
        if not isinstance(js_code, str):
            raise TypeError(f"JavaScript код должен быть строкой, получен {type(js_code).__name__}")
        if not js_code.strip():
            raise ValueError("JavaScript код не может быть пустым")

        if timeout is None:
            timeout = 600  # 10 минут
        return self.execute_script(expression=js_code, timeout=timeout)

    def get_html(self) -> str:
        """Получить HTML страницы.

        Returns:
            HTML содержимое текущей страницы.

        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в get_html")
            return ""

        try:
            # Получаем outerHTML документа
            result = self._chrome_tab.Runtime.evaluate(
                expression="document.documentElement.outerHTML", returnByValue=True, timeout=20000
            )
            if result and "result" in result:
                return result["result"].get("value", "")  # type: ignore[no-any-return]
            return ""
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError, ConnectionError) as e:
            app_logger.error("Ошибка при получении HTML: %s", e)
            return ""

    def screenshot(self, path: str) -> None:
        """Сделать скриншот страницы и сохранить в файл.

        Args:
            path: Путь для сохранения скриншота (PNG).

        """
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в screenshot")
            return

        try:
            # Получаем скриншот в формате base64
            result = self._chrome_tab.Page.captureScreenshot(format="png", fromSurface=True)

            if result and "data" in result:
                import base64

                image_data = base64.b64decode(result["data"])

                with open(path, "wb") as f:
                    f.write(image_data)

                app_logger.debug("Скриншот сохранён: %s", path)
            else:
                app_logger.error("Не удалось получить скриншот: пустой результат")
        except (KeyboardInterrupt, SystemExit):
            raise
        except (OSError, RuntimeError) as e:
            app_logger.error("Ошибка при создании скриншота: %s", e)
            raise

    def close(self) -> None:
        """Закрыть браузер и освободить ресурсы (алиас для stop).

        Метод для совместимости с BrowserService Protocol.
        """
        self.stop()

    def __repr__(self) -> str:
        """Возвращает строковое представление объекта ChromeRemote.

        Returns:
            Строка с именем класса и параметрами.

        """
        classname = self.__class__.__name__
        return (
            f"{classname}(options={self._chrome_options!r}, "
            f"response_patterns={self._response_patterns!r})"
        )
