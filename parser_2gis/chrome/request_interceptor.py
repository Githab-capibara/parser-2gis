"""Модуль перехвата HTTP запросов для Chrome.

Предоставляет класс RequestInterceptor для:
- Перехвата запросов и ответов
- Фильтрации по паттернам
- Управления очередями ответов

ISSUE-003: Выделено из ChromeRemote для соблюдения SRP.
"""

from __future__ import annotations

import queue
import re
import threading
from typing import TYPE_CHECKING, Any

from parser_2gis.logger.logger import logger as app_logger

if TYPE_CHECKING:
    import pychrome

# Type aliases
Request = dict[str, Any]
Response = dict[str, Any]


class RequestInterceptor:
    """Перехватчик HTTP запросов для Chrome.

    Отвечает за:
    - Регистрацию обработчиков событий Network
    - Фильтрацию запросов по паттернам
    - Управление очередями ответов
    - Сбор и корреляцию запросов/ответов

    ISSUE-003: Выделено из ChromeRemote для соблюдения SRP.
    """

    def __init__(self) -> None:
        """Инициализирует перехватчик запросов."""
        self._requests: dict[str, Request] = {}
        self._requests_lock = threading.RLock()
        self._response_patterns: list[str] = []
        self._response_queues: dict[str, queue.Queue] = {}

    def register_response_pattern(self, pattern: str) -> None:
        """Регистрирует паттерн для ожидания ответов.

        Args:
            pattern: Regex паттерн для URL.

        """
        with self._requests_lock:
            if pattern not in self._response_patterns:
                self._response_patterns.append(pattern)
                self._response_queues[pattern] = queue.Queue()
                app_logger.debug("Зарегистрирован паттерн ответа: %s", pattern)

    def unregister_response_pattern(self, pattern: str) -> None:
        """Удаляет паттерн и соответствующую очередь.

        Args:
            pattern: Паттерн для удаления.

        """
        with self._requests_lock:
            if pattern in self._response_patterns:
                self._response_patterns.remove(pattern)
                if pattern in self._response_queues:
                    # Очищаем очередь перед удалением с защитой от бесконечного цикла
                    queue_to_clean = self._response_queues[pattern]
                    max_iterations = 10000  # Защита от бесконечного цикла при высокой нагрузке
                    iterations = 0
                    while not queue_to_clean.empty() and iterations < max_iterations:
                        try:
                            queue_to_clean.get_nowait()
                        except queue.Empty:
                            break
                        iterations += 1
                    if iterations >= max_iterations:
                        app_logger.warning(
                            "Достигнут лимит итераций очистки очереди для паттерна %s", pattern
                        )
                    del self._response_queues[pattern]
                app_logger.debug("Удалён паттерн ответа: %s", pattern)

    def get_response(self, pattern: str, block: bool = False) -> Response | None:
        """Получает ответ по паттерну.

        Args:
            pattern: Паттерн для поиска.
            block: Блокировать ли ожидание.

        Returns:
            Response или None если не найден.

        """
        with self._requests_lock:
            if pattern not in self._response_queues:
                app_logger.error("Паттерн ответа не найден: %s", pattern)
                return None

            try:
                return self._response_queues[pattern].get(block=block)
            except queue.Empty:
                return None

    def clear_requests(self) -> None:
        """Очищает все собранные запросы и очереди ответов."""
        with self._requests_lock:
            self._requests.clear()
            for pattern_queue in self._response_queues.values():
                while not pattern_queue.empty():
                    try:
                        pattern_queue.get_nowait()
                    except queue.Empty:
                        break

    def get_request(self, request_id: str) -> Request | None:
        """Получает запрос по ID.

        Args:
            request_id: ID запроса.

        Returns:
            Request или None если не найден.

        """
        with self._requests_lock:
            return self._requests.get(request_id)

    def setup_network_interceptors(self, chrome_tab: "pychrome.Tab") -> None:
        """Устанавливает перехватчики событий Network на вкладку.

        Args:
            chrome_tab: Вкладка Chrome для настройки.

        """
        if chrome_tab is None:
            app_logger.error("chrome_tab is None в setup_network_interceptors")
            return

        def responseReceived(**kwargs: Any) -> None:
            """Обработчик события получения ответа.

            Args:
                **kwargs: Параметры события (response, requestId, type).

            """
            response: Response = kwargs["response"]
            request_id: str = kwargs["requestId"]
            resource_type = kwargs.get("type")

            response["meta"] = {k: v for k, v in kwargs.items() if k != "response"}

            # Игнорируем Preflight запросы
            if resource_type == "Preflight":
                return

            with self._requests_lock:
                if request_id in self._requests:
                    request = self._requests[request_id]
                    response["request"] = request
                    request["response"] = response

                    # Отправляем в очереди подходящих паттернов
                    for pattern in self._response_patterns:
                        if re.match(pattern, response["url"]):
                            self._response_queues[pattern].put(response)

        def loadingFailed(**kwargs: Any) -> None:
            """Обработчик события неудачной загрузки.

            Args:
                **kwargs: Параметры события (errorText, blockedReason, requestId).

            """
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
            response: Response = {"status": -1, "statusText": status_text}

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

        def requestWillBeSent(**kwargs: Any) -> None:
            """Обработчик события отправки запроса.

            Args:
                **kwargs: Параметры события (request, requestId, type).

            Note:
                Игнорирует Preflight запросы (OPTIONS).
                Фильтрует чувствительные заголовки Authorization и Cookie.

            """
            request: Request = kwargs.pop("request")
            # Фильтрация чувствительных заголовков перед сохранением
            if "headers" in request and isinstance(request["headers"], dict):
                sensitive_headers = ("Authorization", "Cookie", "Set-Cookie", "Proxy-Authorization")
                for header_name in sensitive_headers:
                    request["headers"].pop(header_name, None)
                    # Также удаём варианты с нижним регистром
                    request["headers"].pop(header_name.lower(), None)
            request["meta"] = kwargs
            request_id: str = kwargs["requestId"]
            resource_type = kwargs.get("type")

            # Игнорируем Preflight запросы
            if resource_type == "Preflight":
                return

            with self._requests_lock:
                self._requests[request_id] = request

        # Регистрируем обработчики на вкладке
        chrome_tab.Network.responseReceived = responseReceived  # type: ignore[attr-defined]
        chrome_tab.Network.loadingFailed = loadingFailed  # type: ignore[attr-defined]
        chrome_tab.Network.requestWillBeSent = requestWillBeSent  # type: ignore[attr-defined]

        # Включаем события Network
        chrome_tab.Network.enable()  # type: ignore[attr-defined]

    def get_stats(self) -> dict[str, int]:
        """Возвращает статистику перехватчика.

        Returns:
            Словарь со статистикой (количество запросов, паттернов, очередей).

        """
        with self._requests_lock:
            return {
                "pending_requests": len(self._requests),
                "registered_patterns": len(self._response_patterns),
                "response_queues": len(self._response_queues),
            }


__all__ = ["RequestInterceptor", "Request", "Response"]
