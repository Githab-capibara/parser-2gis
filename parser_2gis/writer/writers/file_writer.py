from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, IO

from ...logger import logger

if TYPE_CHECKING:
    from ..options import WriterOptions


class FileWriter(ABC):
    """Базовый писатель."""
    def __init__(self, file_path: str, writer_options: WriterOptions) -> None:
        self._file_path = file_path
        self._options = writer_options

    @abstractmethod
    def write(self, catalog_doc: Any) -> None:
        """Записывает JSON-документ Catalog Item API, полученный парсером."""
        pass

    def _open_file(self, file_path: str, mode: str = 'r') -> IO[Any]:
        return open(file_path, mode, encoding=self._options.encoding,
                    newline='', errors='replace')

    def _check_catalog_doc(self, catalog_doc: Any, verbose: bool = True) -> bool:
        """Проверяет JSON-документ Catalog Item API на ошибки.

        Args:
            catalog_doc: JSON-документ Catalog Item API.
            verbose: Сообщать ли об найденных ошибках.

        Returns:
            `True`, если документ прошёл все проверки.
            `False`, если в документе найдены ошибки.
        """
        try:
            if not isinstance(catalog_doc, dict):
                if verbose:
                    logger.error('Сервер вернул некорректный документ (не dict).')
                return False

            if 'error' in catalog_doc['meta']:  # Найдена ошибка
                if verbose:
                    error_msg = catalog_doc['meta']['error'].get('message', None)
                    if error_msg:
                        logger.error('Сервер ответил ошибкой: %s', error_msg)
                    else:
                        logger.error('Сервер ответил неизвестной ошибкой.')

                return False

            if catalog_doc['meta'].get('code') != 200:
                if verbose:
                    logger.error('Сервер вернул код ответа: %s', catalog_doc['meta'].get('code'))
                return False
                
            if 'result' not in catalog_doc:
                if verbose:
                    logger.error('Сервер вернул документ без ключа "result".')
                return False
                
            if 'items' not in catalog_doc['result']:
                if verbose:
                    logger.error('Сервер вернул документ без ключа "items".')
                return False
                
            if not isinstance(catalog_doc['result']['items'], list):
                if verbose:
                    logger.error('Сервер вернул некорректный тип "items".')
                return False
                
            if len(catalog_doc['result']['items']) == 0:
                if verbose:
                    logger.error('Сервер вернул пустой список "items".')
                return False
                
            if not isinstance(catalog_doc['result']['items'][0], dict):
                if verbose:
                    logger.error('Сервер вернул некорректный тип элемента "items".')
                return False

            if len(catalog_doc['result']['items']) > 1 and verbose:
                logger.warning('Сервер вернул больше одного ответа.')

            return True
        except (KeyError, TypeError, AttributeError):
            if verbose:
                logger.error('Сервер ответил неизвестным документом.')
            return False

    def __enter__(self) -> FileWriter:
        self._file = self._open_file(self._file_path, 'w')
        return self

    def __exit__(self, *exc_info) -> None:
        # Проверяем наличие атрибута _file перед закрытием
        if hasattr(self, '_file'):
            self._file.close()

    def close(self) -> None:
        """Закрывает файл."""
        if hasattr(self, '_file'):
            self._file.close()
