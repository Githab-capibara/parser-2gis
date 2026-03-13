from __future__ import annotations

import base64
import queue
import re
import socket
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import pychrome
import requests
from requests.exceptions import RequestException
from websocket import WebSocketException

from ..common import wait_until_finished
from ..logger import logger
from .browser import ChromeBrowser
from .dom import DOMNode
from .exceptions import ChromeException
from .patches import patch_all

# Константа задержки запуска Chrome для стабильного подключения
CHROME_STARTUP_DELAY = 1.5

# Максимальная длина JavaScript кода для предотвращения DoS атак
MAX_JS_CODE_LENGTH = 1_000_000  # 1MB лимит

# Паттерн для обнаружения потенциально опасных конструкций в JS
_DANGEROUS_JS_PATTERNS = [
    (r'\beval\s*\(', 'eval() запрещён'),
    (r'\bFunction\s*\(', 'конструктор Function запрещён'),
    (r'\bsetTimeout\s*\([^,]*,\s*["\']', 'setTimeout с строковым кодом запрещён'),
    (r'\bsetInterval\s*\([^,]*,\s*["\']', 'setInterval с строковым кодом запрещён'),
    (r'\bdocument\.write\s*\(', 'document.write() запрещён'),
    (r'\.innerHTML\s*=', 'прямая установка innerHTML запрещена'),
    (r'\.outerHTML\s*=', 'прямая установка outerHTML запрещена'),
]


def _validate_js_code(code: str, max_length: int = MAX_JS_CODE_LENGTH) -> tuple[bool, str]:
    """Валидирует JavaScript код на безопасность.

    Args:
        code: JavaScript код для валидации.
        max_length: Максимальная допустимая длина кода.

    Returns:
        Кортеж (is_valid, error_message):
        - is_valid: True если код безопасен, False иначе
        - error_message: Сообщение об ошибке или пустая строка

    Примечание:
        Проверки включают:
        - Проверка на None и пустую строку
        - Проверка максимальной длины
        - Проверка типа данных
        - Обнаружение опасных паттернов (eval, Function, document.write)
    """
    # Проверка на None
    if code is None:
        return False, "JavaScript код не может быть None"

    # Проверка типа
    if not isinstance(code, str):
        return False, f"JavaScript код должен быть строкой, получен {type(code).__name__}"

    # Проверка на пустую строку
    if not code.strip():
        return False, "JavaScript код не может быть пустым"

    # Проверка максимальной длины
    if len(code) > max_length:
        return False, f"JavaScript код превышает максимальную длину ({len(code)} > {max_length} символов)"

    # Проверка на опасные паттерны
    for pattern, description in _DANGEROUS_JS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"Обнаружен опасный паттерн в JavaScript коде: {description}"

    return True, ""


def _sanitize_js_string(value: str) -> str:
    """Санитизирует строку для безопасного использования в JavaScript.

    Args:
        value: Исходная строка.

    Returns:
        Санитизированная строка с экранированными специальными символами.

    Примечание:
        Экранирует следующие символы:
        - Обратные кавычки (`)
        - Обратные слеши (\\)
        - Доллар ($) для предотвращения инъекций в template literals
    """
    if not isinstance(value, str):
        value = str(value)

    # Экранируем обратные слеши в первую очередь
    value = value.replace('\\', '\\\\')
    # Экранируем обратные кавычки
    value = value.replace('`', '\\`')
    # Экранируем доллар для предотвращения инъекций
    value = value.replace('$', '\\$')
    # Экранируем кавычки
    value = value.replace("'", "\\'")
    value = value.replace('"', '\\"')

    return value

if TYPE_CHECKING:
    from .options import ChromeOptions

    Request = Dict[str, Any]
    Response = Dict[str, Any]


def _validate_remote_port(port: Any) -> int:
    """Валидирует remote_port как integer в допустимом диапазоне.

    Args:
        port: Значение порта для валидации.

    Returns:
        Валидный номер порта.

    Raises:
        ValueError: Если порт некорректен.

    Примечание:
        - Проверяется тип (не bool, только int)
        - Проверяется диапазон 1024-65535
        - Исключаются зарезервированные порты
    """
    # Явная проверка на bool, так как bool является подклассом int
    if isinstance(port, bool):
        raise ValueError(
            f"remote_port не должен быть bool, получен {type(port).__name__}"
        )

    if not isinstance(port, int):
        raise ValueError(
            f"remote_port должен быть integer, получен {type(port).__name__}"
        )

    # Проверка диапазона портов
    if port < 1024:
        raise ValueError(
            f"remote_port должен быть >= 1024 (зарезервированные порты), получен {port}"
        )

    if port > 65535:
        raise ValueError(f"remote_port должен быть <= 65535, получен {port}")

    return port


