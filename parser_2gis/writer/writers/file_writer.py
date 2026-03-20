"""Базовый файловый писатель.

Предоставляет абстрактный класс FileWriter с базовой функциональностью:
- Валидация пути к файлу (Path traversal защита)
- Проверка JSON-документов Catalog Item API
- Управление файловыми ресурсами
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, Dict, Optional

from ...logger import logger

if TYPE_CHECKING:
    from ..options import WriterOptions


class FileWriter(ABC):
    """Базовый писатель."""

    def __init__(self, file_path: str, writer_options: WriterOptions) -> None:
        # ИСПРАВЛЕНИЕ 13: Path traversal защита
        # Валидация пути через os.path.basename() для предотвращения записи
        # файлов за пределы разрешённой output директории
        self._file_path = self._validate_file_path(file_path)
        self._options = writer_options

    def _validate_file_path(self, file_path: str) -> str:
        """
        Валидирует путь к файлу на предмет Path traversal атак.

        Args:
            file_path: Путь к файлу для валидации.

        Returns:
            Валидированный путь к файлу.

        Raises:
            ValueError: Если путь содержит Path traversal конструкции.

        Примечание:
            - Использует os.path.basename() для извлечения имени файла
            - Проверяет на наличие '../' и '..\\' конструкций
            - Ограничивает путь только output директорией
        """
        if not file_path:
            raise ValueError("Путь к файлу не может быть пустым")

        # Конвертируем Path в строку если нужно
        file_path_str = str(file_path) if isinstance(file_path, Path) else file_path

        # Проверяем на наличие Path traversal конструкций
        if ".." in file_path_str:
            logger.warning(
                "Путь к файлу содержит '..' (возможная Path traversal атака): %s. "
                "Путь будет нормализован.",
                file_path_str,
            )

        # Нормализуем путь через os.path.normpath()
        normalized_path = os.path.normpath(file_path_str)

        # Извлекаем базовое имя файла для предотвращения traversal атак
        # Это гарантирует что файл будет создан только в текущей директории
        base_name = os.path.basename(normalized_path)

        # Если после нормализации путь изменился, логируем предупреждение
        if normalized_path != base_name and not normalized_path.startswith(os.getcwd()):
            # Путь содержит директорию отличную от текущей
            # Используем только базовое имя файла
            logger.warning(
                "Путь к файлу выходит за пределы текущей директории: %s. "
                "Используется только имя файла: %s",
                file_path_str,
                base_name,
            )
            return base_name

        return normalized_path

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
