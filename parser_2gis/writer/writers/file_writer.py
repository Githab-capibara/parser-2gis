from __future__ import annotations

from abc import ABC, abstractmethod
from typing import IO, TYPE_CHECKING, Any, Dict, Optional

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

    def _open_file(
        self,
        file_path: str,
        mode: str = "r",
        newline: Optional[str] = None,
        **kwargs: Any,
    ) -> IO[Any]:
        """Открывает файл с указанными параметрами.

        Args:
            file_path: Путь к файлу.
            mode: Режим открытия файла.
            newline: Параметр newline для текстовых файлов. Если None, не передается.
            **kwargs: Дополнительные параметры для open().

        Returns:
            Файловый объект.
        """
        open_kwargs: Dict[str, Any] = {
            "encoding": self._options.encoding,
            "errors": "replace",
        }
        if newline is not None:
            open_kwargs["newline"] = newline
        open_kwargs.update(kwargs)
        return open(file_path, mode, **open_kwargs)

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
                    logger.error("Сервер вернул некорректный документ (не dict).")
                return False

            # Безопасный доступ к meta
            meta = catalog_doc.get("meta", {})
            if not isinstance(meta, dict):
                if verbose:
                    logger.error("Сервер вернул некорректный документ (meta не dict).")
                return False

            # Проверка наличия ошибки в meta
            if meta.get("error"):
                if verbose:
                    error_data = meta.get("error", {})
                    error_msg = (
                        error_data.get("message")
                        if isinstance(error_data, dict)
                        else None
                    )
                    if error_msg:
                        logger.error("Сервер ответил ошибкой: %s", error_msg)
                    else:
                        logger.error("Сервер ответил неизвестной ошибкой.")
                return False

            # Проверка кода ответа
            if meta.get("code") != 200:
                if verbose:
                    logger.error("Сервер вернул код ответа: %s", meta.get("code"))
                return False

            # Проверка наличия result
            if "result" not in catalog_doc:
                if verbose:
                    logger.error('Сервер вернул документ без ключа "result".')
                return False

            result = catalog_doc.get("result", {})
            if not isinstance(result, dict):
                if verbose:
                    logger.error('Сервер вернул некорректный тип "result" (не dict).')
                return False

            # Проверка наличия items
            if "items" not in result:
                if verbose:
                    logger.error('Сервер вернул документ без ключа "items".')
                return False

            items = result.get("items", [])
            if not isinstance(items, list):
                if verbose:
                    logger.error('Сервер вернул некорректный тип "items" (не list).')
                return False

            if len(items) == 0:
                if verbose:
                    logger.error('Сервер вернул пустой список "items".')
                return False

            if not isinstance(items[0], dict):
                if verbose:
                    logger.error(
                        'Сервер вернул некорректный тип элемента "items" (не dict).'
                    )
                return False

            if len(items) > 1 and verbose:
                logger.warning("Сервер вернул больше одного ответа.")

            return True
        except (KeyError, TypeError, AttributeError):
            if verbose:
                logger.error("Сервер ответил неизвестным документом.")
            return False

    def __enter__(self) -> FileWriter:
        self._file = self._open_file(self._file_path, "w")
        return self

    def __exit__(self, *exc_info) -> None:
        # Проверяем наличие атрибута _file перед закрытием
        if hasattr(self, "_file") and not self._file.closed:
            self._file.close()

    def close(self) -> None:
        """Закрывает файл."""
        if hasattr(self, "_file") and not self._file.closed:
            self._file.close()
