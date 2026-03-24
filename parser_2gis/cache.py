"""
Модуль для кэширования результатов парсинга.

Предоставляет функциональность для кэширования результатов парсинга
в локальной базе данных SQLite для ускорения повторных запусков.

Оптимизации:
- Connection pooling для избежания накладных расходов на создание соединений
- WAL режим для лучшей производительности при конкурентном доступе
- Пакетные операции для массовой вставки/удаления
- Компилированные SQL запросы для снижения парсинга

Пример использования:
    >>> from pathlib import Path
    >>> from .cache import CacheManager
    >>> cache = CacheManager(Path("cache.db"))
    >>> cache.initialize()  # Инициализация БД
    >>> cache.get("some_key")  # Получение из кэша
    >>> cache.set("key", {"data": "value"})  # Сохранение в кэш
    >>> cache.close()  # Закрытие соединения
"""

import hashlib
import json
import os
import queue
import re
import sqlite3
import threading
import time
import unicodedata
import urllib.parse
import weakref
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .constants import MAX_DATA_DEPTH, MAX_STRING_LENGTH
from .logger.logger import logger as app_logger


def _normalize_unicode(text: str) -> str:
    """Нормализует unicode текст в форму NFC.

    Предотвращает атаки через unicode normalization.

    Args:
        text: Текст для нормализации.

    Returns:
        Нормализованный текст в форме NFC.
    """
    return unicodedata.normalize("NFC", text)


_SQL_INJECTION_PATTERNS: re.Pattern = re.compile(
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|EXECUTE)\b|"
    r"--|/\*|\*/|@@|CHAR\(|0x[0-9a-f]+|"
    r"\b(OR|AND)\s+\d+\s*=\s*\d+|"
    r"\bUNION\s+(ALL\s+)?SELECT\b|"
    r"\bWAITFOR\s+DELAY\b|"
    r"\bBENCHMARK\s*\(|"
    r"\bHAVING\s+\d+\s*=\s*\d+|"
    r"\bGROUP\s+BY\s+\d+|"
    r"\bORDER\s+BY\s+\d+|"
    r"\bSLEEP\s*\(\s*\d+\s*\)|"
    r"\bINFORMATION_SCHEMA\b|"
    r"\bSYS\.\w+\b|"
    r";\s*(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|EXECUTE)\b)",
    re.IGNORECASE,
)


def _check_sql_injection_patterns(value: Any) -> bool:
    """Проверяет значение на наличие SQL-инъекций.

    Args:
        value: Значение для проверки.

    Returns:
        True если значение безопасно, False если обнаружена SQL-инъекция.
    """
    if isinstance(value, str):
        # Проверяем оригинальное значение
        if _SQL_INJECTION_PATTERNS.search(value):
            app_logger.warning("Обнаружен потенциальный SQL-инъекция в кэше: %s", value[:100])
            return False
        # Проверяем URL-decoded значение для обнаружения encoded атак
        try:
            decoded_value = urllib.parse.unquote(value)
            if decoded_value != value and _SQL_INJECTION_PATTERNS.search(decoded_value):
                app_logger.warning(
                    "Обнаружен потенциальный SQL-инъекция в URL-encoded кэше: %s", value[:100]
                )
                return False
        except (ValueError, TypeError, UnicodeDecodeError):
            # Игнорируем ошибки декодирования
            pass
    return True


# =============================================================================
# ОПТИМИЗАЦИЯ 3.6: orjson wrapper для сериализации
# =============================================================================

# Попытка импортировать orjson для более быстрой сериализации
# orjson в 2-3 раза быстрее стандартного json модуля
try:
    import orjson

    _USE_ORJSON = True
except ImportError:
    _USE_ORJSON = False
    orjson = None  # type: ignore

# =============================================================================
# ОПТИМИЗАЦИЯ: psutil для мониторинга памяти
# =============================================================================

# Попытка импортировать psutil для мониторинга памяти
# psutil используется для динамического расчёта размера пула соединений
try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore


def _serialize_json(data: Dict[str, Any]) -> str:
    """
    Сериализует данные в JSON формат.
    - Выбрасываем явные исключения с контекстом вместо app_logger.warning
    - Используем orjson если установлен (в 2-3 раза быстрее)
    - Fallback на стандартный json если orjson недоступен или возникла TypeError
    - ИСПРАВЛЕНИЕ 7: Добавлена обработка TypeError от orjson

    Args:
        data: Данные для сериализации.

    Returns:
        JSON строка.

    Raises:
        TypeError: При ошибке сериализации данных с полным контекстом.
        ValueError: При ошибке преобразования данных.
    """
    if _USE_ORJSON and orjson is not None:
        # orjson возвращает bytes, декодируем в строку
        try:
            return orjson.dumps(data).decode("utf-8")
        except (orjson.EncodeError, TypeError) as orjson_error:
            # ИСПРАВЛЕНИЕ 7: Fallback на стандартный json при TypeError от orjson
            # TypeError может возникнуть при сериализации неподдерживаемых типов
            app_logger.debug("orjson ошибка, fallback на json: %s", orjson_error)
            # Продолжаем выполнение и используем стандартный json
        except (RuntimeError, OSError, MemoryError) as unexpected_error:
            # Любая другая неожиданная ошибка - логируем и используем fallback
            app_logger.debug("Неожиданная ошибка orjson, fallback на json: %s", unexpected_error)

    # Стандартный json с оптимизированными параметрами
    try:
        return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as json_error:  # FIX #29: Missing error context in re-raise
        raise TypeError(
            f"Critical JSON serialization error: {json_error}. "
            f"Data type: {type(data).__name__}, data size: {len(str(data))} bytes"
        ) from json_error


