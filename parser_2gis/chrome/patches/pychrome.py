"""Патчи для библиотеки pychrome.

Предоставляет функцию patch_all() для применения всех патчей к pychrome.
"""

import json
import logging
import warnings

import pychrome.tab
import websocket

pychrome_logger = logging.getLogger("pychrome")


def patch_pychrome() -> None:
    """Патчит метод _recv_loop в pychrome.tab.Tab для улучшенной обработки исключений.

    Модифицирует поведение получения сообщений через websocket:
    - Обрабатывает таймауты websocket без прерывания цикла
    - Логирует websocket исключения при активном соединении
    - Корректно обрабатывает сообщения с id и method

    """

    def _recv_loop_patched(self) -> None:
        while not self._stopped.is_set():
            try:
                self._ws.settimeout(1)
                message_json = self._ws.recv()
                if not message_json:
                    continue
                message = json.loads(message_json)
            except websocket.WebSocketTimeoutException:
                continue
            except (websocket.WebSocketException, OSError):
                if not self._stopped.is_set():
                    pychrome_logger.error("websocket exception", exc_info=True)
                    self._stopped.set()
                return

            if self.debug:  # pragma: no cover
                pychrome_logger.debug("< RECV %s", message_json)

            if "method" in message:
                self.event_queue.put(message)

            elif "id" in message:
                if message["id"] in self.method_results:
                    self.method_results[message["id"]].put(message)
            else:  # pragma: no cover
                warnings.warn(f"unknown message: {message}", stacklevel=2)

    pychrome.tab.Tab._recv_loop = _recv_loop_patched
