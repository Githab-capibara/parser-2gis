"""Модуль сериализации данных для кэширования.

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
from typing import Any

from ..logger.logger import logger as app_logger

# Попытка импортировать orjson для более быстрой сериализации
# orjson в 2-3 раза быстрее стандартного json модуля
try:
    import orjson

    _USE_ORJSON = True
except ImportError:
    _USE_ORJSON = False


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

    def serialize(self, data: dict[str, Any]) -> str:
        """Сериализует данные в JSON формат.

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
        # ISSUE-104: Убрана избыточная проверка orjson is not None
        if _USE_ORJSON:
            # orjson возвращает bytes, декодируем в строку
            try:
                return str(orjson.dumps(data).decode("utf-8"))
            except (orjson.EncodeError, TypeError) as orjson_error:
                # Fallback на стандартный json при TypeError от orjson
                # TypeError может возникнуть при сериализации неподдерживаемых типов
                app_logger.debug("orjson ошибка, fallback на json: %s", orjson_error)
                # Продолжаем выполнение и используем стандартный json
            except (RuntimeError, OSError, MemoryError) as unexpected_error:
                # Любая другая неожиданная ошибка - логируем и используем fallback
                # ID:041: Изменено на WARNING для видимости проблем сериализации
                app_logger.warning(
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

    def deserialize(self, data: str) -> dict[str, Any]:
        """Десериализует JSON строку в данные с валидацией структуры.

        - Используем orjson если установлен
        - Fallback на стандартный json если orjson недоступен
        - Fallback на другие кодировки (latin-1, cp1251) при UnicodeDecodeError
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
            # ISSUE-104: Убрана избыточная проверка orjson is not None
            if _USE_ORJSON:
                deserialized = orjson.loads(data, option=orjson.OPT_NON_STR_KEYS)
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

        except UnicodeDecodeError as unicode_error:
            # Fallback на другие кодировки при UnicodeDecodeError
            app_logger.debug(
                "UnicodeDecodeError при десериализации, попытка fallback: %s", unicode_error
            )

            # ID:092: Логируем все fallback попытки
            fallback_attempts = []

            # Пытаемся декодировать с заменой некорректных символов
            try:
                if isinstance(data, bytes):
                    # Пробуем latin-1 как универсальную кодировку
                    data_decoded = data.decode("latin-1", errors="replace")
                    deserialized = json.loads(data_decoded)
                    app_logger.info("Fallback на latin-1 успешен (с заменой символов)")
                    return deserialized
                fallback_attempts.append("latin-1: неудача")
            except (json.JSONDecodeError, AttributeError) as fallback_error:
                fallback_attempts.append(f"latin-1: {fallback_error}")
                app_logger.debug("Fallback на latin-1 не удался: %s", fallback_error)

            # Пробуем cp1251 для кириллических данных
            try:
                if isinstance(data, bytes):
                    data_decoded = data.decode("cp1251", errors="replace")
                    deserialized = json.loads(data_decoded)
                    app_logger.info("Fallback на cp1251 успешен (с заменой символов)")
                    return deserialized
                fallback_attempts.append("cp1251: неудача")
            except (json.JSONDecodeError, AttributeError) as fallback_error:
                fallback_attempts.append(f"cp1251: {fallback_error}")
                app_logger.debug("Fallback на cp1251 не удался: %s", fallback_error)

            # Логируем все неудачные попытки перед выбрасыванием исключения
            if fallback_attempts:
                app_logger.warning(
                    "Все fallback кодировки не подошли. Попытки: %s", "; ".join(fallback_attempts)
                )

            # Если все fallback не удались, выбрасываем исключение
            data_len = len(data) if isinstance(data, (str, bytes)) else "N/A"
            raise ValueError(
                f"Не удалось десериализовать данные: все кодировки не подошли. "
                f"Original error: {unicode_error}. Длина данных: {data_len}"
            ) from unicode_error

        except MemoryError as json_error:
            # ISSUE-093, ISSUE-095: Упрощённая обработка ошибок без избыточных try/except
            # ISSUE-104: Убрана избыточная проверка orjson is not None
            # #143: Не логируем содержимое данных — только размер для безопасности
            if _USE_ORJSON:
                # Проверяем, это orjson.JSONDecodeError
                try:
                    if isinstance(json_error, orjson.JSONDecodeError):
                        raise ValueError(
                            f"Ошибка десериализации, размер данных: {len(data)} байт"
                        ) from json_error
                except (AttributeError, TypeError) as orjson_check_error:
                    # orjson.JSONDecodeError недоступен, используем стандартную обработку
                    app_logger.debug(
                        "Не удалось проверить orjson.JSONDecodeError: %s", orjson_check_error
                    )

            # Стандартная обработка JSON ошибок
            raise ValueError(
                f"Ошибка десериализации, размер данных: {len(data)} байт"
            ) from json_error
        except TypeError:
            # Пробрасываем TypeError как есть (некорректный тип данных)
            raise
        except ValueError:
            # Пробрасываем ValueError как есть (некорректная структура)
            raise


# =============================================================================
# ФУНКЦИИ-ОБЁРТКИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ С ТЕСТАМИ
# =============================================================================


def _serialize_json(data: dict[str, Any]) -> str:
    """Функция-обёртка для сериализации JSON (для обратной совместимости с тестами).

    Args:
        data: Данные для сериализации.

    Returns:
        JSON строка.

    Raises:
        TypeError: При ошибке сериализации данных.

    """
    serializer = JsonSerializer()
    return serializer.serialize(data)


def _deserialize_json(data: str) -> dict[str, Any]:
    """Функция-обёртка для десериализации JSON (для обратной совместимости с тестами).

    Args:
        data: JSON строка для десериализации.

    Returns:
        Данные в виде словаря.

    Raises:
        ValueError: При ошибке десериализации.

    """
    serializer = JsonSerializer()
    return serializer.deserialize(data)