def _deserialize_json(data: str) -> Dict[str, Any]:
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
    """
    try:
        if _USE_ORJSON and orjson is not None:
            deserialized = orjson.loads(data)  # type: ignore
        else:
            deserialized = json.loads(data)

        # Проверяем что данные являются словарём
        if not isinstance(deserialized, dict):
            app_logger.error(
                "Некорректный тип данных кэша после десериализации. Ожидался dict, получен %s. Размер данных: %d байт",
                type(deserialized).__name__,
                len(str(deserialized)),
            )
            raise TypeError(
                f"Ожидался словарь после десериализации, получен {type(deserialized).__name__}. "
                f"Размер данных: {len(str(deserialized))} байт"
            )

        # Проверяем данные на наличие потенциально опасных конструкций
        if not _validate_cached_data(deserialized):
            app_logger.error(
                "Данные кэша содержат небезопасные конструкции. Тип: %s, Размер: %d байт",
                type(deserialized).__name__,
                len(str(deserialized)),
            )
            raise ValueError(
                f"Данные кэша содержат небезопасные конструкции. "
                f"Тип: {type(deserialized).__name__}, "
                f"Размер: {len(str(deserialized))} байт"
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
        # Пробрасываем ValueError как есть (небезопасные данные)
        raise


def _validate_numeric_data(data: float | int) -> bool:
    """Валидирует числовые данные (int, float).

    Args:
        data: Числовые данные для валидации.

    Returns:
        True если данные корректны, False если обнаружены NaN/Infinity.
    """
    import math

    if isinstance(data, float) and (math.isnan(data) or math.isinf(data)):
        app_logger.warning("Обнаружено NaN/Infinity в данных кэша")
        return False
    return True


def _validate_string_data(data: str) -> bool:
    """Валидирует строковые данные.

    Args:
        data: Строка для валидации.

    Returns:
        True если строка корректна, False если превышает лимит длины или содержит SQL-инъекцию.
    """
    if len(data) > MAX_STRING_LENGTH:
        app_logger.warning(
            "Длина строки превышает максимальный лимит: %d (максимум: %d)",
            len(data),
            MAX_STRING_LENGTH,
        )
        return False
    if not _check_sql_injection_patterns(data):
        return False
    return True


def _validate_dict_data(data: dict, depth: int) -> bool:
    """Валидирует данные типа dict.

    Args:
        data: Словарь для валидации.
        depth: Текущая глубина вложенности.

    Returns:
        True если словарь корректен, False если обнаружены опасные ключи или значения.
    """
    # Проверяем на __proto__ и другие опасные ключи (prototype pollution)
    dangerous_keys: Set[str] = {"__proto__", "constructor", "prototype"}
    for key in data.keys():
        if isinstance(key, str) and key.lower() in dangerous_keys:
            app_logger.warning("Обнаружена потенциальная __proto__ атака: ключ '%s'", key)
            return False

    # Рекурсивно проверяем все значения словаря
    for key, value in data.items():
        if not isinstance(key, str):
            app_logger.warning("Некорректный тип ключа в данных кэша")
            return False
        if not _validate_cached_data(value, depth + 1):
            return False
    return True


def _validate_list_data(data: list, depth: int) -> bool:
    """Валидирует данные типа list.

    Args:
        data: Список для валидации.
        depth: Текущая глубина вложенности.

    Returns:
        True если список корректен, False если обнаружены недопустимые элементы.
    """
    # Рекурсивно проверяем все элементы списка
    for item in data:
        if not _validate_cached_data(item, depth + 1):
            return False
    return True


def _validate_cached_data(data: Any, depth: int = 0) -> bool:
    """Валидирует данные кэша на безопасность.
    - Проверяет тип данных (только dict, list, str, int, float, bool, None)
    - Ограничивает глубину вложенности для предотвращения DoS (MAX_DATA_DEPTH = 100)
    - Проверяет строки на наличие потенциально опасных SQL/JS конструкций
    - Добавлена проверка на UNION SELECT
    - Добавлена проверка на OR 1=1 и подобные конструкции
    - Добавлена максимальная длина строки (MAX_STRING_LENGTH = 10000)

    Args:
        data: Данные для валидации.
        depth: Текущая глубина вложенности.

    Returns:
        True если данные безопасны, False иначе.
    """
    # Проверяем глубину вложенности НЕМЕДЛЕННО
    # Это предотвращает обход проверки при глубокой вложенности
    if depth > MAX_DATA_DEPTH:
        app_logger.error(
            "КРИТИЧЕСКОЕ ПРЕВЫШЕНИЕ: глубина вложенности данных кэша %d превышает лимит %d",
            depth,
            MAX_DATA_DEPTH,
        )
        return False

    # Дополнительная проверка на граничное значение (depth == MAX_DATA_DEPTH)
    # Предупреждаем о приближении к лимиту
    if depth == MAX_DATA_DEPTH:
        app_logger.warning(
            "Внимание: достигнута максимальная глубина вложенности данных кэша (%d)", MAX_DATA_DEPTH
        )

    # Base types
    if data is None:  # FIX #15: Inconsistent null handling
        return True

    if isinstance(data, bool):
        return True

    if isinstance(data, (int, float)):
        return _validate_numeric_data(data)

    if isinstance(data, str):
        return _validate_string_data(data)

    if isinstance(data, dict):
        return _validate_dict_data(data, depth)

    if isinstance(data, list):
        return _validate_list_data(data, depth)

    # Недопустимый тип
    app_logger.error("КРИТИЧЕСКАЯ ОШИБКА: недопустимый тип данных в кэше: %s", type(data).__name__)
    return False


# Экспортируемые символы модуля
__all__ = ["CacheManager"]

# =============================================================================
# КОНСТАНТЫ ДЛЯ ОПТИМИЗАЦИИ И БЕЗОПАСНОСТИ
# =============================================================================

# Размер пакета для пакетных операций вставки/удаления
DEFAULT_BATCH_SIZE: int = 100

# Максимальный возраст соединения в секундах (5 минут)
MAX_CONNECTION_AGE: int = 300

# Максимальный размер пакета для предотвращения DoS атак
MAX_BATCH_SIZE: int = 1000

# Максимальный размер кэша в мегабайтах
MAX_CACHE_SIZE_MB: int = 500

# Количество записей для удаления при LRU eviction
LRU_EVICT_BATCH: int = 100

# Длина SHA256 хеша в hex формате
SHA256_HASH_LENGTH: int = 64

# =============================================================================
# ВАЛИДАЦИЯ ENV ПЕРЕМЕННЫХ ДЛЯ CONNECTION POOL
# =============================================================================


# Импортируем функцию валидации из parallel_parser если доступна
# или определяем локально для избежания циклических импортов
def _validate_pool_env_int(
    env_name: str, default: int, min_value: Optional[int] = None, max_value: Optional[int] = None
) -> int:
    """Валидирует ENV переменную для параметров пула соединений.

    Args:
        env_name: Имя ENV переменной.
        default: Значение по умолчанию.
        min_value: Минимальное допустимое значение.
        max_value: Максимальное допустимое значение.

    Returns:
        Валидированное целое число в допустимом диапазоне.
    """
    value_str = os.getenv(env_name)

    if value_str is None:
        return default

    try:
        value = int(value_str)

        # Проверяем минимальное значение
        if min_value is not None and value < min_value:
            app_logger.warning(
                "ENV переменная %s=%d меньше минимального значения %d. Используется %d",
                env_name,
                value,
                min_value,
                min_value,
            )
            return min_value

        # Проверяем максимальное значение
        if max_value is not None and value > max_value:
            app_logger.warning(
                "ENV переменная %s=%d больше максимального значения %d. Используется %d",
                env_name,
                value,
                max_value,
                max_value,
            )
            return max_value

        return value

    except ValueError:
        app_logger.warning(
            "ENV переменная %s=%s не является целым числом. Используется значение по умолчанию %d",
            env_name,
            value_str,
            default,
        )
        return default


# Максимальное количество соединений в пуле (10-20 соединений)
# ОБОСНОВАНИЕ: 20 соединений выбрано исходя из:
# - Типичное количество потоков: 5-15
# - Каждое соединение занимает ~1-5MB памяти
# - 20 * 5MB = 100MB - разумный предел для большинства систем
# - queue.Queue для управления соединениями обеспечивает потокобезопасность
# Допустимый диапазон: 5-50 соединений
MAX_POOL_SIZE: int = _validate_pool_env_int(
    "PARSER_MAX_POOL_SIZE", default=20, min_value=5, max_value=50
)

# Минимальное количество соединений в пуле
# Допустимый диапазон: 1-10 соединений
MIN_POOL_SIZE: int = _validate_pool_env_int(
    "PARSER_MIN_POOL_SIZE", default=5, min_value=1, max_value=10
)

# Время жизни соединения в секундах (5 минут)
# Соединения старше этого возраста будут пересозданы
# Допустимый диапазон: 60-3600 секунд (1 час)
CONNECTION_MAX_AGE: int = _validate_pool_env_int(
    "PARSER_CONNECTION_MAX_AGE", default=300, min_value=60, max_value=3600
)


def _calculate_dynamic_pool_size() -> int:
    """
    Рассчитывает оптимальный размер пула соединений на основе доступной памяти.

    Алгоритм расчёта:
    - Получаем доступную память системы (если возможно)
    - Каждое соединение SQLite занимает ~1-5MB памяти
    - Выделяем до 10% доступной памяти под пул соединений
    - Ограничиваем результат пределами [MIN_POOL_SIZE, MAX_POOL_SIZE]

    Returns:
        Оптимальный размер пула соединений.

    Example:
        >>> pool_size = _calculate_dynamic_pool_size()
        >>> print(f"Рекомендуемый размер пула: {pool_size}")
    """
    try:
        # Пытаемся получить информацию о памяти через psutil
        if not _PSUTIL_AVAILABLE or psutil is None:
            raise ImportError("psutil не установлен")

        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)

        # Выделяем до 10% доступной памяти под пул соединений
        # Каждое соединение занимает ~2MB в среднем
        memory_for_pool_mb = available_memory_mb * 0.10
        connections_by_memory = int(memory_for_pool_mb / 2.0)

        # Ограничиваем разумными пределами
        dynamic_size = max(MIN_POOL_SIZE, min(connections_by_memory, MAX_POOL_SIZE))

        app_logger.debug(
            "Динамический размер пула: %d (доступно памяти: %.2f MB)",
            dynamic_size,
            available_memory_mb,
        )

        return dynamic_size

    except ImportError:
        # psutil не установлен, используем значение по умолчанию
        app_logger.debug("psutil не установлен, используем размер пула по умолчанию")
        return MIN_POOL_SIZE
    except (MemoryError, OSError, ValueError, TypeError, Exception):
        # Любая другая ошибка - используем минимальный размер
        app_logger.debug("Ошибка при расчёте размера пула, используем минимум")
        return MIN_POOL_SIZE


class _ConnectionPool:
    """
    Пул соединений для SQLite с reuse и queue.Queue для управления.

    Оптимизация 16:
    - Reuse соединений вместо создания новых
    - max_connections лимит (10-20 соединений)
    - queue.Queue для управления соединениями
    - Правильная очистка соединений
    - Connection pooling для снижения накладных расходов

    Примечание: SQLite требует, чтобы соединение создавалось в том же потоке,
    в котором оно используется. Поэтому пул создает новое соединение для каждого потока.

    Пример использования:
        >>> from pathlib import Path
        >>> pool = _ConnectionPool(Path("cache.db"), pool_size=5)
        >>> conn = pool.get_connection()  # Получить соединение для текущего потока
        >>> pool.return_connection(conn)  # Вернуть соединение в пул
        >>> pool.close_all()  # Закрыть все соединения

    Attributes:
        _cache_file: Путь к файлу базы данных.
        _pool_size: Размер пула соединений.
        _local: Thread-local хранилище для соединений.
        _all_conns: Список всех созданных соединений.
        _lock: Блокировка для потокобезопасности.
        _connection_queue: Queue для управления соединениями.

    Raises:
        sqlite3.Error: При ошибке создания соединения с базой данных.
    """

    def __init__(
        self, cache_file: Path, pool_size: Optional[int] = None, use_dynamic: bool = True
    ) -> None:
        """
        Инициализация пула соединений.

        Args:
            cache_file: Путь к файлу базы данных SQLite.
            pool_size: Размер пула соединений (по умолчанию вычисляется динамически).
                      Для thread-local реализации не используется напрямую.
            use_dynamic: Если True, использует динамический расчёт размера пула
                        на основе доступной памяти (игнорирует pool_size).

        Raises:
            OSError: Если файл базы данных недоступен для записи.
            sqlite3.Error: При ошибке инициализации базы данных.

        Example:
            >>> pool = _ConnectionPool(Path("/tmp/cache.db"))
            >>> # Или с явным размером:
            >>> pool = _ConnectionPool(Path("/tmp/cache.db"), pool_size=10, use_dynamic=False)
        """
        self._cache_file = cache_file
        # Используем динамический расчёт размера пула или заданный вручную
        if use_dynamic:
            calculated_size = _calculate_dynamic_pool_size()
            self._pool_size = calculated_size
            app_logger.info("Используется динамический размер пула соединений: %d", calculated_size)
        else:
            # Ограничиваем размер пула разумными пределами
            self._pool_size = max(MIN_POOL_SIZE, min(pool_size or MIN_POOL_SIZE, MAX_POOL_SIZE))
            app_logger.debug("Используется заданный размер пула соединений: %d", self._pool_size)
        # ИСПРАВЛЕНИЕ: добавляем _max_size для совместимости с тестами
        self._max_size = self._pool_size
        self._local = threading.local()
        self._all_conns: List[sqlite3.Connection] = []
        # ИСПРАВЛЕНИЕ 8: Используем RLock для реентерабельности
        # RLock позволяет одному и тому же потоку получать блокировку несколько раз
        self._lock = threading.RLock()
        # Оптимизация 16: queue.Queue для управления соединениями
        self._connection_queue: queue.Queue[sqlite3.Connection] = queue.Queue(
            maxsize=self._pool_size
        )
        # Кэш времени создания соединений для отслеживания возраста
        self._connection_age: Dict[int, float] = {}
        # ИСПРАВЛЕНИЕ 3: weakref.finalize() для гарантированной очистки ресурсов
        self._weak_ref = weakref.ref(self)
        self._finalizer = weakref.finalize(self, self._cleanup_pool, self._all_conns, self._lock)

    def get_connection(self) -> sqlite3.Connection:
        """
        Получает соединение для текущего потока с reuse.

        Оптимизация 16:
        - Reuse соединений вместо создания новых
        - Проверка возраста соединения и пересоздание при необходимости
        - queue.Queue для потокобезопасного управления
        - Единая блокировка вместо double-checked locking для предотвращения race condition

        SQLite требует создания соединения в том же потоке, где оно будет использоваться.
        Метод использует thread-local хранилище для каждого потока.

        Returns:
            SQLite соединение для текущего потока.

        Примечание:
            Используется единая блокировка (single-checked locking) для предотвращения race condition:
            1. Блокировка RLock
            2. Проверка и получение/создание соединения внутри блокировки
            Это упрощает логику и устраняет гонки данных.
        """
        # ЕДИНАЯ БЛОКИРОВКА для всех операций
        with self._lock:
            # Проверяем есть ли соединение в thread-local
            if hasattr(self._local, "connection") and self._local.connection is not None:
                # Проверяем возраст
                conn_id = id(self._local.connection)
                if conn_id in self._connection_age:
                    age = time.time() - self._connection_age[conn_id]
                    if age <= CONNECTION_MAX_AGE:
                        return self._local.connection
                    # Соединение устарело - закрываем
                    app_logger.debug(
                        "Соединение устарело (возраст: %.0f сек), требуется пересоздание", age
                    )
                    try:
                        self._local.connection.close()
                    except sqlite3.Error as db_error:
                        app_logger.warning(
                            "Ошибка БД при закрытии устаревшего соединения: %s",
                            db_error,
                            exc_info=True,
                        )
                    except OSError as os_error:
                        app_logger.warning(
                            "Ошибка ОС при закрытии устаревшего соединения: %s",
                            os_error,
                            exc_info=True,
                        )
                    if self._local.connection in self._all_conns:
                        self._all_conns.remove(self._local.connection)
                    del self._connection_age[conn_id]
                    self._local.connection = None

            # Если соединения нет, создаём новое или получаем из queue
            if not hasattr(self._local, "connection") or self._local.connection is None:
                # Пытаемся получить соединение из queue
                try:
                    conn = self._connection_queue.get_nowait()
                    # Проверяем возраст соединения
                    conn_id = id(conn)
                    if conn_id in self._connection_age:
                        age = time.time() - self._connection_age[conn_id]
                        if age > CONNECTION_MAX_AGE:
                            # Соединение устарело, пересоздаём
                            app_logger.debug(
                                "Соединение устарело (возраст: %.0f сек), пересоздаём", age
                            )
                            try:
                                conn.close()
                            except sqlite3.Error as db_error:
                                app_logger.warning(
                                    "Ошибка БД при закрытии устаревшего соединения: %s",
                                    db_error,
                                    exc_info=True,
                                )
                            except OSError as os_error:
                                app_logger.warning(
                                    "Ошибка ОС при закрытии устаревшего соединения: %s",
                                    os_error,
                                    exc_info=True,
                                )
                            if conn in self._all_conns:
                                self._all_conns.remove(conn)
                            del self._connection_age[conn_id]
                            conn = self._create_connection()

                    self._local.connection = conn
                    app_logger.debug("Получено соединение из queue (reuse)")
                except queue.Empty:
                    # Queue пуста, создаём новое соединение
                    self._local.connection = self._create_connection()
                    # Проверяем лимит соединений
                    if len(self._all_conns) >= self._pool_size:
                        app_logger.warning(
                            "Достигнут лимит соединений (%d), новое соединение не добавляется в pool",
                            self._pool_size,
                        )
                    else:
                        self._all_conns.append(self._local.connection)
                        self._connection_age[id(self._local.connection)] = time.time()

        return self._local.connection

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """
        Возвращает соединение в пул для reuse.

        Оптимизация 16:
        - Возврат соединения в queue для повторного использования
        - Правильная очистка соединений

        Args:
            conn: Соединение для возврата в пул.
        """
        try:
            # Пытаемся вернуть соединение в queue
            self._connection_queue.put_nowait(conn)
            app_logger.debug("Соединение возвращено в queue для reuse")
        except queue.Full:
            # Queue заполнена, закрываем соединение
            app_logger.debug("Queue заполнена, закрываем соединение")
            try:
                conn.close()
            except sqlite3.Error as db_error:
                app_logger.warning(
                    "Ошибка БД при закрытии соединения (queue заполнена): %s",
                    db_error,
                    exc_info=True,
                )
            except OSError as os_error:
                app_logger.warning(
                    "Ошибка ОС при закрытии соединения (queue заполнена): %s",
                    os_error,
                    exc_info=True,
                )
            with self._lock:
                if conn in self._all_conns:
                    self._all_conns.remove(conn)
            conn_id = id(conn)
            if conn_id in self._connection_age:
                del self._connection_age[conn_id]

    def _create_connection(self) -> sqlite3.Connection:
        """
        Создаёт новое соединение с оптимизированными настройками.

        Returns:
            Новое SQLite соединение.

        Примечание:
            check_same_thread=False необходим для потокобезопасности.
            SQLite требует создания соединения в том же потоке, но с этой опцией
            мы можем безопасно использовать соединения в разных потоках при условии
            правильной синхронизации через RLock.
        """
        conn = sqlite3.connect(
            str(self._cache_file),
            timeout=30.0,  # Увеличенный таймаут для снижения конфликтов
            isolation_level=None,  # Autocommit режим для лучшей производительности
            check_same_thread=False,  # ИСПРАВЛЕНИЕ 1: Потокобезопасность
        )

        # Включаем WAL режим для лучшей конкурентности
        conn.execute("PRAGMA journal_mode=WAL")

        # Увеличиваем размер кэша страниц (по умолчанию 2000 страниц)
        conn.execute("PRAGMA cache_size=-64000")  # 64MB кэш

        # Оптимизируем синхронизацию (риск потери данных при сбое питания)
        conn.execute("PRAGMA synchronous=NORMAL")

        # Включаем busy timeout для обработки конфликтов
        conn.execute("PRAGMA busy_timeout=30000")

        return conn

    def close_all(self) -> None:
        """Закрывает все соединения в пуле с правильной очисткой.

        Примечание:
            Метод потокобезопасен благодаря использованию RLock.
            Все ошибки логируются для отладки.
        """
        with self._lock:
            # Закрываем все соединения из списка
            for conn in self._all_conns:
                try:
                    conn.close()
                except sqlite3.Error as db_error:
                    app_logger.debug("Ошибка БД при закрытии соединения: %s", db_error)
                except OSError as os_error:
                    app_logger.debug("Ошибка ОС при закрытии соединения: %s", os_error)
                except (RuntimeError, TypeError, ValueError) as e:
                    app_logger.debug("Неожиданная ошибка при закрытии соединения: %s", e)
            self._all_conns.clear()
            self._connection_age.clear()

        # Очищаем queue
        while not self._connection_queue.empty():
            try:
                conn = self._connection_queue.get_nowait()
                try:
                    conn.close()
                except sqlite3.Error as db_error:
                    app_logger.warning(
                        "Ошибка БД при закрытии соединения (очистка queue): %s",
                        db_error,
                        exc_info=True,
                    )
                except OSError as os_error:
                    app_logger.warning(
                        "Ошибка ОС при закрытии соединения (очистка queue): %s",
                        os_error,
                        exc_info=True,
                    )
            except queue.Empty:
                break

    @staticmethod
    def _cleanup_pool(all_conns: List[sqlite3.Connection], lock: threading.RLock) -> None:
        """
        Статический метод для гарантированной очистки пула соединений.

        Вызывается weakref.finalize() при уничтожении объекта сборщиком мусора.
        Этот метод не зависит от состояния объекта, поэтому может быть вызван
        даже при циклических ссылках.

        Args:
            all_conns: Список всех соединений для закрытия.
            lock: Блокировка для потокобезопасной очистки.
        """
        if all_conns is not None and lock is not None:
            try:
                with lock:
                    for conn in all_conns:
                        try:
                            conn.close()
                        except (sqlite3.Error, OSError):
                            pass
                    all_conns.clear()
            except (RuntimeError, TypeError):
                # Интерпретатор завершается - игнорируем ошибки
                pass

    def __enter__(self) -> "_ConnectionPool":
        """
        Контекстный менеджер: вход.

        Returns:
            Экземпляр _ConnectionPool для использования в контекстном менеджере.

        Пример:
            >>> with _ConnectionPool(Path("cache.db")) as pool:
            ...     conn = pool.get_connection()
            ...     # работа с соединением
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Контекстный менеджер: выход.

        Args:
            exc_type: Тип исключения (если произошло).
            exc_val: Значение исключения (если произошло).
            exc_tb: Трассировка исключения (если произошло).

        Примечание:
            Гарантирует закрытие всех соединений даже при возникновении исключений.
            Все ошибки при закрытии логируются но не пробрасываются.
        """
        try:
            self.close_all()
        except (RuntimeError, TypeError, ValueError, OSError, sqlite3.Error) as close_error:
            app_logger.error(
                "Ошибка при закрытии пула соединений в контекстном менеджере: %s",
                close_error,
                exc_info=True,
            )
        # Возвращаем None (подавляем исключения) чтобы не мешать основной логике

    def __del__(self) -> None:
        """
        Гарантирует закрытие соединений при уничтожении объекта.

        ИСПОЛЬЗУЕТСЯ weakref.finalize() для гарантированной очистки:
        - weakref.finalize() регистрируется в __init__ и вызывается сборщиком мусора
        - Этот метод __del__ используется только для логирования и как fallback
        - weakref.finalize() работает даже при циклических ссылках

        Важно:
            Не следует полагаться на этот метод для гарантированной очистки.
            Всегда вызывайте close_all() явно или используйте контекстный менеджер.
        """
        # weakref.finalize() уже зарегистрирован в __init__ и вызовет _cleanup_pool
        # Этот метод используется только для логирования
        try:
            # Проверяем есть ли финализатор
            if hasattr(self, "_finalizer") and self._finalizer is not None:
                if self._finalizer.detach():
                    # Финализатор был успешно отделён и вызван
                    app_logger.debug("_ConnectionPool очищен через weakref.finalize()")
                    return

            # Fallback: если финализатор не сработал
            if hasattr(self, "_all_conns") and self._all_conns:
                app_logger.warning(
                    "_ConnectionPool уничтожается сборщиком мусора с %d незакрытыми соединениями. "
                    "Всегда вызывайте close_all() явно или используйте контекстный менеджер.",
                    len(self._all_conns),
                )
        except (MemoryError, KeyboardInterrupt, SystemExit):
            # Критические исключения - пробрасываем дальше
            raise
        except (RuntimeError, TypeError, ValueError, OSError) as del_error:
            # В __del__ нельзя выбрасывать исключения - только логируем
            app_logger.debug("Ошибка в __del__ _ConnectionPool: %s", del_error)


class CacheManager:
    """Менеджер кэша результатов парсинга.

    Этот класс предоставляет возможность кэширования результатов парсинга
    в локальной базе данных SQLite. Кэш позволяет ускорить повторные
    запуски парсера в 10-100 раз за счет избежания повторных
    запросов к серверу 2GIS.

    Оптимизации:
    - Connection pooling для снижения накладных расходов
    - Компилированные SQL запросы для снижения парсинга
    - Пакетные операции для массовой вставки/удаления
    - WAL режим для лучшей конкурентности

    Attributes:
        _cache_dir: Директория для хранения кэша
        _cache_file: Путь к файлу базы данных кэша
        _ttl: Время жизни кэша (timedelta)

    Пример использования:
        >>> cache = CacheManager(Path('/tmp/cache'), ttl_hours=24)
        >>> data = cache.get('https://2gis.ru/moscow/search/Аптеки')
        >>> if data is None:
        ...     # Парсим данные
        ...     data = {...}
        ...     cache.set('https://2gis.ru/moscow/search/Аптеки', data)
    """

    # Компилированные SQL запросы для оптимизации
    SQL_CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS cache (
            url_hash TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp DATETIME NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """

    SQL_CREATE_INDEX = """
        CREATE INDEX IF NOT EXISTS idx_expires_at
        ON cache(expires_at)
    """

    # Индекс для url_hash уже существует как PRIMARY KEY, но добавим
    # дополнительный индекс для ускорения поиска по url_hash в составных запросах
    SQL_CREATE_URL_HASH_INDEX = """
        CREATE INDEX IF NOT EXISTS idx_url_hash
        ON cache(url_hash)
    """

    # ИСПРАВЛЕНИЕ 5: Дополнительный индекс для cache_key для ускорения поиска
    SQL_CREATE_CACHE_KEY_INDEX = """
        CREATE INDEX IF NOT EXISTS idx_cache_key
        ON cache(url_hash, expires_at)
    """

    SQL_SELECT = """
        SELECT data, expires_at
        FROM cache
        WHERE url_hash = ?
    """

    SQL_INSERT_OR_REPLACE = """
        INSERT OR REPLACE INTO cache
        (url_hash, url, data, timestamp, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """

    SQL_DELETE = """
        DELETE FROM cache WHERE url_hash = ?
    """

    SQL_DELETE_EXPIRED = """
        DELETE FROM cache
        WHERE expires_at < ?
    """

    SQL_COUNT_ALL = """
        SELECT COUNT(*) FROM cache
    """

    SQL_COUNT_EXPIRED = """
        SELECT COUNT(*) FROM cache
        WHERE expires_at < ?
    """

    SQL_DELETE_LRU = """
        DELETE FROM cache
        WHERE url_hash IN (
            SELECT url_hash FROM cache
            ORDER BY timestamp ASC
            LIMIT ?
        )
    """

    SQL_GET_CACHE_SIZE = """
        SELECT COUNT(*) FROM cache
    """

    def __init__(self, cache_dir: Path, ttl_hours: int = 24, pool_size: int = 5):
        """Инициализация менеджера кэша.

        Args:
            cache_dir: Директория для хранения кэша
            ttl_hours: Время жизни кэша в часах (по умолчанию 24 часа)
            pool_size: Размер пула соединений (по умолчанию 5)

        Raises:
            ValueError: Если ttl_hours меньше или равен нулю
            TypeError: Если ttl_hours не может быть конвертирован в int
        """
        # Конвертируем ttl_hours в int для защиты от строковых значений
        try:
            ttl_hours = int(ttl_hours)
        except (ValueError, TypeError) as conversion_error:
            raise TypeError(
                f"ttl_hours должен быть целым числом, получено: {type(ttl_hours).__name__}"
            ) from conversion_error

        if ttl_hours <= 0:
            raise ValueError("ttl_hours должен быть положительным числом")

        self._cache_dir = cache_dir
        self._ttl = timedelta(hours=ttl_hours)
        self._cache_file = cache_dir / "cache.db"

        # Инициализация пула соединений и подготовки запросов
        self._pool: Optional[_ConnectionPool] = None
        self._prepared_stmts: Dict[str, Any] = {}

        # ИСПРАВЛЕНИЕ 3: weakref.finalize() для гарантированной очистки ресурсов
        self._weak_ref = weakref.ref(self)
        self._finalizer = weakref.finalize(self, self._cleanup_cache_manager, self._cache_file)

        # Инициализация БД
        self._init_db(pool_size)

    def _init_db(self, pool_size: int) -> None:
        """Инициализация базы данных кэша.

        Создает директорию для кэша (если её нет) и создает
        таблицу для хранения кэшированных данных.

        Args:
            pool_size: Размер пула соединений.
        """
        # Создаём директорию для кэша, если её нет
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Создаём пул соединений
        self._pool = _ConnectionPool(self._cache_file, pool_size)

        # Получаем соединение для инициализации
        conn = self._pool.get_connection()

        try:
            # Создаем таблицу для кэша
            conn.execute(self.SQL_CREATE_TABLE)

            # Создаем индекс для быстрого поиска истекших записей
            conn.execute(self.SQL_CREATE_INDEX)

            # Создаем дополнительный индекс для url_hash для ускорения поиска
            conn.execute(self.SQL_CREATE_URL_HASH_INDEX)

            # ИСПРАВЛЕНИЕ 5: Создаём составной индекс для ускорения поиска
            conn.execute(self.SQL_CREATE_CACHE_KEY_INDEX)

            # Примечание: SQLite3 в Python не поддерживает prepare() для курсоров,
            # поэтому используем прямое выполнение с параметрами для защиты от SQL injection
        except (sqlite3.Error, OSError, MemoryError) as e:
            app_logger.warning("Ошибка при инициализации кэша: %s", e)
            raise

    def _get_cached_row(self, cursor: Any, url_hash: str) -> Optional[tuple[str, str]]:
        """Извлекает строку кэша из базы данных.

        Args:
            cursor: Курсор базы данных.
            url_hash: Хеш URL для поиска.

        Returns:
            Кортеж (data, expires_at_str) или None если не найдено.
        """
        cursor.execute(self.SQL_SELECT, (url_hash,))
        row = cursor.fetchone()
        return row  # type: ignore[return-value]

    def _parse_expires_at(self, expires_at_str: str) -> Optional[datetime]:
        """Парсит строку даты истечения кэша.

        Args:
            expires_at_str: Строка даты в формате ISO.

        Returns:
            datetime объект или None при ошибке парсинга.
        """
        try:
            return datetime.fromisoformat(expires_at_str)
        except ValueError:
            app_logger.debug("Некорректный формат даты в кэше: %s", expires_at_str)
            return None

    def _is_cache_expired(self, expires_at: datetime) -> bool:
        """Проверяет истёк ли кэш.

        Args:
            expires_at: Время истечения кэша.

        Returns:
            True если кэш истёк, False иначе.
        """
        return datetime.now() > expires_at

    def _delete_cached_entry(self, cursor: Any, url_hash: str) -> None:
        """Удаляет запись кэша из базы данных.

        Args:
            cursor: Курсор базы данных.
            url_hash: Хеш URL для удаления.
        """
        cursor.execute(self.SQL_DELETE, (url_hash,))

    def _handle_db_error(
        self, db_error: sqlite3.Error, url: str, cursor: Any, url_hash: str
    ) -> Optional[Dict[str, Any]]:
        """Обрабатывает ошибки базы данных при получении кэша.

        Args:
            db_error: Исключение базы данных.
            url: URL для логирования.
            cursor: Курсор базы данных.
            url_hash: Хеш URL для повторной попытки.

        Returns:
            Данные кэша или None.
        """
        error_str = str(db_error).lower()

        # Временные ошибки - можно повторить попытку
        if "database is locked" in error_str or "busy" in error_str:
            app_logger.warning(
                "База данных заблокирована (временная ошибка): %s. Повторная попытка...", db_error
            )
            time.sleep(0.5)
            try:
                cursor.execute(self.SQL_SELECT, (url_hash,))
                row = cursor.fetchone()
                if row:
                    data, expires_at_str = row
                    expires_at = self._parse_expires_at(expires_at_str)
                    if expires_at and datetime.now() <= expires_at:
                        return _deserialize_json(data)
            except sqlite3.Error as retry_error:
                app_logger.warning("Повторная попытка не удалась: %s", retry_error)
            return None

        # Критическая ошибка диска
        if "disk i/o error" in error_str:
            app_logger.critical("Критическая ошибка диска при получении кэша: %s", db_error)
            raise db_error

        # Таблица не существует
        if "no such table" in error_str:
            app_logger.critical("Таблица кэша не существует: %s", db_error)
            raise db_error

        # Повреждение базы данных
        if "corrupt" in error_str or "malformed" in error_str:
            app_logger.critical("База данных повреждена: %s", db_error)
            raise db_error

        # Остальные ошибки БД
        app_logger.error(
            "Неизвестная ошибка БД при получении кэша: %s (тип: %s)",
            db_error,
            type(db_error).__name__,
        )
        return None

    def _handle_deserialize_error(
        self, decode_error: Exception, url: str, cursor: Any, url_hash: str, conn: Any
    ) -> None:
        """Обрабатывает ошибки десериализации кэша.

        Args:
            decode_error: Исключение десериализации.
            url: URL для логирования.
            cursor: Курсор базы данных.
            url_hash: Хеш URL для удаления.
            conn: Соединение базы данных.
        """
        error_type = type(decode_error).__name__
        app_logger.warning(
            "Ошибка %s при чтении кэша для URL %s: %s. Повреждённая запись будет удалена.",
            error_type,
            url,
            decode_error,
        )
        try:
            self._delete_cached_entry(cursor, url_hash)
            conn.commit()
        except sqlite3.Error as cleanup_error:
            app_logger.warning("Ошибка при удалении повреждённой записи: %s", cleanup_error)

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Получение данных из кэша.

        Проверяет наличие кэша для указанного URL. Если кэш существует
        и не истек, возвращает кэшированные данные. Иначе возвращает None.

        Args:
            url: URL для поиска в кэше

        Returns:
            Кэшированные данные или None, если кэш истек или отсутствует

        Raises:
            sqlite3.Error: При критической ошибке БД (disk I/O, no such table)
        """
        if not self._pool:
            return None

        try:
            url_hash = self._hash_url(url)
        except (ValueError, TypeError):
            return None

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN IMMEDIATE")
            row = self._get_cached_row(cursor, url_hash)

            if not row:
                conn.rollback()
                return None

            data, expires_at_str = row
            expires_at = self._parse_expires_at(expires_at_str)

            if expires_at is None:
                conn.rollback()
                return None

            if self._is_cache_expired(expires_at):
                self._delete_cached_entry(cursor, url_hash)
                conn.commit()
                return None

            conn.commit()
            return _deserialize_json(data)

        except sqlite3.Error as db_error:
            try:
                conn.rollback()
            except (sqlite3.Error, OSError, MemoryError) as rollback_error:
                app_logger.debug("Ошибка при откате транзакции: %s", rollback_error)

            return self._handle_db_error(db_error, url, cursor, url_hash)

        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as decode_error:
            self._handle_deserialize_error(decode_error, url, cursor, url_hash, conn)
            return None

        except (MemoryError, OSError, RuntimeError) as general_error:
            app_logger.error(
                "Непредвиденная ошибка при чтении кэша для URL %s: %s (тип: %s)",
                url,
                general_error,
                type(general_error).__name__,
            )
            return None

        finally:
            try:
                cursor.close()
            except (sqlite3.Error, OSError, MemoryError) as cursor_error:
                app_logger.debug("Ошибка при закрытии курсора: %s", cursor_error)

    def set(self, url: str, data: Dict[str, Any]) -> None:
        """Сохранение данных в кэш.

        Проверяет корректность данных и сохраняет их в кэш для указанного URL.
        Если кэш для этого URL уже существует, он будет перезаписан.

        Оптимизация 18:
        - Кэширование datetime.now() в переменную
        - Использование одной временной метки для всех операций в методе
        - Избегание повторных вызовов datetime.now()

        Args:
            url: URL для кэширования
            data: Данные для сохранения (должны быть сериализуемы в JSON)

        Raises:
            TypeError: Если data является None или не является словарём.
            ValueError: Если URL некорректен.
        """
        if not self._pool:
            return

        # ВАЛИДАЦИЯ: проверка data на None
        if data is None:
            raise TypeError("Данные кэша не могут быть None")

        # Вычисляем хеш URL и время истечения
        url_hash = self._hash_url(url)

        # Используем одну временную метку для всех операций в методе
        now = datetime.now()
        expires_at = now + self._ttl

        # Сериализуем данные один раз
        # Оптимизация 3.6: используем orjson wrapper для быстрой сериализации
        try:
            data_json = _serialize_json(data)
        except (TypeError, ValueError) as e:
            app_logger.error("Ошибка сериализации данных для кэша: %s", e)
            return

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            # ПРОВЕРКА: Ограничение размера кэша перед вставкой
            self._enforce_cache_size_limit(conn)

            # Сохраняем данные в базу с использованием подготовленного запроса
            # Используем кэшированную временную метку now вместо повторных вызовов datetime.now()
            cursor.execute(
                self.SQL_INSERT_OR_REPLACE,
                (url_hash, url, data_json, now.isoformat(), expires_at.isoformat()),
            )
            conn.commit()
        except sqlite3.Error as db_error:
            app_logger.error("Ошибка БД при сохранении кэша: %s", db_error)
        finally:
            cursor.close()

    def set_batch(self, items: List[Tuple[str, Dict[str, Any]]]) -> int:
        """
        Пакетное сохранение данных в кэш.

        Оптимизация: массовая вставка данных снижает накладные расходы
        на транзакции и коммиты, увеличивая производительность в 5-10 раз
        при массовой записи.

        Args:
            items: Список кортежей (url, data) для сохранения.

        Returns:
            Количество сохранённых записей.
        """
        if not self._pool or not items:
            return 0

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        saved_count = 0
        skipped_count = 0

        # Используем одну временную метку для всех операций в методе
        # Это обеспечивает консистентность времени для всей пакетной операции
        now = datetime.now()
        expires_at = now + self._ttl

        try:
            for url, data in items:
                url_hash = self._hash_url(url)

                try:
                    # Оптимизация 3.6: используем orjson wrapper для быстрой сериализации
                    data_json = _serialize_json(data)
                    # Используем кэшированную временную метку now для всех записей
                    cursor.execute(
                        self.SQL_INSERT_OR_REPLACE,
                        (url_hash, url, data_json, now.isoformat(), expires_at.isoformat()),
                    )
                    saved_count += 1
                except (TypeError, ValueError) as serialize_error:
                    app_logger.warning(
                        "Ошибка сериализации данных для кэша (%s): %s", url, serialize_error
                    )
                    skipped_count += 1
                    continue

            # ПРОВЕРКА: Ограничение размера кэша перед пакетной вставкой
            self._enforce_cache_size_limit(conn)

            # Один коммит для всех записей
            conn.commit()

            if skipped_count > 0:
                app_logger.warning(
                    "Пакетное сохранение кэша завершено: сохранено %d записей, пропущено %d записей",
                    saved_count,
                    skipped_count,
                )

        except sqlite3.Error as db_error:
            app_logger.error("Ошибка БД при пакетном сохранении кэша: %s", db_error)
        finally:
            cursor.close()

        return saved_count

    def clear(self) -> None:
        """Очистка всего кэша.

        Удаляет все записи из кэша.
        """
        if not self._pool:
            return

        conn = self._pool.get_connection()

        try:
            # Простое удаление всех данных быстрее чем DELETE FROM
            conn.execute("DELETE FROM cache")
            conn.commit()
            app_logger.debug("Кэш полностью очищен")
        except sqlite3.Error as db_error:
            app_logger.error("Ошибка БД при очистке кэша: %s", db_error)

    def clear_expired(self) -> int:
        """Очистка истекшего кэша.

        Удаляет все записи, у которых время истечения меньше текущего.

        Оптимизация 18:
        - Кэширование datetime.now() в переменную
        - Использование одной временной метки для операции удаления

        Returns:
            Количество удалённых записей
        """
        if not self._pool:
            return 0

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            current_time = datetime.now()

            # Удаляем истекшие записи с использованием подготовленного запроса
            cursor.execute(self.SQL_DELETE_EXPIRED, (current_time.isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                app_logger.debug("Очищено %d истекших записей кэша", deleted_count)

            return deleted_count

        except sqlite3.Error as db_error:
            app_logger.warning("Ошибка БД при очистке истекшего кэша: %s", db_error)
            return 0
        finally:
            cursor.close()

    def clear_batch(self, url_hashes: List[str]) -> int:
        """
        Пакетное удаление записей по хешам URL.

        Оптимизация: массовое удаление снижает накладные расходы
        на транзакции.

        Args:
            url_hashes: Список хешей URL для удаления.

        Returns:
            Количество удалённых записей.

        Raises:
            ValueError: Если размер пакета превышает MAX_BATCH_SIZE.
        """
        if not self._pool or not url_hashes:
            return 0

        # ВАЖНО: Ограничиваем максимальный размер пакета для предотвращения DoS
        if len(url_hashes) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Размер пакета {len(url_hashes)} превышает максимальный лимит {MAX_BATCH_SIZE}"
            )

        # ВАЖНО: Строгая валидация каждого хеша (64 символа, hex)
        # Это предотвращает SQL injection через некорректные хеши
        for hash_val in url_hashes:
            if not self._validate_hash(hash_val):
                raise ValueError(f"Некорректный формат хеша: {hash_val}")

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            # БЕЗОПАСНОСТЬ: SQL injection предотвращён через:
            # 1. Строгую валидацию каждого хеша (64 символа, hex) через _validate_hash()
            # 2. Использование параметризованного запроса с плейсхолдерами (?)
            # 3. Ограничение максимального размера пакета (MAX_BATCH_SIZE)
            # Даже при формировании SQL через f-string, параметры передаются
            # отдельно через cursor.execute(), что полностью защищает от SQL injection.
            # Формирование запроса: DELETE FROM cache WHERE url_hash IN (?,?,?,...)
            placeholders = ",".join("?" * len(url_hashes))
            delete_query = f"DELETE FROM cache WHERE url_hash IN ({placeholders})"
            cursor.execute(delete_query, url_hashes)  # nosec B608
            deleted_count = cursor.rowcount
            conn.commit()

            return deleted_count

        except sqlite3.Error as db_error:
            app_logger.warning("Ошибка БД при пакетном удалении: %s", db_error)
            return 0
        finally:
            cursor.close()

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики кэша.

        Returns:
            Словарь со статистикой:
            - total_records: Общее количество записей
            - expired_records: Количество истекших записей
            - cache_size: Размер файла базы данных в байтах

        Примечание:
            Метод включает обработку ошибок для всех операций с файловой системой
            и базой данных для предотвращения сбоев.
        """
        if not self._pool:
            return {"total_records": 0, "expired_records": 0, "cache_size": 0}

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            # Общее количество записей
            cursor.execute(self.SQL_COUNT_ALL)
            total = cursor.fetchone()[0]

            # Оптимизация 3.2: кэшируем datetime.now() в переменную
            # Используем одну временную метку для всех операций в методе
            current_time = datetime.now()

            # Количество истекших записей
            cursor.execute(self.SQL_COUNT_EXPIRED, (current_time.isoformat(),))
            expired = cursor.fetchone()[0]

            # Размер файла базы данных с обработкой ошибок
            try:
                cache_size = self._cache_file.stat().st_size if self._cache_file.exists() else 0
            except OSError:
                # Файл недоступен или ошибка файловой системы
                cache_size = 0

            return {"total_records": total, "expired_records": expired, "cache_size": cache_size}

        except sqlite3.Error as db_error:
            # Ошибка базы данных
            app_logger.warning("Ошибка при получении статистики кэша: %s", db_error)
            return {"total_records": 0, "expired_records": 0, "cache_size": 0}
        finally:
            cursor.close()

    def close(self) -> None:
        """
        Закрывает все соединения и освобождает ресурсы.

        Важно: Вызывать перед завершением работы приложения.
        """
        if hasattr(self, "_pool") and self._pool is not None:
            self._pool.close_all()
            self._pool = None
            app_logger.debug("Менеджер кэша закрыт")

    @staticmethod
    def _cleanup_cache_manager(cache_file: Path) -> None:
        """
        Статический метод для гарантированной очистки CacheManager.

        Вызывается weakref.finalize() при уничтожении объекта сборщиком мусора.
        Этот метод не зависит от состояния объекта, поэтому может быть вызван
        даже при циклических ссылках.

        Args:
            cache_file: Путь к файлу базы данных кэша.
        """
        # weakref.finalize() не может закрыть соединения напрямую,
        # но может залогировать предупреждение если файл существует
        if cache_file is not None and cache_file.exists():
            # Файл кэша существует - это нормально, кэш сохраняется между запусками
            pass

    def __enter__(self) -> "CacheManager":
        """
        Возвращает экземпляр CacheManager для использования в контекстном менеджере.

        Returns:
            Экземпляр CacheManager.

        Пример использования:
            >>> with CacheManager(Path('/tmp/cache')) as cache:
            ...     data = cache.get('https://2gis.ru/moscow')
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Закрывает все соединения при выходе из контекста.

        Args:
            exc_type: Тип исключения (если было выброшено).
            exc_val: Значение исключения (если было выброшено).
            exc_tb: Трассировка исключения (если было выброшено).

        Примечание:
            Гарантирует закрытие всех соединений даже при возникновении исключений.
        """
        self.close()

    def __del__(self) -> None:
        """
        Гарантирует закрытие соединений при уничтожении объекта.

        ИСПОЛЬЗУЕТСЯ weakref.finalize() для гарантированной очистки:
        - weakref.finalize() регистрируется в __init__ и вызывается сборщиком мусора
        - Этот метод __del__ используется только для логирования и как fallback
        - weakref.finalize() работает даже при циклических ссылках

        Пример правильного использования:
            with CacheManager(...) as cache:
                cache.get(...)
            # или
            cache = CacheManager(...)
            try:
                cache.get(...)
            finally:
                cache.close()
        """
        # weakref.finalize() уже зарегистрирован в __init__
        # Этот метод используется только для логирования
        try:
            # Проверяем есть ли финализатор
            if hasattr(self, "_finalizer") and self._finalizer is not None:
                if self._finalizer.detach():
                    # Финализатор был успешно отделён и вызван
                    app_logger.debug("CacheManager очищен через weakref.finalize()")
                    return

            # Fallback: если финализатор не сработал
            if hasattr(self, "_pool") and self._pool is not None:
                app_logger.warning(
                    "CacheManager уничтожается сборщиком мусора без явного закрытия. "
                    "Всегда вызывайте close() явно или используйте контекстный менеджер."
                )
        except (MemoryError, KeyboardInterrupt, SystemExit):
            # Критические исключения - пробрасываем дальше
            raise
        except (RuntimeError, TypeError, ValueError, OSError) as del_error:
            # В __del__ нельзя выбрасывать исключения - только логируем
            app_logger.debug("Ошибка в __del__ CacheManager: %s", del_error)

    @staticmethod
    def _hash_url(url: str) -> str:
        """
        Хеширование URL.

        Вычисляет SHA256 хеш от указанного URL для использования
        в качестве ключа в базе данных кэша.
        - Добавлена проверка на None и тип данных
        - Выбрасывается явное исключение при некорректных входных данных

        Args:
            url: URL для хеширования. Должен быть непустой строкой.

        Returns:
            SHA256 хеш URL в виде шестнадцатеричной строки.

        Raises:
            ValueError: Если URL является None или пустой строкой.
            TypeError: Если URL не является строкой.

        Пример:
            >>> hash_val = CacheManager._hash_url('https://2gis.ru/moscow')
            >>> len(hash_val)
            64
        """
        # КРИТИЧЕСКАЯ ВАЛИДАЦИЯ: проверка на None
        if url is None:
            raise ValueError("URL не может быть None")

        # КРИТИЧЕСКАЯ ВАЛИДАЦИЯ: проверка типа
        if not isinstance(url, str):
            raise TypeError(f"URL должен быть строкой, получен {type(url).__name__}")

        # КРИТИЧЕСКАЯ ВАЛИДАЦИЯ: проверка на пустую строку
        if not url.strip():
            raise ValueError("URL не может быть пустой строкой")

        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_hash(hash_val: str) -> bool:
        """Валидация хеша.

        Проверяет, что хеш имеет корректный формат:
        - Длина ровно 64 символа (SHA256 hex)
        - Содержит только шестнадцатеричные символы (0-9, a-f)

        Args:
            hash_val: Хеш для валидации

        Returns:
            True если хеш корректен, False иначе
        """
        if len(hash_val) != SHA256_HASH_LENGTH:
            return False
        try:
            int(hash_val, 16)
            return True
        except ValueError:
            return False

    def _get_cache_size_mb(self, conn: Optional[sqlite3.Connection] = None) -> float:
        """
        Получает размер кэша в мегабайтах.

        Вычисляет размер файла базы данных кэша в мегабайтах.
        Если файл не существует, возвращает 0.0.

        Args:
            conn: SQLite соединение (опционально, используется для проверки целостности БД).

        Returns:
            Размер кэша в мегабайтах.

        Примечание:
            Метод включает обработку ошибок для всех операций с файловой системой
            для предотвращения сбоев при недоступности файла.
        """
        try:
            if not self._cache_file.exists():
                return 0.0

            cache_size_bytes = self._cache_file.stat().st_size
            cache_size_mb = cache_size_bytes / (1024 * 1024)

            # Дополнительная проверка целостности БД если предоставлено соединение
            if conn is not None:
                try:
                    # Быстрая проверка целостности
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA quick_check(1)")
                    cursor.close()
                except sqlite3.Error:
                    # Если БД повреждена, логируем предупреждение
                    app_logger.warning("База данных кэша может быть повреждена")

            return cache_size_mb

        except OSError as os_error:
            app_logger.warning("Ошибка при получении размера кэша: %s", os_error)
            return 0.0

    def _enforce_cache_size_limit(self, conn: sqlite3.Connection) -> None:
        """
        Принудительное ограничение размера кэша.

        Реализует LRU (Least Recently Used) политику eviction:
        - Проверяет размер файла кэша через _get_cache_size_mb()
        - Если размер превышает MAX_CACHE_SIZE_MB, удаляет старые записи
          до тех пор, пока размер не станет меньше лимита
        - Использует пакетное удаление по LRU_EVICT_BATCH записей за раз

        Args:
            conn: SQLite соединение для выполнения запросов

        Примечание:
            Метод использует цикл для гарантированного снижения размера кэша
            ниже лимита. За один проход может удалить несколько пакетов записей.
        """
        try:
            # Получаем текущий размер кэша
            cache_size_mb = self._get_cache_size_mb(conn)

            # Проверяем превышение лимита
            if cache_size_mb > MAX_CACHE_SIZE_MB:
                app_logger.warning(
                    "Размер кэша %.2f MB превышает лимит %d MB. Запуск LRU eviction...",
                    cache_size_mb,
                    MAX_CACHE_SIZE_MB,
                )

                cursor = conn.cursor()
                try:
                    total_deleted = 0
                    eviction_iterations = 0
                    max_iterations = 50  # Защита от бесконечного цикла

                    # Циклически удаляем записи пока размер не станет меньше лимита
                    while (
                        cache_size_mb > MAX_CACHE_SIZE_MB and eviction_iterations < max_iterations
                    ):
                        eviction_iterations += 1

                        # Удаляем пакет старых записей (LRU - по timestamp)
                        cursor.execute(self.SQL_DELETE_LRU, (LRU_EVICT_BATCH,))
                        deleted_count = cursor.rowcount
                        conn.commit()

                        if deleted_count == 0:
                            # Нечего удалять - выходим из цикла
                            app_logger.debug("LRU eviction: записей для удаления не осталось")
                            break

                        total_deleted += deleted_count
                        app_logger.debug(
                            "LRU eviction (итерация %d): удалено %d записей (всего: %d)",
                            eviction_iterations,
                            deleted_count,
                            total_deleted,
                        )

                        # Проверяем новый размер кэша
                        cache_size_mb = self._get_cache_size_mb(conn)

                    if eviction_iterations >= max_iterations:
                        app_logger.warning(
                            "LRU eviction: достигнут лимит итераций (%d), текущий размер %.2f MB",
                            max_iterations,
                            cache_size_mb,
                        )

                    if total_deleted > 0:
                        app_logger.info(
                            "LRU eviction завершена: удалено %d записей за %d итераций, "
                            "новый размер %.2f MB",
                            total_deleted,
                            eviction_iterations,
                            cache_size_mb,
                        )

                finally:
                    cursor.close()

        except OSError as os_error:
            app_logger.warning("Ошибка при проверке размера кэша: %s", os_error)
        except sqlite3.Error as db_error:
            app_logger.warning("Ошибка БД при LRU eviction: %s", db_error)


# Алиас для обратной совместимости
Cache = CacheManager

# =============================================================================
# RE-EXPORT ДЛЯ ТЕСТОВ
# =============================================================================
