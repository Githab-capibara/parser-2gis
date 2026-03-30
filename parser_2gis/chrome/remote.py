"""Модуль удалённого управления Chrome через DevTools Protocol.

Предоставляет класс ChromeRemote для взаимодействия с браузером Chrome:
- Управление браузером через WebSocket
- Выполнение JavaScript кода
- Работа с DOM деревом
- Перехват сетевых запросов

Композиция:
- JSExecutor - валидация и выполнение JavaScript
- HTTPCache - кэширование HTTP запросов
- RateLimiter - rate limiting для запросов
"""

from __future__ import annotations

import base64
import queue
import re
import socket
import threading
import time
import weakref
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import pychrome
from websocket import WebSocketException

from parser_2gis.logger.logger import logger as app_logger
from parser_2gis.utils.decorators import wait_until_finished

from .browser import ChromeBrowser
from .constants import (
    CHROME_STARTUP_DELAY,
    EXTERNAL_RATE_LIMIT_CALLS,
    EXTERNAL_RATE_LIMIT_PERIOD,
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

try:
    from ratelimit import limits, sleep_and_retry
except ImportError:
    limits = None  # type: ignore[assignment, misc]
    sleep_and_retry = None  # type: ignore[assignment, misc]

_RATELIMIT_AVAILABLE = limits is not None and sleep_and_retry is not None

try:
    from requests.exceptions import RequestException
except ImportError:
    RequestException = Exception  # type: ignore[misc, assignment]


# Импорты для backward совместимости

if TYPE_CHECKING:
    from .options import ChromeOptions

    Request = Dict[str, Any]
    Response = Dict[str, Any]


# =============================================================================
# ЛОКАЛЬНЫЕ КОНСТАНТЫ И ПАТТЕРНЫ
# =============================================================================

# Задержка между проверками порта в секундах
PORT_CHECK_RETRY_DELAY: float = 0.005  # Максимально ускоренная проверка порта

# Оптимизация: скомпилированный regex паттерн для проверки портов
_PORT_CHECK_PATTERN = re.compile(r"^http://127\.0\.0\.1:(\d+)$")


# =============================================================================
# ФУНКЦИИ ПРОВЕРКИ ПОРТОВ
# =============================================================================


@lru_cache(maxsize=64)
def _check_port_cached(port: int) -> bool:
    """Проверяет доступность порта с кэшированием через lru_cache."""
    return _check_port_available_internal(port, timeout=0.3, retries=1)


def _check_port_available_internal(port: int, timeout: float = 0.3, retries: int = 2) -> bool:
    """Внутренняя функция проверки порта без кэширования."""
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
        except (socket.error, OSError) as e:
            app_logger.debug("Ошибка при проверке порта %d: %s", port, e)
            result = False
            break
        finally:
            sock.close()

    return result


def _check_port_available(port: int, timeout: float = 0.3, retries: int = 2) -> bool:
    """Проверяет доступность порта для подключения."""
    return _check_port_available_internal(port, timeout=timeout, retries=retries)


def _clear_port_cache() -> None:
    """Очищает кэш проверки портов."""
    _check_port_cached.cache_clear()


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

    _active_instances: weakref.WeakSet["ChromeRemote"] = weakref.WeakSet()

    def __init__(self, chrome_options: ChromeOptions, response_patterns: list[str]) -> None:
        """Инициализирует ChromeRemote для управления браузером через CDP.

        Args:
            chrome_options: Опции Chrome для настройки браузера.
            response_patterns: Паттерны для фильтрации сетевых ответов.
        """
        self._chrome_options: ChromeOptions = chrome_options
        self._chrome_browser: Optional[ChromeBrowser] = None
        self._chrome_interface: Optional[pychrome.Browser] = None
        self._chrome_tab: Optional[pychrome.Tab] = None
        self._dev_url: Optional[str] = None
        self._response_patterns: list[str] = response_patterns
        self._response_queues: dict[str, queue.Queue[Response]] = {
            x: queue.Queue() for x in response_patterns
        }
        self._requests: dict[str, Request] = {}
        self._requests_lock = threading.RLock()

        # Счётчик общего размера всех JS скриптов для предотвращения DoS атак
        self._total_js_size: int = 0
        self._js_size_lock = threading.RLock()

    @wait_until_finished(timeout=3600)  # 1 час
    def _connect_interface(self) -> bool:
        """Устанавливает соединение с Chrome и открывает новую вкладку."""
        max_attempts = 3
        attempt_delay = 0.05  # Максимально ускоренное подключение

        for attempt in range(max_attempts):
            try:
                if self._dev_url is None:
                    app_logger.error("dev_url не установлен при подключении")
                    return False
                from urllib.parse import urlparse

                parsed_url = urlparse(self._dev_url)
                port = int(parsed_url.port)

                if _check_port_available(port, timeout=10.0):  # Увеличено для стабильности
                    app_logger.warning(
                        "Порт %d свободен (Chrome ещё не слушает), попытка %d/%d",
                        port,
                        attempt + 1,
                        max_attempts,
                    )
                    if attempt < max_attempts - 1:
                        time.sleep(attempt_delay)
                        continue
                    return False

                app_logger.debug(
                    "Подключение к Chrome DevTools Protocol по адресу: %s", self._dev_url
                )
                self._chrome_interface = pychrome.Browser(url=self._dev_url)

                app_logger.debug("Создание вкладки через _create_tab()...")
                self._chrome_tab = self._create_tab()

                app_logger.debug("Запуск вкладки с timeout=300...")
                self._start_tab_with_timeout(self._chrome_tab, timeout=300)  # 5 минут

                if not self._verify_connection():
                    app_logger.warning("Проверка соединения не пройдена, повторная попытка")
                    self._cleanup_interface()
                    if attempt < max_attempts - 1:
                        time.sleep(attempt_delay)
                        continue
                    app_logger.error(
                        "Все попытки подключения исчерпаны (проверка соединения не пройдена)"
                    )
                    return False

                app_logger.info("Успешное подключение к Chrome DevTools Protocol")
                return True

            except (RequestException, WebSocketException, ChromeException) as e:
                app_logger.error(
                    "Ошибка подключения к Chrome DevTools Protocol (%s): %s", self._dev_url, e
                )
                self._cleanup_interface()
                if attempt < max_attempts - 1:
                    time.sleep(attempt_delay)
                continue

        app_logger.error("Все %d попыток подключения исчерпаны", max_attempts)
        return False

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
                            "%s/json/close/%s" % (self._dev_url, self._chrome_tab.id),
                            timeout=5,
                            verify=True,
                        )
                except Exception as e:
                    app_logger.debug("Ошибка при очистке вкладки: %s", e)
                finally:
                    self._chrome_tab = None

            if self._chrome_interface is not None:
                self._chrome_interface = None

        except Exception as e:
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
                timeout=1000,  # Максимально ускоренный таймаут проверки соединения
            )

            if result and result.get("result", {}).get("value") == 2:
                app_logger.debug("Проверка соединения пройдена")
                return True
            else:
                app_logger.warning("Проверка соединения вернула неожиданный результат: %s", result)
                return False

        except Exception as e:
            app_logger.warning("Ошибка при проверке соединения: %s", e)
            return False

    def start(self) -> None:
        """Открывает браузер, создаёт новую вкладку, настраивает удалённый интерфейс."""
        try:
            self._chrome_browser = ChromeBrowser(self._chrome_options)

            remote_port = _validate_remote_port(self._chrome_browser.remote_port)
            self._dev_url = f"http://127.0.0.1:{remote_port}"

            # Оптимизация: увеличены задержки для поддержки 40+ параллельных браузеров
            startup_delay = CHROME_STARTUP_DELAY
            max_startup_attempts = 20  # Увеличено для 40+ браузеров
            max_delay = 5.0  # Максимальная задержка между попытками

            for attempt in range(max_startup_attempts):
                app_logger.debug(
                    "Ожидание запуска Chrome (%.1f сек, попытка %d)...", startup_delay, attempt + 1
                )
                time.sleep(startup_delay)

                # ИСПРАВЛЕНИЕ: Увеличено количество проверок порта и время таймаута
                if not _check_port_available(remote_port, timeout=2.0, retries=3):
                    app_logger.debug(
                        "Порт %d занят (Chrome запущен), готов к подключению", remote_port
                    )
                    break

                # Увеличиваем задержку экспоненциально, но не более max_delay
                startup_delay = min(startup_delay * 1.5, max_delay)
            else:
                # ИСПРАВЛЕНИЕ: Очищаем кэш портов и пробуем ещё раз перед ошибкой
                _clear_port_cache()
                if _check_port_available(remote_port, timeout=2.0, retries=3):
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

        except Exception as e:
            app_logger.error("Ошибка запуска Chrome: %s", e)
            if self._chrome_browser:
                app_logger.warning("Закрытие браузера из-за ошибки при запуске")
                self._chrome_browser.close()
            raise

    def _start_tab_with_timeout(self, tab: pychrome.Tab, timeout: int = 300) -> None:  # 5 минут
        """Запускает вкладку с таймаутом."""
        result: Dict[str, Optional[Exception]] = {"error": None}

        def start_target() -> None:
            """Запускает вкладку Chrome в отдельном потоке.

            Note:
                Функция выполняется в daemon потоке с таймаутом.
            """
            try:
                tab.start()
            except Exception as e:
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
        """Создаёт Chrome-вкладку с повторными попытками."""
        max_attempts = 10
        delay_seconds = 0.15  # Максимально ускоренное создание вкладки

        for attempt in range(max_attempts):
            try:
                app_logger.debug("Попытка %d/%d: создание вкладки...", attempt + 1, max_attempts)
                resp = _safe_external_request(
                    "put", "%s/json/new" % (self._dev_url), json={}, timeout=60, verify=True
                )

                # Проверка на None перед вызовом raise_for_status()
                if resp is None:
                    raise ChromeException("HTTP запрос вернул None")

                resp.raise_for_status()
                app_logger.debug("Вкладка успешно создана")
                return pychrome.Tab(**resp.json())

            except (RequestException, ValueError, KeyError) as e:
                if attempt < max_attempts - 1:
                    app_logger.warning(
                        "Не удалось создать вкладку (попытка %d): %s. Повторная попытка через %.1f сек...",
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

    def _close_tab(self, tab: pychrome.Tab) -> None:
        """Закрывает Chrome-вкладку."""
        if tab.status == pychrome.Tab.status_started:
            tab.stop()
        _safe_external_request("put", "%s/json/close/%s" % (self._dev_url, tab.id), verify=True)

    def _setup_tab(self) -> None:
        """Скрывает следы webdriver, включает перехват запросов/ответов, исправляет UA."""
        if self._chrome_tab is None:
            error_msg = "Chrome tab не инициализирован в _setup_tab. Вкладка не была создана."
            app_logger.error(error_msg)
            raise RuntimeError(error_msg)

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
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        def responseReceived(**kwargs) -> None:
            """Собирает ответы."""
            response = kwargs["response"]
            request_id = kwargs["requestId"]
            resource_type = kwargs.get("type")

            response["meta"] = {k: v for k, v in kwargs.items() if k != "response"}

            if resource_type == "Preflight":
                return

            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response["request"] = request
                    request["response"] = response

                    for pattern in self._response_patterns:
                        if re.match(pattern, response["url"]):
                            self._response_queues[pattern].put(response)

        def loadingFailed(**kwargs) -> None:
            """Обрабатывает неудачные загрузки запросов."""
            error_text = kwargs.get("errorText")
            blocked_reason = kwargs.get("blockedReason")
            status_text = ""

            if error_text:
                status_text = f"error: {error_text}"
            if blocked_reason:
                if status_text:
                    status_text += ", "
                status_text += f"blocked_reason: {blocked_reason}"

            request_id = kwargs.get("requestId")
            response = {"status": -1, "statusText": status_text}

            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response["request"] = request
                    request["response"] = response
                    request_url = request["url"]

                    if request_url:
                        for pattern in self._response_patterns:
                            if re.match(pattern, request_url):
                                self._response_queues[pattern].put(response)

        def requestWillBeSent(**kwargs) -> None:
            """Обработчик события отправки HTTP запроса.

            Args:
                **kwargs: Параметры запроса (requestId, request, type, etc.).

            Note:
                Игнорирует Preflight запросы (OPTIONS).
            """
            request = kwargs.pop("request")
            request["meta"] = kwargs
            request_id = kwargs["requestId"]
            resource_type = kwargs.get("type")

            if resource_type == "Preflight":
                return

            with self._requests_lock:
                self._requests[request_id] = request

        self._chrome_tab.Network.responseReceived = responseReceived
        self._chrome_tab.Network.loadingFailed = loadingFailed
        self._chrome_tab.Network.requestWillBeSent = requestWillBeSent

        self._chrome_tab.Network.enable()
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
        MONITOR_INTERVAL = (
            0.25  # Оптимизированный интервал мониторинга вкладки для быстрого обнаружения проблем
        )

        def monitor_tab() -> None:
            """Мониторинг вкладки с оптимизированным интервалом."""
            if self._chrome_tab is None:
                return

            last_check_time: float = 0.0

            while not self._chrome_tab._stopped.is_set():
                current_time = time.time()

                if current_time - last_check_time >= MONITOR_INTERVAL:
                    try:
                        ret = _safe_external_request(
                            "get", "%s/json" % self._dev_url, timeout=3, verify=True
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

                self._chrome_tab._stopped.wait(MONITOR_INTERVAL)

        self._ping_thread = threading.Thread(target=monitor_tab, daemon=True)
        self._ping_thread.start()

        if self._chrome_tab is None:
            return
        original_send = self._chrome_tab._send

        def wrapped_send(*args, **kwargs) -> Any:
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
                else:
                    app_logger.debug("UserAbortException при отправке: %s", e)
                    raise

        self._chrome_tab._send = wrapped_send

    def navigate(self, url: str, referer: str = "", timeout: int = 3600) -> None:  # 1 час
        """Переходит по URL."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в navigate")
            return
        try:
            ret = self._chrome_tab.Page.navigate(url=url, _timeout=timeout, referrer=referer)
            error_message = ret.get("errorText", None)
            if error_message:
                raise ChromeException(error_message)
        except Exception as e:
            app_logger.error("Ошибка навигации по URL %s: %s", url, e)
            raise

    @wait_until_finished(timeout=3600, throw_exception=False, poll_interval=0.005)  # 1 час
    def wait_response(self, response_pattern: str) -> Optional[Response]:
        """Ждёт указанный ответ с предопределённым паттерном."""
        try:
            if self._chrome_tab is None:
                app_logger.warning("Chrome tab не инициализирован")
                return None

            if self._chrome_tab._stopped.is_set():
                app_logger.warning("Вкладка Chrome была остановлена")
                return None

            return self._response_queues[response_pattern].get(block=False)
        except queue.Empty:
            return None
        except KeyError:
            app_logger.warning("Неизвестный паттерн ответа: %s", response_pattern)
            return None
        except Exception as e:
            app_logger.error("Ошибка при ожидании ответа: %s", e)
            return None

    def clear_requests(self) -> None:
        """Очищает все собранные запросы и очереди ответов."""
        with self._requests_lock:
            self._requests = {}
        for pattern_queue in self._response_queues.values():
            while not pattern_queue.empty():
                try:
                    pattern_queue.get_nowait()
                except queue.Empty:
                    break

    @wait_until_finished(timeout=3600, throw_exception=False, poll_interval=0.005)  # 1 час
    def get_response_body(self, response: Response) -> str:
        """Получает тело ответа."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в get_response_body")
            return ""

        response_data: Optional[Dict[str, Any]] = None
        response_body: str = ""

        try:
            if "meta" not in response:
                app_logger.warning("Отсутствует поле meta в response")
                return ""

            if "requestId" not in response["meta"]:
                app_logger.warning("Отсутствует поле requestId в response.meta")
                return ""

            request_id = response["meta"]["requestId"]

            response_data = self._chrome_tab.call_method(
                "Network.getResponseBody", requestId=request_id
            )

            if not response_data:
                app_logger.debug("Тело ответа пустое для requestId: %s", request_id)
                return ""

            if response_data.get("base64Encoded"):
                try:
                    encoded_body = response_data.get("body", "")
                    if encoded_body:
                        decoded_bytes = base64.b64decode(encoded_body)
                        response_body = decoded_bytes.decode("utf-8")
                    else:
                        response_body = ""
                except (UnicodeDecodeError, ValueError) as decode_error:
                    app_logger.warning(
                        "Ошибка декодирования тела ответа (requestId: %s): %s",
                        request_id,
                        decode_error,
                    )
                    response_body = ""
            else:
                response_body = response_data.get("body", "")

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

        except Exception as e:
            app_logger.warning("Непредвиденная ошибка при получении тела ответа: %s", e)
            return ""

        finally:
            if response_data is not None:
                response_data.pop("body", None)
                response_data = None

    @wait_until_finished(timeout=None, throw_exception=False)
    def get_responses(self) -> List[Response]:
        """Получает собранные ответы."""
        with self._requests_lock:
            return [x["response"] for x in self._requests.values() if "response" in x]

    def get_requests(self) -> List[Request]:
        """Получает записанные запросы."""
        with self._requests_lock:
            return [*self._requests.values()]

    def get_document(self, full: bool = True) -> DOMNode:
        """Получает DOM-дерево документа."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в get_document")
            return DOMNode(
                nodeId=0, backendNodeId=0, nodeType=0, nodeName="", localName="", nodeValue=""
            )
        tree = self._chrome_tab.DOM.getDocument(depth=-1 if full else 1)
        return DOMNode(**tree["root"])

    def add_start_script(self, source: str) -> None:
        """Добавляет скрипт, выполняющийся на каждой новой странице."""
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

    def add_blocked_requests(self, urls: List[str]) -> bool:
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

    def _execute_script_internal_impl(self, expression: str, timeout: int = 300) -> Any:  # 5 минут
        """Внутренний метод выполнения скрипта."""
        result = {"value": None, "error": None}

        def execute_target() -> None:
            """Внутренняя функция для выполнения скрипта."""
            try:
                eval_result = self._chrome_tab.Runtime.evaluate(
                    expression=expression, returnByValue=True
                )
                result["value"] = eval_result["result"].get("value", None)
            except Exception as e:
                result["error"] = e
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
        except Exception as e:
            app_logger.warning("Непредвиденная ошибка при выполнении скрипта: %s", e)
            return None

    if _RATELIMIT_AVAILABLE:
        _execute_script_internal = sleep_and_retry(
            limits(calls=EXTERNAL_RATE_LIMIT_CALLS, period=EXTERNAL_RATE_LIMIT_PERIOD)(
                _execute_script_internal_impl
            )
        )
    else:
        _execute_script_internal = _execute_script_internal_impl

    def perform_click(self, dom_node: DOMNode, timeout: Optional[int] = None) -> None:
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
        except Exception as e:
            app_logger.error("Ошибка при выполнении клика: %s", e)

    def wait(self, timeout: Optional[float] = None) -> None:
        """Ожидает указанное время."""
        if self._chrome_tab is None:
            app_logger.error("Chrome tab не инициализирован в wait")
            return
        self._chrome_tab.wait(timeout)

    def stop(self) -> None:
        """Закрывает браузер, отключает интерфейс."""
        app_logger.info("Начало остановки ChromeRemote...")

        try:
            if self._chrome_tab is not None:
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

            if self._chrome_browser is not None:
                try:
                    app_logger.debug("Закрытие Chrome браузера...")
                    self._chrome_browser.close()
                    app_logger.info("Chrome браузер успешно закрыт")
                except Exception as close_browser_error:
                    app_logger.error(
                        "Ошибка при закрытии браузера: %s (тип: %s)",
                        close_browser_error,
                        type(close_browser_error).__name__,
                    )
                finally:
                    self._chrome_browser = None
                    app_logger.debug("_chrome_browser обнулён")

            if self._chrome_interface is not None:
                app_logger.debug("Отключение Chrome интерфейса...")
                self._chrome_interface = None
                app_logger.debug("_chrome_interface обнулён")

        except Exception as outer_error:
            app_logger.critical(
                "Критическая ошибка при остановке ChromeRemote: %s (тип: %s)",
                outer_error,
                type(outer_error).__name__,
                exc_info=True,
            )
        finally:
            app_logger.debug("Выполнение финальной очистки ресурсов...")

            self._chrome_tab = None
            self._chrome_browser = None
            self._chrome_interface = None

            try:
                self.clear_requests()
                app_logger.debug("Очередь запросов очищена")
            except Exception as clear_requests_error:
                app_logger.warning("Ошибка при очистке очереди запросов: %s", clear_requests_error)

            self._response_queues = {}
            app_logger.debug("Очереди ответов обнулены")

            try:
                _clear_port_cache()
                app_logger.debug("Кэш портов очищен")
            except Exception as clear_cache_error:
                app_logger.warning("Ошибка при очистке кэша портов: %s", clear_cache_error)

            app_logger.info("Завершение остановки ChromeRemote - все ресурсы очищены")

    def __enter__(self) -> "ChromeRemote":
        """Контекстный менеджер: вход.

        Returns:
            Экземпляр ChromeRemote.
        """
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Контекстный менеджер: выход.

        Args:
            exc_info: Информация об исключении (если было).
        """
        self.stop()

    # =============================================================================
    # МЕТОДЫ ДЛЯ BrowserService PROTOCOL
    # =============================================================================
    # Эти методы предоставляют совместимость с Protocol BrowserService
    # для разрыва связи между chrome/ и parser/

    def execute_js(self, js_code: str, timeout: Optional[int] = None) -> Any:
        """Выполнить JavaScript код (алиас для execute_script).

        Метод для совместимости с BrowserService Protocol.

        Args:
            js_code: JavaScript код для выполнения.
            timeout: Таймаут выполнения в секундах (по умолчанию 30).

        Returns:
            Результат выполнения JavaScript.
        """
        if timeout is None:
            timeout = 300  # 5 минут
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
                expression="document.documentElement.outerHTML", returnByValue=True, timeout=10000
            )
            if result and "result" in result:
                return result["result"].get("value", "")
            return ""
        except Exception as e:
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
        except Exception as e:
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
        return f"{classname}(options={self._chrome_options!r}, response_patterns={self._response_patterns!r})"
