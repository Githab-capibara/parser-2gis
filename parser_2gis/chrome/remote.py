from __future__ import annotations

import base64
import queue
import re
import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

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
    """
    if not isinstance(port, int):
        raise ValueError(f"remote_port должен быть integer, получен {type(port).__name__}")
    if port < 1024 or port > 65535:
        raise ValueError(f"remote_port должен быть в диапазоне 1024-65535, получен {port}")
    return port

# Применяем все пользовательские патчи
patch_all()


class ChromeRemote:
    """Обёртка для Chrome DevTools Protocol Interface.

    Args:
        chrome_options: Параметры ChromeOptions.
        response_patterns: Паттерны URL ответов для перехвата.
    """
    def __init__(self, chrome_options: ChromeOptions, response_patterns: list[str]) -> None:
        self._chrome_options: ChromeOptions = chrome_options
        self._chrome_browser: ChromeBrowser
        self._chrome_interface: pychrome.Browser
        self._chrome_tab: pychrome.Tab
        self._response_patterns: list[str] = response_patterns
        self._response_queues: dict[str, queue.Queue[Response]] = {x: queue.Queue() for x in response_patterns}
        self._requests: dict[str, Request] = {}  # _requests[request_id] = <Request>
        self._requests_lock = threading.Lock()

    @wait_until_finished(timeout=300)
    def _connect_interface(self) -> bool:
        """Устанавливает соединение с Chrome и открывает новую вкладку.

        Returns:
            `True` при успехе, `False` при неудаче.
        """
        try:
            self._chrome_interface = pychrome.Browser(url=self._dev_url)
            self._chrome_tab = self._create_tab()
            self._chrome_tab.start()
            return True
        except (RequestException, WebSocketException, ChromeException) as e:
            logger.error('Ошибка подключения к Chrome DevTools Protocol: %s', e)
            return False

    def start(self) -> None:
        """Открывает браузер, создаёт новую вкладку, настраивает удалённый интерфейс.

        Raises:
            ChromeException: Если не удалось подключиться к Chrome.
        """
        # Открываем браузер
        self._chrome_browser = ChromeBrowser(self._chrome_options)

        # Валидируем порт перед использованием
        remote_port = _validate_remote_port(self._chrome_browser.remote_port)
        self._dev_url = f'http://127.0.0.1:{remote_port}'

        # Подключаем браузер к CDP с проверкой результата
        if not self._connect_interface():
            self._chrome_browser.close()
            raise ChromeException("Не удалось подключиться к Chrome DevTools Protocol")

        self._setup_tab()
        self._init_tab_monitor()

    def _create_tab(self) -> pychrome.Tab:
        """Создаёт Chrome-вкладку.
        
        Returns:
            Новый экземпляр pychrome.Tab.
            
        Raises:
            ChromeException: Если не удалось создать вкладку.
        """
        try:
            resp = requests.put('%s/json/new' % (self._dev_url), json=True, timeout=30)
            resp.raise_for_status()
            return pychrome.Tab(**resp.json())
        except (RequestException, ValueError, KeyError) as e:
            raise ChromeException(f'Не удалось создать вкладку: {e}')

    def _close_tab(self, tab: pychrome.Tab) -> None:
        """Закрывает Chrome-вкладку."""
        if tab.status == pychrome.Tab.status_started:
            tab.stop()
        requests.put('%s/json/close/%s' % (self._dev_url, tab.id))

    def _setup_tab(self) -> None:
        """Скрывает следы webdriver, включает перехват запросов/ответов, исправляет UA."""
        # Исправляем user agent для headless браузера
        original_useragent = self.execute_script('navigator.userAgent')
        fixed_useragent = original_useragent.replace('Headless', '')
        self._chrome_tab.Network.setUserAgentOverride(userAgent=fixed_useragent)

        # Скрываем следы webdriver
        self.add_start_script(r'''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        ''')

        def responseReceived(**kwargs) -> None:
            """Собирает ответы."""
            # Извлекаем response до изменения kwargs
            response = kwargs['response']
            request_id = kwargs['requestId']
            resource_type = kwargs.get('type')
            
            # Сохраняем метаданные ответа
            response['meta'] = {k: v for k, v in kwargs.items() if k != 'response'}

            # Пропускаем preflight запросы
            if resource_type == 'Preflight':
                return

            # Добавляем ответ атомарно под блокировкой
            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response['request'] = request
                    request['response'] = response

                    # Помещаем ответ в очередь атомарно, чтобы избежать гонки
                    for pattern in self._response_patterns:
                        if re.match(pattern, response['url']):
                            self._response_queues[pattern].put(response)

        def loadingFailed(**kwargs) -> None:
            """Обрабатывает неудачные загрузки запросов."""
            error_text = kwargs.get('errorText')
            blocked_reason = kwargs.get('blockedReason')
            status_text = ''

            if error_text:
                status_text = f'error: {error_text}'
            if blocked_reason:
                if status_text:
                    status_text += ', '
                status_text += f'blocked_reason: {blocked_reason}'

            request_id = kwargs.get('requestId')
            response = {
                'status': -1,
                'statusText': status_text,
            }

            # Унифицированный паттерн блокировки: всё под одним локом
            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response['request'] = request
                    request['response'] = response
                    request_url = request['url']

                    # Если ответ нужен, помещаем его в очередь атомарно
                    if request_url:
                        for pattern in self._response_patterns:
                            if re.match(pattern, request_url):
                                self._response_queues[pattern].put(response)

        def requestWillBeSent(**kwargs) -> None:
            request = kwargs.pop('request')
            request['meta'] = kwargs
            request_id = kwargs['requestId']
            resource_type = kwargs.get('type')

            # Пропускаем preflight запросы
            if resource_type == 'Preflight':
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
        # Используем list для возможности изменения значения в замыкании
        tab_detached = [False]
        tab_detached_lock = threading.Lock()

        def monitor_tab() -> None:
            """V8 OOM может убить вкладку Chrome и сохранить websocket функциональным,
            как будто ничего не случилось, поэтому мы мониторим индексную страницу вкладок
            и проверяем, жива ли наша вкладка."""
            while not self._chrome_tab._stopped.is_set():
                try:
                    ret = requests.get('%s/json' % self._dev_url, json=True, timeout=5)
                    with tab_detached_lock:
                        tab_found = any(x['id'] == self._chrome_tab.id for x in ret.json())
                        if not tab_found:
                            tab_detached[0] = True
                            self._chrome_tab._stopped.set()

                    self._chrome_tab._stopped.wait(0.5)
                except (ConnectionError, RequestException, TimeoutError):
                    break
                except Exception:
                    # Ловим любые неожиданные исключения, чтобы мониторинг не падал
                    self._chrome_tab._stopped.wait(0.5)

        self._ping_thread = threading.Thread(target=monitor_tab, daemon=True)
        self._ping_thread.start()

        def get_send_with_reraise() -> Callable[..., Any]:
            """Повторно выбрасывает "Вкладка была остановлена" вместо `UserAbortException`,
            если обнаружена отсоединение вкладки."""
            original_send = self._chrome_tab._send

            def wrapped_send(*args, **kwargs) -> Any:
                try:
                    return original_send(*args, **kwargs)
                except pychrome.UserAbortException:
                    with tab_detached_lock:
                        if tab_detached[0]:
                            raise pychrome.RuntimeException('Вкладка была остановлена')
                        else:
                            raise
            return wrapped_send

        self._chrome_tab._send = get_send_with_reraise()

    def navigate(self, url: str, referer: str = '', timeout: int = 300) -> None:
        """Переходит по URL.

        Args:
            url: URL для навигации.
            referer: Установить заголовок referer.
            timeout: Таймаут ожидания в секундах (по умолчанию 5 минут).

        Raises:
            ChromeException: При ошибке навигации.
        """
        ret = self._chrome_tab.Page.navigate(url=url, _timeout=timeout, referrer=referer)
        error_message = ret.get('errorText', None)
        if error_message:
            raise ChromeException(error_message)

    @wait_until_finished(timeout=300, throw_exception=False)
    def wait_response(self, response_pattern: str) -> Response | None:
        """Ждёт указанный ответ с предопределённым паттерном.

        Args:
            response_pattern: Паттерн URL ответа.

        Returns:
            Ответ или None в случае таймаута (5 минут).
        """
        try:
            if self._chrome_tab._stopped.is_set():
                raise pychrome.RuntimeException('Tab has been stopped')
            return self._response_queues[response_pattern].get(block=False)
        except queue.Empty:
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
        """
        response_data = None
        try:
            request_id = response['meta']['requestId']
            response_data = self._chrome_tab.call_method('Network.getResponseBody',
                                                         requestId=request_id)
            if response_data.get('base64Encoded'):
                response_data['body'] = base64.b64decode(response_data['body']).decode('utf-8')

            response_body = response_data.get('body', '')
            response['body'] = response_body
            return response_body
        except (pychrome.CallMethodException, KeyError, UnicodeDecodeError, TypeError):
            # Тело ответа не найдено или ошибка декодирования
            return ''
        finally:
            # Гарантированная очистка ссылки на тело для предотвращения утечки памяти
            if response_data:
                response_data.pop('body', None)
            # Очищаем ссылку на response_data для помощи сборщику мусора
            response_data = None

    @wait_until_finished(timeout=None, throw_exception=False)
    def get_responses(self) -> list[Response]:
        """Получает собранные ответы."""
        with self._requests_lock:
            return [x['response'] for x in self._requests.values() if 'response' in x]

    def get_requests(self) -> list[Request]:
        """Получает записанные запросы."""
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
        return DOMNode(**tree['root'])

    def add_start_script(self, source: str) -> None:
        """Добавляет скрипт, выполняющийся на каждой новой странице.

        Args:
            source: Текст скрипта.
        """
        self._chrome_tab.Page.addScriptToEvaluateOnNewDocument(source=source)

    def add_blocked_requests(self, urls: list[str]) -> bool:
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
            Значение результата.
        """
        eval_result = self._chrome_tab.Runtime.evaluate(expression=expression,
                                                        returnByValue=True)
        return eval_result['result'].get('value', None)

    def perform_click(self, dom_node: DOMNode, timeout: Optional[int] = None) -> None:
        """Выполняет клик мыши на DOM-узле.

        Args:
            dom_node: Элемент DOMNode.
        """
        resolved_node = self._chrome_tab.DOM.resolveNode(backendNodeId=dom_node.backend_id, _timeout=timeout)
        object_id = resolved_node['object']['objectId']
        self._chrome_tab.Runtime.callFunctionOn(objectId=object_id, functionDeclaration='''
            (function() { this.scrollIntoView({ block: "center",  behavior: "instant" }); this.click(); })
        ''')

    def wait(self, timeout: float | None = None) -> None:
        """Ожидает `timeout` секунд."""
        self._chrome_tab.wait(timeout)

    def stop(self) -> None:
        """Закрывает браузер, отключает интерфейс."""
        # Закрываем вкладку и браузер
        if self._chrome_tab:
            try:
                self._close_tab(self._chrome_tab)
            except (pychrome.RuntimeException, RequestException):
                pass

        if self._chrome_browser:
            self._chrome_browser.close()

        self.clear_requests()
        self._response_queues = {}

    def __enter__(self) -> ChromeRemote:
        self.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self.stop()

    def __repr__(self) -> str:
        classname = self.__class__.__name__
        return f'{classname}(options={self._chrome_options!r}, response_patterns={self._response_patterns!r})'
