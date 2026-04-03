"""Модуль валидации данных для кэширования.

Предоставляет класс CacheDataValidator для проверки данных кэша
на безопасность и соответствие ограничениям.

Пример использования:
    >>> from parser_2gis.cache import CacheDataValidator
    >>> validator = CacheDataValidator()
    >>> data = {"key": "value"}
    >>> is_valid = validator.validate(data)
"""

import math
import re
import urllib.parse
from typing import Any, ClassVar

from ..constants import MAX_DATA_DEPTH, MAX_STRING_LENGTH
from ..logger.logger import logger as app_logger


class CacheDataValidator:
    """Валидатор данных кэша на безопасность.

    Проверяет данные на:
    - Тип данных (только dict, list, str, int, float, bool, None)
    - Глубину вложенности (MAX_DATA_DEPTH = 100)
    - Длину строк (MAX_STRING_LENGTH = 10000)
    - Наличие SQL-инъекций
    - Prototype pollution атаки (__proto__, constructor, prototype)
    - Числовые аномалии (NaN, Infinity)

    Attributes:
        max_depth: Максимальная глубина вложенности данных.
        max_string_length: Максимальная длина строки.

    Пример использования:
        >>> validator = CacheDataValidator()
        >>> validator.validate({"key": "value"})
        True
        >>> validator.validate({"__proto__": "attack"})
        False

    """

    # Паттерн для обнаружения SQL-инъекций
    # Используем (?<![^\s]) вместо \b для корректной работы с unicode
    # Расширенный набор паттернов для обнаружения различных типов SQL-инъекций
    _SQL_INJECTION_PATTERNS: re.Pattern[str] = re.compile(
        r"(?i)(?:\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|EXECUTE)\b|"
        r"--|/\*|\*/|@@|CHAR\(|0x[0-9a-f]+|"
        r"\b(?:OR|AND)\s+\d+\s*=\s*\d+|"
        r"\bUNION\s+(?:ALL\s+)?SELECT\b|"
        r"\bWAITFOR\s+DELAY\b|"
        r"\bBENCHMARK\s*\(|"
        r"\bHAVING\s+\d+\s*=\s*\d+|"
        r"\bGROUP\s+BY\s+\d+|"
        r"\bORDER\s+BY\s+\d+|"
        r"\bSLEEP\s*\(\s*\d+\s*\)|"
        r"\bINFORMATION_SCHEMA\b|"
        r"\bSYS\.\w+|"
        r";\s*(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|EXECUTE)|"
        r"\b(?:LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b|"
        r"\b(?:EXTRACTVALUE|UPDATEXML)\s*\(|"
        r"\bxp_\w+|"
        r"\b(?:TRUNCATE|ALTER|CREATE|GRANT|REVOKE)\b|"
        r"\b(?:CONCAT|GROUP_CONCAT|CAST|CONVERT)\s*\(|"
        r"'\s*(?:OR|AND|UNION|SELECT|INSERT|UPDATE|DELETE|DROP|EXEC)\b)"
    )

    # Опасные ключи для защиты от prototype pollution
    # Расширенный набор для полной защиты от различных методов прототипного загрязнения
    _DANGEROUS_KEYS: ClassVar[set[str]] = {
        "__proto__",
        "constructor",
        "prototype",
        "__defineGetter__",
        "__defineSetter__",
        "__lookupGetter__",
        "__lookupSetter__",
        "__iterator__",
        "hasOwnProperty",
        "isPrototypeOf",
        "propertyIsEnumerable",
        "toString",
        "valueOf",
        "toLocaleString",
    }

    def __init__(self) -> None:
        """Инициализация валидатора."""
        self.max_depth = MAX_DATA_DEPTH
        self.max_string_length = MAX_STRING_LENGTH

    def validate(self, data: Any, depth: int = 0) -> bool:
        """Валидирует данные кэша на безопасность.

        Проверяет тип данных, глубину вложенности, наличие опасных конструкций.

        Args:
            data: Данные для валидации.
            depth: Текущая глубина вложенности.

        Returns:
            True если данные безопасны, False иначе.

        Example:
            >>> validator = CacheDataValidator()
            >>> validator.validate({"key": "value"})
            True
            >>> validator.validate(None)
            True
            >>> validator.validate({"__proto__": "attack"})
            False

        """
        # Проверяем глубину вложенности НЕМЕДЛЕННО
        # Это предотвращает обход проверки при глубокой вложенности
        if depth > self.max_depth:
            app_logger.error(
                "КРИТИЧЕСКОЕ ПРЕВЫШЕНИЕ: глубина вложенности данных кэша %d превышает лимит %d",
                depth,
                self.max_depth,
            )
            return False

        # Дополнительная проверка на граничное значение (depth == max_depth)
        # Предупреждаем о приближении к лимиту
        if depth == self.max_depth:
            app_logger.warning(
                "Внимание: достигнута максимальная глубина вложенности данных кэша (%d)",
                self.max_depth,
            )

        # Base types
        if data is None:
            return True

        if isinstance(data, bool):
            return True

        if isinstance(data, (int, float)):
            return self._check_numeric(data)

        if isinstance(data, str):
            return self._check_string(data)

        if isinstance(data, dict):
            return self._check_dict(data, depth)

        if isinstance(data, list):
            return self._check_list(data, depth)

        # Недопустимый тип
        app_logger.error(
            "КРИТИЧЕСКАЯ ОШИБКА: недопустимый тип данных в кэше: %s", type(data).__name__
        )
        return False

    def _check_numeric(self, data: float | int) -> bool:
        """Валидирует числовые данные (int, float).

        Args:
            data: Числовые данные для валидации.

        Returns:
            True если данные корректны, False если обнаружены NaN/Infinity.

        Example:
            >>> validator = CacheDataValidator()
            >>> validator._check_numeric(42)
            True
            >>> validator._check_numeric(float('nan'))
            False

        """
        if isinstance(data, float) and (math.isnan(data) or math.isinf(data)):
            app_logger.warning("Обнаружено NaN/Infinity в данных кэша")
            return False
        return True

    def _check_string(self, data: str) -> bool:
        """Валидирует строковые данные.

        Args:
            data: Строка для валидации.

        Returns:
            True если строка корректна, False если превышает лимит длины
            или содержит SQL-инъекцию.

        Example:
            >>> validator = CacheDataValidator()
            >>> validator._check_string("normal string")
            True
            >>> validator._check_string("SELECT * FROM users")
            False

        """
        if len(data) > self.max_string_length:
            app_logger.warning(
                "Длина строки превышает максимальный лимит: %d (максимум: %d)",
                len(data),
                self.max_string_length,
            )
            return False
        if not self._check_sql_injection_patterns(data):
            return False
        return True

    def _check_dict(self, data: dict, depth: int) -> bool:
        """Валидирует данные типа dict.

        Args:
            data: Словарь для валидации.
            depth: Текущая глубина вложенности.

        Returns:
            True если словарь корректен, False если обнаружены опасные ключи
            или значения.

        Example:
            >>> validator = CacheDataValidator()
            >>> validator._check_dict({"key": "value"}, 0)
            True
            >>> validator._check_dict({"__proto__": "attack"}, 0)
            False

        """
        # Проверяем на __proto__ и другие опасные ключи (prototype pollution)
        for key in data.keys():
            if isinstance(key, str) and key.lower() in self._DANGEROUS_KEYS:
                app_logger.warning("Обнаружена потенциальная __proto__ атака: ключ '%s'", key)
                return False

        # H010: Проверяем глубину ПЕРЕД рекурсивным вызовом для оптимизации
        next_depth = depth + 1
        if next_depth > self.max_depth:
            app_logger.error(
                "КРИТИЧЕСКОЕ ПРЕВЫШЕНИЕ: глубина вложенности данных кэша %d превышает лимит %d",
                next_depth,
                self.max_depth,
            )
            return False

        # Рекурсивно проверяем все значения словаря
        for key, value in data.items():
            if not isinstance(key, str):
                app_logger.warning("Некорректный тип ключа в данных кэша")
                return False
            if not self.validate(value, next_depth):
                return False
        return True

    def _check_list(self, data: list, depth: int) -> bool:
        """Валидирует данные типа list.

        Args:
            data: Список для валидации.
            depth: Текущая глубина вложенности.

        Returns:
            True если список корректен, False если обнаружены недопустимые элементы.

        Example:
            >>> validator = CacheDataValidator()
            >>> validator._check_list([1, 2, 3], 0)
            True
            >>> validator._check_list([{"key": "value"}], 0)
            True

        """
        # H010: Проверяем глубину ПЕРЕД рекурсивным вызовом для оптимизации
        next_depth = depth + 1
        if next_depth > self.max_depth:
            app_logger.error(
                "КРИТИЧЕСКОЕ ПРЕВЫШЕНИЕ: глубина вложенности данных кэша %d превышает лимит %d",
                next_depth,
                self.max_depth,
            )
            return False

        # Рекурсивно проверяем все элементы списка
        for item in data:
            if not self.validate(item, next_depth):
                return False
        return True

    def _check_sql_injection_patterns(self, value: Any) -> bool:
        """Проверяет значение на наличие SQL-инъекций.

        Args:
            value: Значение для проверки.

        Returns:
            True если значение безопасно, False если обнаружена SQL-инъекция.

        Example:
            >>> validator = CacheDataValidator()
            >>> validator._check_sql_injection_patterns("normal string")
            True
            >>> validator._check_sql_injection_patterns("'; DROP TABLE users; --")
            False

        """
        if isinstance(value, str):
            # Проверяем оригинальное значение
            if self._SQL_INJECTION_PATTERNS.search(value):
                app_logger.warning("Обнаружен потенциальный SQL-инъекция в кэше: %s", value[:100])
                return False
            # Проверяем URL-decoded значение для обнаружения encoded атак
            try:
                decoded_value = urllib.parse.unquote(value)
                if decoded_value != value and self._SQL_INJECTION_PATTERNS.search(decoded_value):
                    app_logger.warning(
                        "Обнаружен потенциальный SQL-инъекция в URL-encoded кэше: %s", value[:100]
                    )
                    return False
            except (ValueError, TypeError, UnicodeDecodeError) as e:
                # Игнорируем ошибки декодирования
                app_logger.debug("Ошибка декодирования URL-encoded значения: %s", e)
        return True


__all__ = ["CacheDataValidator"]
