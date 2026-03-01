from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from ..exceptions import ChromeRuntimeException, ChromeUserAbortException
from ..logger import logger
from ..parser import get_parser
from ..writer import get_writer
from .runner import AbstractRunner

if TYPE_CHECKING:
    from ..config import Configuration


class GUIRunner(AbstractRunner, threading.Thread):
    """GUI-поток для запуска парсера.

    Args:
        urls: 2GIS URLs с элементами для сбора.
        output_path: Путь к результирующему файлу.
        format: Формат файла: `csv`, `xlsx` или `json`.
        config: Конфигурация.
    """
    def __init__(self, urls: list[str], output_path: str, format: str,
                 config: Configuration) -> None:
        AbstractRunner.__init__(self, urls, output_path, format, config)
        threading.Thread.__init__(self)

        self._parser = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Запускает поток."""
        self._cancelled = False
        logger.info('Парсинг запущен.')
        threading.Thread.start(self)

    def stop(self) -> None:
        """Останавливает поток."""
        if not self._started.is_set():  # type: ignore
            raise RuntimeError('start() is not called')

        if self._cancelled:
            return  # We can stop the thread only once

        self._cancelled = True
        self._stop_parser()

    def _stop_parser(self) -> None:
        """Закрывает парсер, если он был открыт."""
        with self._lock:
            if self._parser:
                self._parser.close()
                self._parser = None

    def run(self) -> None:
        """Точка активности потока."""
        with get_writer(self._output_path, self._format, self._config.writer) as writer:
            for url in self._urls:
                try:
                    logger.info(f'Парсинг ссылки {url}')
                    self._parser = get_parser(url,
                                              chrome_options=self._config.chrome,
                                              parser_options=self._config.parser)
                    assert self._parser

                    if not self._cancelled:
                        self._parser.parse(writer)
                except Exception as e:
                    if not self._cancelled:  # Не перехватываем преднамеренные исключения, вызванные остановкой парсера
                        if isinstance(e, ChromeRuntimeException) and str(e) == 'Tab has been stopped':
                            logger.error('Вкладка браузера была закрыта.')
                        elif isinstance(e, ChromeUserAbortException):
                            logger.error('Работа парсера прервана пользователем.')
                        else:
                            logger.error('Ошибка во время работы парсера.', exc_info=True)
                finally:
                    logger.info('Парсинг ссылки завершён.')
                    self._stop_parser()
                    if self._cancelled:
                        break

        logger.info('Парсинг завершён.')
