"""
Модуль сериализации данных для кэширования.

Предоставляет класс JsonSerializer для сериализации и десериализации
данных в формат JSON с поддержкой orjson для высокой производительности.

Пример использования:
    >>> from parser_2gis.cache import JsonSerializer
    >>> serializer = JsonSerializer()
    >>> data = {"key": "value"}
    >>> json_str = serializer.serialize(data)
    >>> deserialized = serializer.deserialize(json_str)
"""

import json
from typing import Any, Dict

from ..logger.logger import logger as app_logger

# Попытка импортировать orjson для более быстрой сериализации
# orjson в 2-3 раза быстрее стандартного json модуля
try:
    import orjson

    _USE_ORJSON = True
except ImportError:
    _USE_ORJSON = False
    orjson = None  # type: ignore


class JsonSerializer:
    """Сериализатор данных в JSON формат.

    Поддерживает orjson с fallback на стандартный json модуль.
    Обеспечивает валидацию структуры данных после десериализации.

    Attributes:
        use_orjson: Флаг использования orjson (True если доступен).

    Пример использования:
        >>> serializer = JsonSerializer()
        >>> data = {"key": "value"}
        >>> json_str = serializer.serialize(data)
        >>> deserialized = serializer.deserialize(json_str)
    """

    def __init__(self) -> None:
        """Инициализация сериализатора."""
        self.use_orjson = _USE_ORJSON

    def serialize(self, data: Dict[str, Any]) -> str:
        """
        Сериализует данные в JSON формат.

        - Выбрасываем явные исключения с контекстом вместо app_logger.warning
        - Используем orjson если установлен (в 2-3 раза быстрее)
        - Fallback на стандартный json если orjson недоступен или возникла TypeError

        Args:
            data: Данные для сериализации.

        Returns:
            JSON строка.

        Raises:
            TypeError: При ошибке сериализации данных с полным контекстом.
            ValueError: При ошибке преобразования данных.

        Example:
            >>> serializer = JsonSerializer()
            >>> serializer.serialize({"key": "value"})
            '{"key":"value"}'
        """
        if self.use_orjson and orjson is not None:
            # orjson возвращает bytes, декодируем в строку
            try:
                return orjson.dumps(data).decode("utf-8")
            except (orjson.EncodeError, TypeError) as orjson_error:
                # Fallback на стандартный json при TypeError от orjson
                # TypeError может возникнуть при сериализации неподдерживаемых типов
                app_logger.debug("orjson ошибка, fallback на json: %s", orjson_error)
                # Продолжаем выполнение и используем стандартный json
            except (RuntimeError, OSError, MemoryError) as unexpected_error:
                # Любая другая неожиданная ошибка - логируем и используем fallback
                app_logger.debug(
                    "Неожиданная ошибка orjson, fallback на json: %s", unexpected_error
                )

        # Стандартный json с оптимизированными параметрами
        try:
            return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as json_error:
            raise TypeError(
                f"Critical JSON serialization error: {json_error}. "
                f"Data type: {type(data).__name__}, data size: {len(str(data))} bytes"
            ) from json_error

    def deserialize(self, data: str) -> Dict[str, Any]:
        """
        Десериализует JSON строку в данные с валидацией структуры.

        - Выбрасываем явные исключения с контекстом вместо app_logger.warning
        - Используем orjson если установлен
        - Fallback на стандартный json если orjson недоступен
        - ВАЛИДАЦИЯ СТРУКТУРЫ ДАННЫХ после десериализации

        Args:
            data: JSON строка для десериализации.

        Returns:
            Данные в виде словаря.

        Raises:
            json.JSONDecodeError: При ошибке парсинга JSON с контекстом.
            UnicodeDecodeError: При ошибке декодирования Unicode.
            orjson.JSONDecodeError: При ошибке парсинга orjson с контекстом.
            ValueError: При критической ошибке десериализации или некорректной структуре.
            TypeError: Если данные не являются словарём.

        Example:
            >>> serializer = JsonSerializer()
            >>> serializer.deserialize('{"key":"value"}')
            {'key': 'value'}
        """
        try:
            if self.use_orjson and orjson is not None:
                deserialized = orjson.loads(data, option=orjson.OPT_NON_STR_KEYS)  # type: ignore
            else:
                deserialized = json.loads(data)

            # Проверяем что данные являются словарём
            if not isinstance(deserialized, dict):
                app_logger.error(
                    "Некорректный тип данных кэша после десериализации. "
                    "Ожидался dict, получен %s. Размер данных: %d байт",
                    type(deserialized).__name__,
                    len(str(deserialized)),
                )
                raise TypeError(
                    f"Ожидался словарь после десериализации, "
                    f"получен {type(deserialized).__name__}. "
                    f"Размер данных: {len(str(deserialized))} байт"
                )

            return deserialized

        except (UnicodeDecodeError, MemoryError) as json_error:
            # Обрабатываем все остальные исключения десериализации с сохранением цепочки
            if orjson is not None:
                try:
                    # Проверяем, это orjson.JSONDecodeError
                    if isinstance(json_error, orjson.JSONDecodeError):  # type: ignore
                        raise ValueError(
                            f"Критическая ошибка десериализации orjson: {json_error}. "
                            f"Длина данных: {len(data)}, "
                            f"Содержимое: {data[:200]}..."
                        ) from json_error
                except (AttributeError, TypeError) as e:
                    app_logger.warning("Ошибка проверки orjson: %s", e)
            # Стандартная обработка JSON ошибок
            raise ValueError(
                f"Критическая ошибка десериализации: {json_error}. Длина данных: {len(data)}"
            ) from json_error
        except TypeError:
            # Пробрасываем TypeError как есть (некорректный тип данных)
            raise
        except ValueError:
            # Пробрасываем ValueError как есть (некорректная структура)
            raise
