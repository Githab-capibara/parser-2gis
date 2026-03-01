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
from .browser import ChromeBrowser
from .dom import DOMNode
from .exceptions import ChromeException
from .patches import patch_all

if TYPE_CHECKING:
    from .options import ChromeOptions

    Request = Dict[str, Any]
    Response = Dict[str, Any]

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

    @wait_until_finished(timeout=60)
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
        except (RequestException, WebSocketException):
            return False

    def start(self) -> None:
        """Открывает браузер, создаёт новую вкладку, настраивает удалённый интерфейс."""
        # Открываем браузер
        self._chrome_browser = ChromeBrowser(self._chrome_options)
        self._dev_url = f'http://127.0.0.1:{self._chrome_browser.remote_port}'

        # Подключаем браузер к CDP
        self._connect_interface()
        self._setup_tab()
        self._init_tab_monitor()

    def _create_tab(self) -> pychrome.Tab:
        """Создаёт Chrome-вкладку."""
        resp = requests.put('%s/json/new' % (self._dev_url), json=True)         
        return pychrome.Tab(**resp.json())

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
            response = kwargs.pop('response')
            response['meta'] = kwargs
            request_id = kwargs['requestId']
            resource_type = kwargs.get('type')

            # Пропускаем preflight запросы
            if resource_type == 'Preflight':
                return

            # Добавляем ответ
            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response['request'] = request
                    request['response'] = response

            # Если ответ нужен, помещаем его в очередь
            for pattern in self._response_patterns:
                if re.match(pattern, response['url']):
                    self._response_queues[pattern].put(response)

        def loadingFailed(**kwargs) -> None:
            error_text = kwargs.get('errorText')
            blocked_reason = kwargs.get('blockedReason')
            status_text = ''

            if error_text:
                status_text = 'error: %s' % error_text
            if blocked_reason:
                if status_text:
                    status_text += ', '
                status_text += 'blocked_reason: %s' % blocked_reason

            request_id = kwargs.get('requestId')
            response = {
                'status': -1,
                'statusText': status_text,
            }

            # Добавляем ответ
            request_url = None
            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response['request'] = request
                    request['response'] = response
                    request_url = request['url']

            if request_url:
                # Если ответ нужен, помещаем его в очередь
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
        tab_detached = False

        def monitor_tab() -> None:
            """V8 OOM может уронить вкладку Chrome и сохранить websocket функциональным,
            как будто ничего не случилось, поэтому мы мониторим индексную страницу вкладок
            и проверяем, жива ли наша вкладка."""
            while not self._chrome_tab._stopped.is_set():
                try:
                    ret = requests.get('%s/json' % self._dev_url, json=True)
                    if not any(x['id'] == self._chrome_tab.id for x in ret.json()):
                        nonlocal tab_detached
                        tab_detached = True
                        self._chrome_tab._stopped.set()

                    self._chrome_tab._stopped.wait(0.5)
                except ConnectionError:
                    break

        self._ping_thread = threading.Thread(target=monitor_tab, daemon=True)
        self._ping_thread.start()

        def get_send_with_reraise() -> Callable[..., Any]:
            """Повторно выбрасывает "Tab has been stopped" вместо `UserAbortException`,
            если обнаружена отсоединение вкладки."""
            original_send = self._chrome_tab._send

            def wrapped_send(*args, **kwargs) -> Any:
                try:
                    return original_send(*args, **kwargs)
                except pychrome.UserAbortException:
                    if tab_detached:
                        raise pychrome.RuntimeException('Tab has been stopped')
                    else:
                        raise
            return wrapped_send

        self._chrome_tab._send = get_send_with_reraise()

    def navigate(self, url: str, referer: str = '', timeout: int = 60) -> None:
        """Переходит по URL.

        Args:
            referer: Установить заголовок referer.
            timeout: Таймаут ожидания.

        Returns:
            None при успехе, сообщение об ошибке при неудаче.
        """
        ret = self._chrome_tab.Page.navigate(url=url, _timeout=timeout, referrer=referer)
        error_message = ret.get('errorText', None)
        if error_message:
            raise ChromeException(error_message)

    @wait_until_finished(timeout=30, throw_exception=False)
    def wait_response(self, response_pattern: str) -> Response | None:
        """Ждёт указанный ответ с предопределённым паттерном.

        Args:
            response_pattern: Паттерн URL ответа.

        Returns:
            Ответ или None в случае таймаута.
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

    @wait_until_finished(timeout=15, throw_exception=False)
    def get_response_body(self, response: Response) -> str:
        """Получает тело ответа.

        Args:
            response: Ответ.
        """
        try:
            request_id = response['meta']['requestId']
            response_data = self._chrome_tab.call_method('Network.getResponseBody',
                                                         requestId=request_id)
            if response_data['base64Encoded']:
                response_data['body'] = base64.b64decode(response_data['body']).decode('utf-8')

            response_body = response_data['body']
            response['body'] = response_body
            return response_body
        except pychrome.CallMethodException:
            # Тело ответа не найдено
            return ''

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