def _check_port_available(port: int, timeout: float = 0.5, retries: int = 2) -> bool:
    """Проверяет доступность порта для подключения.

    Args:
        port: Номер порта для проверки.
        timeout: Таймаут проверки в секундах.
        retries: Количество повторных проверок для снижения race condition.

    Returns:
        True если порт доступен для подключения, False иначе.

    Примечание:
        Использует TCP socket для проверки доступности порта.
        Выполняет несколько проверок для снижения race condition.
    """
    for attempt in range(retries):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex(("127.0.0.1", port))
            # Если порт занят (result == 0), возвращаем False немедленно
            if result == 0:
                return False
            # Небольшая задержка между проверками
            if attempt < retries - 1:
                time.sleep(0.1)
        except Exception:
            return False
        finally:
            sock.close()
    # Порт свободен после всех проверок
    return True


# Применяем все пользовательские патчи
patch_all()


class ChromeRemote:
    """Обёртка для Chrome DevTools Protocol Interface.

    Args:
        chrome_options: Параметры ChromeOptions.
        response_patterns: Паттерны URL ответов для перехвата.
    """

    def __init__(
        self, chrome_options: ChromeOptions, response_patterns: list[str]
    ) -> None:
        self._chrome_options: ChromeOptions = chrome_options
        self._chrome_browser: Optional[ChromeBrowser] = None
        self._chrome_interface: Optional[pychrome.Browser] = None
        self._chrome_tab: Optional[pychrome.Tab] = None
        self._dev_url: Optional[str] = None
        self._response_patterns: list[str] = response_patterns
        self._response_queues: dict[str, queue.Queue[Response]] = {
            x: queue.Queue() for x in response_patterns
        }
        self._requests: dict[str, Request] = {}  # _requests[request_id] = <Request>
        self._requests_lock = threading.Lock()

    @wait_until_finished(timeout=300)
    def _connect_interface(self) -> bool:
        """Устанавливает соединение с Chrome и открывает новую вкладку.

        Returns:
            `True` при успехе, `False` при неудаче.

        Примечание:
            Функция детально логирует все ошибки подключения для отладки.
            Перед подключением проверяется доступность порта.
            Выполняется до 3 попыток подключения.
        """
        max_attempts = 3
        attempt_delay = 2.0

        for attempt in range(max_attempts):
            try:
                # Извлекаем порт из dev_url для проверки
                port = int(self._dev_url.split(":")[-1])

                # Проверка доступности порта перед подключением
                if not _check_port_available(port, timeout=1.0):
                    logger.warning(
                        "Порт %d недоступен при подключении к DevTools (попытка %d/%d)",
                        port,
                        attempt + 1,
                        max_attempts,
                    )
                    if attempt < max_attempts - 1:
                        time.sleep(attempt_delay)
                        continue
                    return False

                logger.debug(
                    "Подключение к Chrome DevTools Protocol по адресу: %s",
                    self._dev_url,
                )
                self._chrome_interface = pychrome.Browser(url=self._dev_url)

                logger.debug("Создание вкладки через _create_tab()...")
                self._chrome_tab = self._create_tab()

                logger.debug("Запуск вкладки...")
                self._chrome_tab.start()
                logger.info("Успешное подключение к Chrome DevTools Protocol")
                return True

            except RequestException as e:
                # Ошибки HTTP/сети
                logger.error(
                    "Ошибка сети при подключении к Chrome DevTools Protocol (%s): %s",
                    self._dev_url,
                    e,
                )
                if attempt < max_attempts - 1:
                    time.sleep(attempt_delay)
                continue

            except WebSocketException as e:
                # Ошибки WebSocket соединения
                logger.error(
                    "Ошибка WebSocket при подключении к Chrome DevTools Protocol (%s): %s",
                    self._dev_url,
                    e,
                )
                if attempt < max_attempts - 1:
                    time.sleep(attempt_delay)
                continue

            except ChromeException as e:
                # Специфичные ошибки Chrome
                logger.error(
                    "Ошибка Chrome при подключению к DevTools Protocol (%s): %s",
                    self._dev_url,
                    e,
                )
                if attempt < max_attempts - 1:
                    time.sleep(attempt_delay)
                continue

            except Exception as e:
                # Любые другие непредвиденные ошибки
                logger.error(
                    "Непредвиденная ошибка при подключении к Chrome DevTools Protocol (%s): %s",
                    self._dev_url,
                    e,
                    exc_info=True,
                )
                if attempt < max_attempts - 1:
                    time.sleep(attempt_delay)
                continue

        # Все попытки исчерпаны
        logger.error("Все %d попыток подключения исчерпаны", max_attempts)
        return False

    def start(self) -> None:
        """Открывает браузер, создаёт новую вкладку, настраивает удалённый интерфейс.

        Raises:
            ChromeException: Если не удалось подключиться к Chrome.

        Примечание:
            Добавлена задержка после запуска Chrome для стабильного подключения.
            При параллельном запуске нескольких браузеров может потребоваться больше времени.
        """
        try:
            # Открываем браузер
            self._chrome_browser = ChromeBrowser(self._chrome_options)

            # Валидируем порт перед использованием
            remote_port = _validate_remote_port(self._chrome_browser.remote_port)
            self._dev_url = f"http://127.0.0.1:{remote_port}"

            # Начальная задержка для запуска Chrome (даём время на старт)
            # При параллельном запуске нескольких браузеров увеличиваем задержку
            logger.debug("Ожидание запуска Chrome (%.1f сек)...", CHROME_STARTUP_DELAY)
            time.sleep(CHROME_STARTUP_DELAY)

            # Проверка доступности порта перед подключением с повторными попытками
            max_port_check_attempts = 5
            port_check_delay = 1.0

            for attempt in range(max_port_check_attempts):
                if _check_port_available(remote_port, timeout=2.0):
                    logger.debug("Порт %d доступен для подключения", remote_port)
                    break

                if attempt < max_port_check_attempts - 1:
                    logger.warning(
                        "Порт %d недоступен (попытка %d/%d). Ожидание %.1f сек...",
                        remote_port,
                        attempt + 1,
                        max_port_check_attempts,
                        port_check_delay,
                    )
                    time.sleep(port_check_delay)
                else:
                    raise ChromeException(
                        f"Порт {remote_port} недоступен после {max_port_check_attempts} попыток. "
                        "Возможно, Chrome не запустился."
                    )

            # Подключаем браузер к CDP с проверкой результата
            if not self._connect_interface():
                raise ChromeException("Не удалось подключиться к Chrome DevTools Protocol")

            self._setup_tab()
            self._init_tab_monitor()
            
        except Exception:
            # При любой ошибке закрываем браузер для предотвращения утечки ресурсов
            if self._chrome_browser:
                logger.warning("Закрытие браузера из-за ошибки при запуске")
                self._chrome_browser.close()
            raise

    def _create_tab(self) -> pychrome.Tab:
        """Создаёт Chrome-вкладку с повторными попытками.

        Returns:
            Новый экземпляр pychrome.Tab.

        Raises:
            ChromeException: Если не удалось создать вкладку после всех попыток.

        Примечание:
            - Выполняется до 10 попыток создания вкладки
            - Задержка между попытками: 1.5 секунды
            - Увеличенный timeout для каждой попытки: 60 секунд
            - Детальное логирование для отладки
        """
        max_attempts = 10
        delay_seconds = 1.5

        for attempt in range(max_attempts):
            try:
                logger.debug(
                    "Попытка %d/%d: создание вкладки...", attempt + 1, max_attempts
                )
                # requests.put не принимает параметр json=True, используем данные запроса
                resp = requests.put(
                    "%s/json/new" % (self._dev_url),
                    json={},  # Пустой JSON для создания вкладки
                    timeout=60,  # Увеличенный timeout для стабильности
                )
                resp.raise_for_status()
                logger.debug("Вкладка успешно создана")
                return pychrome.Tab(**resp.json())

            except (RequestException, ValueError, KeyError) as e:
                if attempt < max_attempts - 1:
                    logger.warning(
                        "Не удалось создать вкладку (попытка %d): %s. Повторная попытка через %.1f сек...",
                        attempt + 1,
                        e,
                        delay_seconds,
                    )
                    time.sleep(delay_seconds)
                else:
                    raise ChromeException(
                        f"Не удалось создать вкладку после {max_attempts} попыток: {e}"
                    )

        raise ChromeException("Не удалось создать вкладку")

    def _close_tab(self, tab: pychrome.Tab) -> None:
        """Закрывает Chrome-вкладку."""
        if tab.status == pychrome.Tab.status_started:
            tab.stop()
        requests.put("%s/json/close/%s" % (self._dev_url, tab.id))

    def _setup_tab(self) -> None:
        """Скрывает следы webdriver, включает перехват запросов/ответов, исправляет UA.

        Примечание:
            Метод устанавливает пользовательский агент, скрывает признаки webdriver
            и настраивает перехват сетевых запросов для последующей обработки.
        """
        # Исправляем user agent для headless браузера
        original_useragent = self.execute_script("navigator.userAgent")

        # Проверяем успешность получения user agent
        if original_useragent:
            fixed_useragent = original_useragent.replace("Headless", "")
        else:
            # Запасной вариант: стандартный user agent Chrome
            fixed_useragent = (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            logger.warning(
                "Не удалось получить user agent, используется запасной вариант"
            )

        self._chrome_tab.Network.setUserAgentOverride(userAgent=fixed_useragent)

        # Скрываем следы webdriver
        self.add_start_script(r"""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        def responseReceived(**kwargs) -> None:
            """Собирает ответы."""
            # Извлекаем response до изменения kwargs
            response = kwargs["response"]
            request_id = kwargs["requestId"]
            resource_type = kwargs.get("type")

            # Сохраняем метаданные ответа
            response["meta"] = {k: v for k, v in kwargs.items() if k != "response"}

            # Пропускаем preflight запросы
            if resource_type == "Preflight":
                return

            # Добавляем ответ атомарно под блокировкой
            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response["request"] = request
                    request["response"] = response

                    # Помещаем ответ в очередь атомарно, чтобы избежать гонки
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
            response = {
                "status": -1,
                "statusText": status_text,
            }

            # Унифицированный паттерн блокировки: всё под одним локом
            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response["request"] = request
                    request["response"] = response
                    request_url = request["url"]

                    # Если ответ нужен, помещаем его в очередь атомарно
                    if request_url:
                        for pattern in self._response_patterns:
                            if re.match(pattern, request_url):
                                self._response_queues[pattern].put(response)

        def requestWillBeSent(**kwargs) -> None:
            request = kwargs.pop("request")
            request["meta"] = kwargs
            request_id = kwargs["requestId"]
            resource_type = kwargs.get("type")

            # Пропускаем preflight запросы
            if resource_type == "Preflight":
                return

            # Добавляем запрос
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
        # Используем threading.Event для потокобезопасного флага
        tab_detached = threading.Event()

        def monitor_tab() -> None:
            """V8 OOM может убить вкладку Chrome и сохранить websocket функциональным,
            как будто ничего не случилось, поэтому мы мониторим индексную страницу вкладок
            и проверяем, жива ли наша вкладка."""
            while not self._chrome_tab._stopped.is_set():
                try:
                    # requests.get не принимает параметр json=True, убираем его
                    ret = requests.get("%s/json" % self._dev_url, timeout=5)
                    tab_found = any(
                        x["id"] == self._chrome_tab.id for x in ret.json()
                    )
                    if not tab_found:
                        tab_detached.set()
                        self._chrome_tab._stopped.set()

                    self._chrome_tab._stopped.wait(0.5)
                except (ConnectionError, RequestException, TimeoutError):
                    break
                except Exception:
                    # Ловим любые неожиданные исключения, чтобы мониторинг не падал
                    self._chrome_tab._stopped.wait(0.5)

        self._ping_thread = threading.Thread(target=monitor_tab, daemon=True)
        self._ping_thread.start()

        # Устанавливаем обёртку для отправки с повторным выбросом исключения
        original_send = self._chrome_tab._send

        def wrapped_send(*args, **kwargs) -> Any:
            try:
                return original_send(*args, **kwargs)
            except pychrome.UserAbortException:
                if tab_detached.is_set():
                    raise pychrome.RuntimeException("Вкладка была остановлена")
                else:
                    raise

        self._chrome_tab._send = wrapped_send

    def navigate(self, url: str, referer: str = "", timeout: int = 300) -> None:
        """Переходит по URL.

        Args:
            url: URL для навигации.
            referer: Установить заголовок referer.
            timeout: Таймаут ожидания в секундах (по умолчанию 5 минут).

        Raises:
            ChromeException: При ошибке навигации.
        """
        try:
            ret = self._chrome_tab.Page.navigate(
                url=url, _timeout=timeout, referrer=referer
            )
            error_message = ret.get("errorText", None)
            if error_message:
                raise ChromeException(error_message)
        except Exception as e:
            logger.error("Ошибка навигации по URL %s: %s", url, e)
            raise

    @wait_until_finished(timeout=300, throw_exception=False)
    def wait_response(self, response_pattern: str) -> Optional[Response]:
        """Ждёт указанный ответ с предопределённым паттерном.

        Args:
            response_pattern: Паттерн URL ответа.

        Returns:
            Ответ или None в случае таймаута (5 минут) или ошибки.
        """
        try:
            if self._chrome_tab is None:
                logger.warning("Chrome tab не инициализирован")
                return None

            if self._chrome_tab._stopped.is_set():
                logger.warning("Вкладка Chrome была остановлена")
                return None

            return self._response_queues[response_pattern].get(block=False)
        except queue.Empty:
            return None
        except KeyError:
            logger.warning("Неизвестный паттерн ответа: %s", response_pattern)
            return None
        except Exception as e:
            logger.error("Ошибка при ожидании ответа: %s", e)
            return None

    def clear_requests(self) -> None:
        """Очищает все собранные запросы и очереди ответов."""
        with self._requests_lock:
            self._requests = {}
        # Очищаем очереди ответов для предотвращения утечки памяти
        for pattern_queue in self._response_queues.values():
            while not pattern_queue.empty():
                try:
                    pattern_queue.get_nowait()
                except queue.Empty:
                    break

    @wait_until_finished(timeout=60, throw_exception=False)
    def get_response_body(self, response: Response) -> str:
        """Получает тело ответа.

        Args:
            response: Ответ.

        Returns:
            Тело ответа или пустую строку при ошибке.

        Примечание:
            Функция гарантирует очистку временных данных для предотвращения утечки памяти.
        """
        response_data: Optional[Dict[str, Any]] = None
        response_body: str = ""

        try:
            # Проверяем наличие необходимых полей
            if "meta" not in response:
                logger.warning("Отсутствует поле meta в response")
                return ""

            if "requestId" not in response["meta"]:
                logger.warning("Отсутствует поле requestId в response.meta")
                return ""

            request_id = response["meta"]["requestId"]

            # Получаем тело ответа
            response_data = self._chrome_tab.call_method(
                "Network.getResponseBody", requestId=request_id
            )

            if not response_data:
                logger.debug("Тело ответа пустое для requestId: %s", request_id)
                return ""

            # Декодируем base64 если необходимо
            if response_data.get("base64Encoded"):
                try:
                    encoded_body = response_data.get("body", "")
                    if encoded_body:
                        decoded_bytes = base64.b64decode(encoded_body)
                        response_body = decoded_bytes.decode("utf-8")
                    else:
                        response_body = ""
                except (UnicodeDecodeError, ValueError) as decode_error:
                    logger.warning(
                        "Ошибка декодирования тела ответа (requestId: %s): %s",
                        request_id,
                        decode_error,
                    )
                    response_body = ""
            else:
                response_body = response_data.get("body", "")

            # Сохраняем тело в response для удобства
            response["body"] = response_body
            return response_body

        except pychrome.CallMethodException as e:
            # Ошибка вызова метода CDP
            logger.debug("CallMethodException при получении тела ответа: %s", e)
            return ""

        except KeyError as e:
            # Отсутствует необходимое поле
            logger.warning(
                "Отсутствует поле в response при получении тела ответа: %s", e
            )
            return ""

        except Exception as e:
            # Любая другая ошибка
            logger.warning("Непредвиденная ошибка при получении тела ответа: %s", e)
            return ""

        finally:
            # Гарантированная очистка временных данных для предотвращения утечки памяти
            if response_data is not None:
                # Явно удаляем большие данные из памяти
                response_data.pop("body", None)
                # Обнуляем ссылку для помощи сборщику мусора
                response_data = None

    @wait_until_finished(timeout=None, throw_exception=False)
    def get_responses(self) -> List[Response]:
        """Получает собранные ответы.

        Returns:
            Список всех ответов с полем 'response'.
        """
        with self._requests_lock:
            return [x["response"] for x in self._requests.values() if "response" in x]

    def get_requests(self) -> List[Request]:
        """Получает записанные запросы.

        Returns:
            Список всех записанных запросов.
        """
        with self._requests_lock:
            return [*self._requests.values()]

    def get_document(self, full: bool = True) -> DOMNode:
        """Получает DOM-дерево документа.

        Args:
            full: Флаг, возвращать полное DOM или только корень.

        Returns:
            Корневой DOM-узел.
        """
        tree = self._chrome_tab.DOM.getDocument(depth=-1 if full else 1)
        return DOMNode(**tree["root"])

    def add_start_script(self, source: str) -> None:
        """Добавляет скрипт, выполняющийся на каждой новой странице.

        Args:
            source: Текст скрипта.

        Raises:
            ValueError: Если скрипт не прошёл валидацию безопасности.

        Примечание безопасности:
            Перед выполнением скрипт проходит проверку на:
            - Тип данных (должен быть строкой)
            - Максимальную длину
            - Наличие опасных паттернов (eval, Function, document.write)
        """
        # Валидация скрипта на безопасность
        is_valid, error_msg = _validate_js_code(source)
        if not is_valid:
            logger.error("Валидация скрипта не пройдена: %s", error_msg)
            raise ValueError(f"Небезопасный JavaScript код: {error_msg}")

        self._chrome_tab.Page.addScriptToEvaluateOnNewDocument(source=source)

    def add_blocked_requests(self, urls: List[str]) -> bool:
        """Блокирует нежелательные запросы.

        Args:
            urls: Шаблоны URL для блокировки. Поддерживаются подстановочные знаки ('*').

        Returns:
            `True` при успехе, `False` при неудаче.
        """
        try:
            self._chrome_tab.Network.setBlockedURLs(urls=urls)
            return True
        except pychrome.CallMethodException:
            # Похоже, старая версия браузера, пропускаем
            return False

    def execute_script(self, expression: str) -> Any:
        """Выполняет скрипт.

        Args:
            expression: Текст выражения.

        Returns:
            Значение результата или None при ошибке.

        Raises:
            ValueError: Если выражение не прошло валидацию безопасности.

        Примечание безопасности:
            Перед выполнением выражение проходит проверку на:
            - Тип данных (должен быть строкой)
            - Максимальную длину
            - Наличие опасных паттернов (eval, Function, document.write)
        """
        # Валидация выражения на безопасность
        is_valid, error_msg = _validate_js_code(expression)
        if not is_valid:
            logger.error("Валидация выражения не пройдена: %s", error_msg)
            raise ValueError(f"Небезопасный JavaScript код: {error_msg}")

        try:
            eval_result = self._chrome_tab.Runtime.evaluate(
                expression=expression, returnByValue=True
            )
            return eval_result["result"].get("value", None)
        except Exception as e:
            logger.warning("Ошибка при выполнении скрипта: %s", e)
            return None

    def perform_click(self, dom_node: DOMNode, timeout: Optional[int] = None) -> None:
        """Выполняет клик мыши на DOM-узле.

        Args:
            dom_node: Элемент DOMNode.
            timeout: Таймаут операции в секундах (опционально).
        """
        try:
            resolved_node = self._chrome_tab.DOM.resolveNode(
                backendNodeId=dom_node.backend_id, _timeout=timeout
            )
            object_id = resolved_node["object"]["objectId"]
            self._chrome_tab.Runtime.callFunctionOn(
                objectId=object_id,
                functionDeclaration="""
                    (function() {
                        this.scrollIntoView({ block: "center", behavior: "instant" });
                        this.click();
                    })
                """,
            )
        except Exception as e:
            logger.error("Ошибка при выполнении клика: %s", e)

    def wait(self, timeout: Optional[float] = None) -> None:
        """Ожидает указанное время.

        Args:
            timeout: Время ожидания в секундах.
        """
        self._chrome_tab.wait(timeout)

    def stop(self) -> None:
        """Закрывает браузер, отключает интерфейс.

        Примечание:
            Функция гарантирует очистку всех ресурсов даже при ошибках.
        """
        try:
            # Закрываем вкладку
            if self._chrome_tab is not None:
                try:
                    self._close_tab(self._chrome_tab)
                except (pychrome.RuntimeException, RequestException) as e:
                    logger.debug("Ошибка при закрытии вкладки: %s", e)

            # Закрываем браузер
            if self._chrome_browser is not None:
                try:
                    self._chrome_browser.close()
                except Exception as e:
                    logger.debug("Ошибка при закрытии браузера: %s", e)

            # Очищаем запросы и очереди
            self.clear_requests()
            self._response_queues = {}

        except Exception as e:
            logger.error("Непредвиденная ошибка при остановке ChromeRemote: %s", e)

    def __enter__(self) -> ChromeRemote:
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.stop()

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return f"{classname}(options={self._chrome_options!r}, response_patterns={self._response_patterns!r})"
