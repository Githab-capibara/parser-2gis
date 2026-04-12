"""Модуль менеджера кэша для парсинга.

Предоставляет класс CacheManager для кэширования результатов парсинга
в локальной базе данных SQLite.

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.cache import CacheManager
    >>> cache = CacheManager(Path("cache"))
    >>> cache.get("some_key")  # Получение из кэша
    >>> cache.set("key", {"data": "value"})  # Сохранение в кэш
    >>> cache.close()  # Закрытие соединения

ISSUE-004: Рефакторинг - выделены вспомогательные функции в cache_utils.py
"""

import hashlib
import json
import re
import sqlite3
import time
import weakref
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

# Импорты для типизации (для совместимости с Python 3.9)
from typing import Any, Protocol

from ..constants.cache import (
    DEFAULT_CACHE_FILE_NAME,
    LRU_EVICT_BATCH,
    MAX_BATCH_SIZE,
    MAX_CACHE_SIZE_MB,
)
from ..logger.logger import logger as app_logger

# ISSUE-031: Импортируем DEFAULT_TTL_HOURS из общего модуля вместо chrome.constants
# для устранения архитектурного нарушения (cache не должен зависеть от chrome)
from ..shared_config_constants import DEFAULT_TTL_HOURS, MAX_RESPONSE_SIZE
from .cache_utils import (
    compute_crc32_cached,
    compute_data_json_hash,
    get_cache_size_mb,
    hash_url,
    is_cache_expired,
    parse_expires_at,
    validate_hash,
)
from .pool import ConnectionPool
from .serializer import JsonSerializer
from .validator import CacheDataValidator

# Пороговые значения для проверки размера кэша
_CACHE_SIZE_CHECK_THRESHOLD: int = 100  # Проверка размера только при > 100 записей
_CACHE_LRU_MAX_ITERATIONS: int = 10000  # Максимум итераций LRU eviction

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

# Кортеж строки кэша: (data, checksum, expires_at_str)
type CacheRow = tuple[str, int, str]
# Пара элемента кэша: (url, data)
type CacheItem = tuple[str, dict[str, Any]]

# Размер пула соединений по умолчанию (10 соединений — баланс между производительностью и памятью)
DEFAULT_POOL_SIZE: int = 10


# =============================================================================
# CACHED HASH COMPUTATION (P0-8: Кэширование SHA-256 для снижения CPU нагрузки)
# =============================================================================


@lru_cache(maxsize=1024)
def _compute_data_hash_cached(data: str) -> str:
    """Кэширует вычисление SHA-256 хеша для данных.

    P0-8: LRU кеш на 1024 записи для предотвращения повторных вычислений
    SHA-256 + CRC32 при каждом чтении кэша.
    """
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# =============================================================================
# PROTOCOLS FOR DATABASE CURSOR (P1-2)
# =============================================================================


class CursorProtocol(Protocol):
    """Протокол для курсора базы данных."""

    def execute(self, query: str, params: tuple[Any, ...] = ...) -> "CursorProtocol":
        """Выполняет SQL запрос."""
        ...  # pylint: disable=unnecessary-ellipsis

    def fetchone(self) -> tuple[Any, ...] | None:
        """Возвращает одну строку результата."""
        ...  # pylint: disable=unnecessary-ellipsis

    def close(self) -> None:
        """Закрывает курсор."""
        ...  # pylint: disable=unnecessary-ellipsis


class ConnectionProtocol(Protocol):
    """Протокол для соединения базы данных."""

    def cursor(self) -> CursorProtocol:
        """Создаёт курсор."""
        ...  # pylint: disable=unnecessary-ellipsis

    def commit(self) -> None:
        """Фиксирует транзакцию."""
        ...  # pylint: disable=unnecessary-ellipsis

    def rollback(self) -> None:
        """Откатывает транзакцию."""
        ...  # pylint: disable=unnecessary-ellipsis

    def execute(self, query: str, params: tuple[Any, ...] = ...) -> CursorProtocol:
        """Выполняет SQL запрос."""
        ...  # pylint: disable=unnecessary-ellipsis


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

    ISSUE-003-#20: SQL-константы определены как атрибуты класса для
    централизованного управления запросами и возможности переиспользования.

    Attributes:
        cache_dir: Директория для хранения кэша
        ttl: Время жизни кэша (timedelta)
        CREATE_TABLE_SQL: SQL-запрос создания таблицы кэша
        CREATE_INDEX_SQL: SQL-запрос создания индекса по expires_at
        CREATE_CACHE_KEY_INDEX_SQL: SQL-запрос создания составного индекса
        SELECT_SQL: SQL-запрос выборки данных по url_hash
        UPSERT_SQL: SQL-запрос вставки или замены записи
        DELETE_SQL: SQL-запрос удаления записи по url_hash
        DELETE_EXPIRED_SQL: SQL-запрос удаления истёкших записей
        COUNT_ALL_SQL: SQL-запрос подсчёта всех записей
        COUNT_EXPIRED_SQL: SQL-запрос подсчёта истёкших записей
        DELETE_LRU_SQL: SQL-запрос удаления LRU записей
        GET_CACHE_SIZE_SQL: SQL-запрос получения размера кэша

    Пример использования:
        >>> from pathlib import Path
        >>> from parser_2gis.cache import CacheManager

        # Базовое использование
        >>> cache = CacheManager(Path('/tmp/cache'), ttl_hours=24)
        >>> data = cache.get('https://2gis.ru/moscow/search/Аптеки')
        >>> if data is None:
        ...     # Парсим данные
        ...     data = {...}
        ...     cache.set('https://2gis.ru/moscow/search/Аптеки', data)

    """

    # P0-16: Константы retry логики как атрибуты класса
    _MAX_RETRIES: int = 3
    _RETRY_DELAY: float = 0.1

    # ISSUE-003-#20: Скомпилированные SQL-запросы как атрибуты класса
    # для централизованного управления и переиспользования
    CREATE_TABLE_SQL = """
        CREATE TABLE IF NOT EXISTS cache (
            url_hash TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            data TEXT NOT NULL,
            checksum INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """

    CREATE_INDEX_SQL = """
        CREATE INDEX IF NOT EXISTS idx_expires_at
        ON cache(expires_at)
    """

    # Составной индекс для range queries по url_hash + expires_at
    CREATE_CACHE_KEY_INDEX_SQL = """
        CREATE INDEX IF NOT EXISTS idx_cache_key
        ON cache(url_hash, expires_at)
    """

    SELECT_SQL = """
        SELECT data, checksum, expires_at
        FROM cache
        WHERE url_hash = ?
    """

    # ISSUE-003-#20: INSERT ... ON CONFLICT DO UPDATE вместо устаревшего INSERT OR REPLACE
    UPSERT_SQL = """
        INSERT INTO cache (url_hash, url, data, checksum, timestamp, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(url_hash) DO UPDATE SET
            url=excluded.url,
            data=excluded.data,
            checksum=excluded.checksum,
            timestamp=excluded.timestamp,
            expires_at=excluded.expires_at
    """

    DELETE_SQL = """
        DELETE FROM cache WHERE url_hash = ?
    """

    DELETE_EXPIRED_SQL = """
        DELETE FROM cache
        WHERE expires_at < ?
    """

    COUNT_ALL_SQL = """
        SELECT COUNT(*) FROM cache
    """

    COUNT_EXPIRED_SQL = """
        SELECT COUNT(*) FROM cache
        WHERE expires_at < ?
    """

    DELETE_LRU_SQL = """
        DELETE FROM cache
        WHERE url_hash IN (
            SELECT url_hash FROM cache
            ORDER BY timestamp ASC
            LIMIT ?
        )
    """

    GET_CACHE_SIZE_SQL = """
        SELECT COUNT(*) FROM cache
    """

    def __init__(
        self,
        cache_dir: Path,
        ttl_hours: int = DEFAULT_TTL_HOURS,
        pool_size: int = DEFAULT_POOL_SIZE,
        cache_file_name: str = DEFAULT_CACHE_FILE_NAME,
    ) -> None:
        """Инициализация менеджера кэша.

        Args:
            cache_dir: Директория для хранения кэша
            ttl_hours: Время жизни кэша в часах (по умолчанию 24 часа)
            pool_size: Размер пула соединений (по умолчанию 10)
            cache_file_name: Имя файла кэша (по умолчанию "cache.db")

        Raises:
            ValueError: Если ttl_hours меньше или равен нулю
            TypeError: Если ttl_hours не может быть конвертирован в int

        """
        # Конвертируем ttl_hours в int для защиты от строковых значений
        try:
            ttl_hours = int(ttl_hours)
        except (ValueError, TypeError) as conversion_error:
            raise TypeError(
                "ttl_hours должен быть целым числом, получено: %s" % type(ttl_hours).__name__
            ) from conversion_error

        if ttl_hours <= 0:
            raise ValueError("ttl_hours должен быть положительным числом")

        # D002: Валидация имени файла кэша для предотвращения инъекций
        if not cache_file_name or not isinstance(cache_file_name, str):
            raise ValueError("cache_file_name должен быть непустой строкой")
        # #144: Проверяем что имя не содержит путей
        # (до basename для совместимости с тестами)
        if "/" in cache_file_name or "\\" in cache_file_name or ".." in cache_file_name:
            raise ValueError("cache_file_name не должен содержать '/', '\\' или '..'")
        # Извлекаем только имя файла для защиты от path traversal атак
        cache_file_name = Path(cache_file_name).name
        if not cache_file_name.endswith(".db"):
            raise ValueError("cache_file_name должен заканчиваться на '.db'")
        # D002: Проверка на абсолютный путь (path traversal защита)
        if Path(cache_file_name).is_absolute():
            raise ValueError("cache_file_name не должен быть абсолютным путём")
        # D002: Проверка что имя файла содержит только безопасные символы
        if not re.match(r"^[a-zA-Z0-9_-]+\.db$", cache_file_name):
            raise ValueError(
                "cache_file_name должен содержать только латинские буквы, цифры, "
                "'-' и '_', формат: 'имя.db', получено: %r" % cache_file_name
            )

        self._cache_dir = cache_dir
        self._ttl = timedelta(hours=ttl_hours)
        # ID:067: Используем pathlib.Path.with_name() для безопасности имени файла
        # Это предотвращает path traversal атаки и обеспечивает корректную обработку имён
        self._cache_file = (
            cache_dir.with_name(cache_file_name)
            if cache_dir.is_dir()
            else cache_dir / cache_file_name
        )

        # Инициализация компонентов
        self._pool: ConnectionPool | None = None
        self._serializer = JsonSerializer()
        self._validator = CacheDataValidator()

        # ISSUE-003-#15: Флаг инициализации БД для пропуска повторных CREATE TABLE
        self._db_initialized: bool = False

        # weakref.finalize() для гарантированной очистки ресурсов
        self._weak_ref = weakref.ref(self)
        self._finalizer = weakref.finalize(self, self._cleanup_cache_manager)

        # Инициализация БД
        self._init_db(pool_size)

    def _init_db(self, pool_size: int) -> None:
        """Инициализация базы данных кэша.

        Создает директорию для кэша (если её нет) и создает
        таблицу для хранения кэшированных данных.

        C4: Включает WAL режим и настраивает synchronous=NORMAL для производительности.
        ISSUE-003-#15: Кэширует флаг инициализации для пропуска повторных CREATE TABLE.

        Args:
            pool_size: Размер пула соединений.

        Raises:
            OSError: Если не удалось создать директорию для кэша.
            sqlite3.Error: При ошибке инициализации базы данных.

        """
        # ID:066: Обрабатываем OSError при создании директории
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as mkdir_error:
            app_logger.error(
                "Не удалось создать директорию для кэша %s: %s", self._cache_dir, mkdir_error
            )
            raise

        # Создаём пул соединений
        try:
            self._pool = ConnectionPool(self._cache_file, pool_size)
        except (OSError, sqlite3.Error) as pool_error:
            app_logger.error("Ошибка при создании пула соединений: %s", pool_error)
            raise

        # ISSUE-003-#15: Пропускаем инициализацию если БД уже создана
        if self._db_initialized:
            return

        # Получаем соединение для инициализации
        conn = self._pool.get_connection()

        try:
            # C4: Включаем WAL режим для лучшей конкурентности и защиты от потери данных
            conn.execute("PRAGMA journal_mode=WAL")

            # C4: Настраиваем synchronous=NORMAL для производительности
            conn.execute("PRAGMA synchronous=NORMAL")

            # Создаем таблицу для кэша
            conn.execute(self.CREATE_TABLE_SQL)

            # Создаем индекс для быстрого поиска истекших записей
            conn.execute(self.CREATE_INDEX_SQL)

            # Создаём составной индекс для ускорения поиска
            conn.execute(self.CREATE_CACHE_KEY_INDEX_SQL)

            # Применяем изменения
            conn.commit()

            # ISSUE-003-#15: Отмечаем БД как инициализированную
            self._db_initialized = True

        except (sqlite3.Error, OSError, MemoryError) as e:
            app_logger.error("Ошибка при инициализации кэша: %s", e)
            raise

    def _safe_close_cursor(self, cursor: sqlite3.Cursor | None) -> None:
        """Безопасно закрывает курсор с обработкой ошибок.

        Args:
            cursor: Курсор для закрытия (может быть None).

        """
        if cursor is None:
            return
        try:
            cursor.close()
        except (sqlite3.Error, OSError, MemoryError) as cursor_error:
            # Критические ошибки логируются на уровне warning для диагностики
            app_logger.warning("Ошибка при закрытии курсора: %s", cursor_error)

    def _select_from_db(self, conn: sqlite3.Connection, url_hash: str) -> CacheRow | None:
        """Выполняет SELECT запрос к базе данных для извлечения строки кэша.

        ISSUE-065: Использует conn.execute() напрямую вместо создания курсора.

        Args:
            conn: Соединение базы данных sqlite3.
            url_hash: Хеш URL для поиска.

        Returns:
            Кортеж (data, checksum, expires_at_str) или None если не найдено.

        """
        # ISSUE-065: Используем conn.execute() напрямую для простых SELECT запросов
        cursor = conn.execute(self.SELECT_SQL, (url_hash,))
        row = cursor.fetchone()
        cursor.close()
        return row  # type: ignore[no-any-return]

    def _parse_expires_at(self, expires_at_str: str) -> datetime | None:
        """Парсит строку даты истечения кэша.

        ISSUE-004: Делегирует cache_utils.parse_expires_at.
        """
        return parse_expires_at(expires_at_str)

    def _is_cache_expired(self, expires_at: datetime | None) -> bool:
        """Проверяет истёк ли кэш.

        ISSUE-004: Делегирует cache_utils.is_cache_expired.
        """
        return is_cache_expired(expires_at)

    def _delete_cached_entry(self, cursor: sqlite3.Cursor, url_hash: str) -> None:
        """Удаляет запись кэша из базы данных.

        Args:
            cursor: Курсор базы данных sqlite3.
            url_hash: Хеш URL для удаления.

        """
        cursor.execute(self.DELETE_SQL, (url_hash,))

    def _handle_cache_hit(
        self, data: str, checksum: int, expires_at_str: str, conn: sqlite3.Connection, url_hash: str
    ) -> dict[str, Any] | None:
        """Обрабатывает попадание в кэш.

        ISSUE-071: Использует conn вместо cursor для оптимизации.

        Args:
            data: Сериализованные данные.
            checksum: CRC32 checksum для проверки целостности.
            expires_at_str: Строка даты истечения.
            conn: Соединение базы данных sqlite3.
            url_hash: Хеш URL.

        Returns:
            Десериализованные данные или None если кэш истёк или checksum не совпадает.

        """
        expires_at = self._parse_expires_at(expires_at_str)
        if expires_at is None:
            conn.rollback()
            return None

        if self._is_cache_expired(expires_at):
            # ISSUE-065: Используем conn.execute() напрямую
            conn.execute(self.DELETE_SQL, (url_hash,))
            conn.commit()
            return None

        # H002: Проверка CRC32 checksum с кэшированием для проверки целостности данных
        # P0-8: Используем кэшированную функцию для снижения CPU нагрузки
        data_json_hash = _compute_data_hash_cached(data)
        computed_checksum = compute_crc32_cached(data_json_hash, data)
        if computed_checksum != checksum:
            app_logger.warning(
                "CRC32 checksum не совпадает для URL %s (ожидался: %d, получен: %d). "
                "Данные считаются повреждёнными.",
                url_hash,
                checksum,
                computed_checksum,
            )
            # ISSUE-065: Используем conn.execute() напрямую
            conn.execute(self.DELETE_SQL, (url_hash,))
            conn.commit()
            return None

        conn.commit()
        return self._serializer.deserialize(data)

    def _handle_cache_miss(
        self, _cursor: sqlite3.Cursor, _url_hash: str, conn: sqlite3.Connection
    ) -> None:
        """Обрабатывает промах кэша.

        Args:
            _cursor: Курсор базы данных sqlite3.
            _url_hash: Хеш URL.
            conn: Соединение базы данных sqlite3.

        """
        conn.rollback()

    def _handle_db_error(
        self, db_error: sqlite3.Error, url: str, url_hash: str
    ) -> dict[str, Any] | None:
        """Обрабатывает ошибки базы данных при получении кэша.

        ISSUE-065, ISSUE-071: Использует conn вместо cursor для оптимизации.

        H6: Упрощённая обработка ошибок до 3 категорий:
        1. Временные ошибки (database is locked, busy) - повторная попытка
        2. Критические ошибки (disk i/o, no such table, corrupt) - выбрасываются дальше
        3. Остальные ошибки - логируются и возвращается None

        Args:
            db_error: Исключение базы данных.
            url: URL для логирования.
            url_hash: Хеш URL для повторной попытки.

        Returns:
            Данные кэша или None если произошла ошибка.

        Raises:
            sqlite3.Error: При критических ошибках базы данных.

        """
        error_str = str(db_error).lower()

        # H6 Категория 1: Временные ошибки - можно повторить попытку
        if "database is locked" in error_str or "busy" in error_str:
            app_logger.warning(
                "База данных заблокирована (временная ошибка): %s. Повторная попытка...", db_error
            )
            time.sleep(0.5)
            # ISSUE-065: Повторная попытка через conn.execute() напрямую
            # Для этого нужно получить новое соединение
            retry_conn = None
            try:
                app_logger.warning(
                    "Повторная попытка получения кэша после блокировки БД (URL: %s)", url
                )
                retry_conn = self._pool.get_connection() if self._pool else None
                if retry_conn:
                    retry_cursor = retry_conn.execute(self.SELECT_SQL, (url_hash,))
                    try:
                        row = retry_cursor.fetchone()
                    finally:
                        retry_cursor.close()
                    if row:
                        data, expires_at_str = row
                        expires_at = self._parse_expires_at(expires_at_str)
                        if expires_at and datetime.now(timezone.utc) <= expires_at:
                            return self._serializer.deserialize(data)
            except sqlite3.Error as retry_error:
                app_logger.warning("Повторная попытка не удалась: %s", retry_error)
            finally:
                # ИСПРАВЛЕНИЕ #9: Гарантированный возврат соединения в пул
                if retry_conn and self._pool:
                    try:
                        self._pool.return_connection(retry_conn)
                    except (sqlite3.Error, OSError) as return_error:
                        app_logger.debug("Ошибка при возврате соединения в пул: %s", return_error)
            app_logger.warning("Кэш недоступен после retry (URL: %s). Возврат None.", url)
            return None

        # H6 Категория 2: Критические ошибки - выбрасываются дальше
        if "disk i/o error" in error_str or "no such table" in error_str:
            app_logger.critical("Критическая ошибка диска при получении кэша: %s", db_error)
            raise db_error

        if "corrupt" in error_str or "malformed" in error_str:
            app_logger.critical("База данных повреждена: %s", db_error)
            raise db_error

        # ID:070: Категория 3 - Остальные ошибки - логируем явно перед возвратом None
        # чтобы не скрыть потенциально важные ошибки
        app_logger.error(
            "Ошибка БД при получении кэша (возврат None): %s (тип: %s, URL: %s)",
            db_error,
            type(db_error).__name__,
            url,
        )
        return None

    def _handle_deserialize_error(
        self, decode_error: Exception, url: str, conn: sqlite3.Connection, url_hash: str
    ) -> None:
        """Обрабатывает ошибки десериализации кэша.

        ISSUE-065: Использует conn.execute() напрямую вместо cursor.

        Args:
            decode_error: Исключение десериализации.
            url: URL для логирования.
            conn: Соединение базы данных sqlite3.
            url_hash: Хеш URL для удаления.

        Raises:
            sqlite3.Error: При ошибке удаления повреждённой записи.

        """
        error_type = type(decode_error).__name__
        app_logger.warning(
            "Ошибка %s при чтении кэша для URL %s: %s. Повреждённая запись будет удалена.",
            error_type,
            url,
            decode_error,
        )
        try:
            # ISSUE-065: Используем conn.execute() напрямую
            conn.execute(self.DELETE_SQL, (url_hash,))
            conn.commit()
        except sqlite3.Error as cleanup_error:
            app_logger.warning("Ошибка при удалении повреждённой записи: %s", cleanup_error)

    def get(self, url: str) -> dict[str, Any] | None:
        """Получение данных из кэша.

        Проверяет наличие кэша для указанного URL. Если кэш существует
        и не истек, возвращает кэшированные данные. Иначе возвращает None.

        ISSUE-071: Оптимизация - используется conn.execute() напрямую для простых запросов.

        Args:
            url: URL для поиска в кэше

        Returns:
            Кэшированные данные или None, если кэш истек или отсутствует

        Raises:
            sqlite3.Error: При критической ошибке БД (disk I/O, no such table)

        """
        # ИСПРАВЛЕНИЕ: Рефакторинг — используется декомпозиция на подметоды
        if not self._pool:
            return None

        # D004: Валидация URL перед использованием
        if url is None:
            return None
        if not isinstance(url, str):
            return None
        if not url.strip():
            return None

        try:
            url_hash = self._hash_url(url)
        except (ValueError, TypeError):
            return None

        conn = self._pool.get_connection()

        try:
            # Добавляем retry логику для обработки sqlite3.OperationalError (database is locked)
            for attempt in range(self._MAX_RETRIES):
                try:
                    # ИСПРАВЛЕНИЕ #17: BEGIN DEFERRED вместо BEGIN IMMEDIATE
                    # для SELECT запросов. DEFERRED достаточно для read-транзакции,
                    # IMMEDIATE создаёт unnecessary write-транзакцию
                    conn.execute("BEGIN DEFERRED")
                    break
                except sqlite3.OperationalError as lock_error:
                    if (
                        "database is locked" in str(lock_error).lower()
                        and attempt < self._MAX_RETRIES - 1
                    ):
                        app_logger.debug(
                            "База данных заблокирована при BEGIN IMMEDIATE (попытка %d/%d): %s",
                            attempt + 1,
                            self._MAX_RETRIES,
                            lock_error,
                        )
                        time.sleep(self._RETRY_DELAY * (2**attempt))
                    else:
                        raise

            # ISSUE-071: Используем conn.execute() напрямую для простых SELECT запросов
            row = self._select_from_db(conn, url_hash)

            if not row:
                # ISSUE-071: Используем conn.rollback() напрямую
                conn.rollback()
                return None

            data, checksum, expires_at_str = row
            # ISSUE-071: Передаём conn вместо cursor для _handle_cache_hit
            return self._handle_cache_hit(data, checksum, expires_at_str, conn, url_hash)

        except sqlite3.Error as db_error:
            # ISSUE-003-#19: Не вызываем rollback если retry уже обработал транзакцию
            # _handle_db_error может выполнить commit при успешной retry попытке
            result = self._handle_db_error(db_error, url, url_hash)
            if result is None:
                # Только если retry не вернул результат, делаем rollback
                try:
                    conn.rollback()
                except (sqlite3.Error, OSError, MemoryError) as rollback_error:
                    app_logger.debug("Ошибка при откате транзакции: %s", rollback_error)
            return result

        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as decode_error:
            self._handle_deserialize_error(decode_error, url, conn, url_hash)
            return None

        except (MemoryError, OSError, RuntimeError) as general_error:
            app_logger.error(
                "Непредвиденная ошибка при чтении кэша для URL %s: %s (тип: %s)",
                url,
                general_error,
                type(general_error).__name__,
            )
            # P0-3: Добавляем rollback транзакции при MemoryError
            try:
                conn.rollback()
            except (sqlite3.Error, OSError, MemoryError) as rollback_error:
                app_logger.debug("Ошибка при откате транзакции: %s", rollback_error)
            return None
        finally:
            # ISSUE-084: Возвращаем соединение в пул явно для предотвращения утечки ресурсов
            if self._pool is not None:
                self._pool.return_connection(conn)

    def set(self, url: str, data: dict[str, Any]) -> None:
        """Сохранение данных в кэш.

        Проверяет корректность данных и сохраняет их в кэш для указанного URL.
        Если кэш для этого URL уже существует, он будет перезаписан.

        Args:
            url: URL для кэширования
            data: Данные для сохранения (должны быть сериализуемы в JSON)

        Raises:
            TypeError: Если data является None или не является словарём.
            ValueError: Если URL некорректен.

        """
        if not self._pool:
            return

        # D004: Валидация URL перед использованием
        if url is None:
            raise ValueError("URL не может быть None")
        if not isinstance(url, str):
            raise TypeError(f"URL должен быть строкой, получен {type(url).__name__}")
        if not url.strip():
            raise ValueError("URL не может быть пустой строкой")
        # Проверка на минимальную валидность URL (должен содержать схему)
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL должен начинаться с http:// или https://")

        # ВАЛИДАЦИЯ: проверка data на None
        if data is None:
            raise TypeError("Данные кэша не могут быть None")

        # ID:073: Проверка MAX_RESPONSE_SIZE до сериализации для предотвращения MemoryError
        # Оцениваем приблизительный размер данных перед сериализацией
        try:
            # Быстрая оценка размера через repr() для предотвращения дорогой сериализации
            estimated_size = len(repr(data).encode("utf-8"))
            if estimated_size > MAX_RESPONSE_SIZE:
                raise MemoryError(
                    f"Приблизительный размер данных ({estimated_size} байт) превышает лимит "
                    f"({MAX_RESPONSE_SIZE} байт). Кэширование отклонено."
                )
        except MemoryError:
            # Пробрасываем MemoryError дальше
            raise
        except (TypeError, ValueError, AttributeError) as estimate_error:
            # Если не удалось оценить размер, продолжаем с сериализацией
            app_logger.debug("Не удалось оценить размер данных до сериализации: %s", estimate_error)

        # Вычисляем хеш URL и время истечения
        url_hash = self._hash_url(url)

        # Используем одну временную метку для всех операций в методе
        now = datetime.now(timezone.utc)
        expires_at = now + self._ttl

        # ID:072: Обработка MemoryError при сериализации
        data_json: str | None = None
        try:
            data_json = self._serializer.serialize(data)
        except MemoryError:
            # ID:072: Graceful обработка MemoryError при сериализации
            app_logger.error(
                "MemoryError при сериализации данных для кэша (URL: %s). "
                "Данные слишком большие для обработки.",
                url,
            )
            raise
        except (TypeError, ValueError) as serialize_error:
            app_logger.error("Ошибка сериализации данных для кэша: %s", serialize_error)
            raise TypeError(
                f"Не удалось сериализовать данные в JSON: {serialize_error}"
            ) from serialize_error

        # CRITICAL 2: Проверка размера данных после сериализации
        data_size = len(data_json.encode("utf-8"))
        if data_size > MAX_RESPONSE_SIZE:
            raise MemoryError(
                f"Размер данных ({data_size} байт) превышает лимит ({MAX_RESPONSE_SIZE} байт). "
                "Кэширование больших данных может привести к MemoryError."
            )

        conn = self._pool.get_connection()
        # P1-8: Гарантируем создание курсора перед try для безопасности в finally
        cursor: sqlite3.Cursor | None = None

        try:
            cursor = conn.cursor()
            # H002: Вычисляем CRC32 checksum с кэшированием для часто используемых данных
            # P1-15: Используем кэшированную функцию для вычисления hash
            data_json_hash = compute_data_json_hash(data_json)
            checksum = compute_crc32_cached(data_json_hash, data_json)

            # ПРОВЕРКА: Ограничение размера кэша перед вставкой
            self._enforce_cache_size_limit(conn)

            # Сохраняем данные в базу с использованием подготовленного запроса
            cursor.execute(
                self.UPSERT_SQL,
                (url_hash, url, data_json, checksum, now.isoformat(), expires_at.isoformat()),
            )
            conn.commit()
        except MemoryError:
            # CRITICAL 2: Graceful деградация при MemoryError
            # P1-8: Добавляем rollback транзакции при MemoryError
            try:
                conn.rollback()
            except (sqlite3.Error, OSError, MemoryError) as rollback_error:
                app_logger.debug("Ошибка при откате транзакции: %s", rollback_error)
            app_logger.warning(
                "MemoryError при сохранении кэша для URL %s. Данные не были сохранены.", url
            )
            raise
        except sqlite3.Error as db_error:
            # ИСПРАВЛЕНИЕ: Унифицированный стиль обработки ошибок
            # Критические ошибки БД выбрасываются дальше
            error_str = str(db_error).lower()
            if "disk i/o error" in error_str or "no such table" in error_str:
                app_logger.critical("Критическая ошибка БД при сохранении кэша: %s", db_error)
                raise
            # Ожидаемые ошибки логируются
            app_logger.error("Ошибка БД при сохранении кэша: %s", db_error)
        finally:
            # P1-8: Гарантированное закрытие курсора в finally
            self._safe_close_cursor(cursor)

    def get_batch(self, urls: list[str]) -> dict[str, dict[str, Any] | None]:
        """Пакетное получение данных из кэша.

        C015: Оптимизация N+1 queries через пакетное получение.
        P0-9: Устранение double hashing через однократное вычисление хешей.

        Args:
            urls: Список URL для получения.

        Returns:
            Словарь {url: data} где data=None если кэш не найден.

        """
        if not self._pool or not urls:
            return {}

        conn = self._pool.get_connection()
        cursor = conn.cursor()
        results: dict[str, dict[str, Any] | None] = {}

        # P0-9: Предварительное вычисление всех хешей (устранение double hashing)
        url_to_hash: dict[str, str] = {}
        valid_hashes: list[str] = []
        for url in urls:
            try:
                url_hash = self._hash_url(url)
                url_to_hash[url] = url_hash
                valid_hashes.append(url_hash)
            except (ValueError, TypeError):
                results[url] = None
                continue

        if not valid_hashes:
            return results

        # C015, P0-10: Пакетный запрос вместо N+1 queries
        # Используем параметризованный запрос для безопасности
        placeholders = ",".join("?" * len(valid_hashes))
        batch_query = f"""
            SELECT url_hash, data, checksum, expires_at
            FROM cache
            WHERE url_hash IN ({placeholders})
        """  # nosec B608 — placeholders генерируется как "?,?,...", данные параметризуются

        try:
            cursor.execute("BEGIN")
            cursor.execute(batch_query, valid_hashes)
            rows = cursor.fetchall()

            # P0-9: Используем预先 вычисленные хеши для маппинга результатов
            hash_to_data: dict[str, tuple[str, int, str]] = {}
            for row in rows:
                url_hash, data, checksum, expires_at_str = row
                hash_to_data[url_hash] = (data, checksum, expires_at_str)

            # Обрабатываем результаты
            for url, url_hash in url_to_hash.items():
                if url_hash not in hash_to_data:
                    results[url] = None
                    continue

                data, checksum, expires_at_str = hash_to_data[url_hash]
                # P0-9: Передаём url_hash для устранения повторного вычисления
                result = self._handle_cache_hit(data, checksum, expires_at_str, conn, url_hash)
                results[url] = result

            conn.commit()
        except sqlite3.Error as db_error:
            try:
                conn.rollback()
            except (sqlite3.Error, OSError, MemoryError) as rollback_error:
                app_logger.debug("Ошибка при откате пакетной операции: %s", rollback_error)
            app_logger.error("Ошибка БД при пакетном получении кэша: %s", db_error)
            results = dict.fromkeys(urls)
        finally:
            self._safe_close_cursor(cursor)

        return results

    def set_batch(self, items: list[tuple[str, dict[str, Any]]]) -> int:
        """Пакетное сохранение данных в кэш.

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
        now = datetime.now(timezone.utc)
        expires_at = now + self._ttl

        # Оптимизация: сериализация в один проход, затем пакетная вставка
        batch_params: list[tuple[str, str, str, int, str, str]] = []
        for url, data in items:
            try:
                url_hash = self._hash_url(url)
                data_json = self._serializer.serialize(data)
                # H002: Вычисляем CRC32 checksum с кэшированием для часто используемых данных
                # P0-8: Используем кэшированную функцию для снижения CPU нагрузки
                data_json_hash = _compute_data_hash_cached(data_json)
                checksum = compute_crc32_cached(data_json_hash, data_json)
                batch_params.append(
                    (url_hash, url, data_json, checksum, now.isoformat(), expires_at.isoformat())
                )
                saved_count += 1
            except (TypeError, ValueError) as serialize_error:
                app_logger.warning(
                    "Ошибка сериализации данных для кэша (%s): %s", url, serialize_error
                )
                skipped_count += 1
                continue

        try:
            # Пакетная вставка через executemany для снижения накладных расходов
            if batch_params:
                cursor.executemany(self.UPSERT_SQL, batch_params)

                # ПРОВЕРКА: Ограничение размера кэша перед пакетной вставкой
                # C013: Проверяем размер кэша только если количество записей > порога
                if len(items) > _CACHE_SIZE_CHECK_THRESHOLD:
                    self._enforce_cache_size_limit(conn)

                # Один коммит для всех записей
                conn.commit()

            if skipped_count > 0:
                app_logger.warning(
                    "Пакетное сохранение кэша: сохранено %d, пропущено %d",
                    saved_count,
                    skipped_count,
                )

        except sqlite3.Error as db_error:
            # ИСПРАВЛЕНИЕ: Унифицированный стиль обработки ошибок
            error_str = str(db_error).lower()
            if "disk i/o error" in error_str or "no such table" in error_str:
                app_logger.critical(
                    "Критическая ошибка БД при пакетном сохранении кэша: %s", db_error
                )
                raise
            app_logger.error("Ошибка БД при пакетном сохранении кэша: %s", db_error)
        finally:
            self._safe_close_cursor(cursor)

        return saved_count

    def clear(self) -> None:
        """Очистка всего кэша.

        Удаляет все записи из кэша.
        """
        if not self._pool:
            return

        conn = self._pool.get_connection()

        try:
            conn.execute("DELETE FROM cache")
            conn.commit()
            app_logger.debug("Кэш полностью очищен")
        except sqlite3.Error as db_error:
            # ИСПРАВЛЕНИЕ: Унифицированный стиль обработки ошибок
            error_str = str(db_error).lower()
            if "disk i/o error" in error_str or "no such table" in error_str:
                app_logger.critical("Критическая ошибка БД при очистке кэша: %s", db_error)
                raise
            app_logger.error("Ошибка БД при очистке кэша: %s", db_error)

    def delete(self, url: str) -> None:
        """Удаление записи из кэша по URL.

        Args:
            url: URL для удаления из кэша.

        """
        if not self._pool:
            return

        try:
            url_hash = self._hash_url(url)
        except (ValueError, TypeError):
            return

        conn = self._pool.get_connection()

        try:
            conn.execute(self.DELETE_SQL, (url_hash,))
            conn.commit()
        except sqlite3.Error as db_error:
            error_str = str(db_error).lower()
            if "disk i/o error" in error_str or "no such table" in error_str:
                app_logger.critical("Критическая ошибка БД при удалении кэша: %s", db_error)
                raise
            app_logger.error("Ошибка БД при удалении кэша: %s", db_error)

    def clear_expired(self) -> int:
        """Очистка истекшего кэша.

        Удаляет все записи, у которых время истечения меньше текущего.

        Returns:
            Количество удалённых записей

        """
        if not self._pool:
            return 0

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            current_time = datetime.now(timezone.utc)

            cursor.execute(self.DELETE_EXPIRED_SQL, (current_time.isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count is not None and deleted_count > 0:
                app_logger.debug("Очищено %d истекших записей кэша", deleted_count)

            return deleted_count

        except sqlite3.Error as db_error:
            # ИСПРАВЛЕНИЕ: Унифицированный стиль обработки ошибок
            error_str = str(db_error).lower()
            if "disk i/o error" in error_str or "no such table" in error_str:
                app_logger.critical(
                    "Критическая ошибка БД при очистке истекшего кэша: %s", db_error
                )
                raise
            app_logger.warning("Ошибка БД при очистке истекшего кэша: %s", db_error)
            return 0
        finally:
            self._safe_close_cursor(cursor)

    def clear_batch(self, url_hashes: list[str]) -> int:
        """Пакетное удаление записей по хешам URL.

        Args:
            url_hashes: Список хешей URL для удаления.

        Returns:
            Количество удалённых записей.

        Raises:
            ValueError: Если размер пакета превышает MAX_BATCH_SIZE.

        """
        if not self._pool or not url_hashes:
            return 0

        # Ограничиваем максимальный размер пакета для предотвращения DoS
        if len(url_hashes) > MAX_BATCH_SIZE:
            raise ValueError(
                f"Размер пакета {len(url_hashes)} превышает максимальный лимит {MAX_BATCH_SIZE}"
            )

        # Строгая валидация каждого хеша (64 символа, hex)
        validated_hashes = [h for h in url_hashes if self._validate_hash(h)]
        if not validated_hashes:
            return 0

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            # Переиспользуем временную таблицу вместо создания каждый раз
            cursor.execute("CREATE TEMP TABLE IF NOT EXISTS temp_hashes (hash TEXT PRIMARY KEY)")
            # Очищаем таблицу перед вставкой для повторного использования
            cursor.execute("DELETE FROM temp_hashes")

            # Вставляем хеши безопасно через параметризованный запрос
            cursor.executemany(
                "INSERT INTO temp_hashes VALUES (?)", [(h,) for h in validated_hashes]
            )

            # Удаляем через JOIN с временной таблицей
            cursor.execute("DELETE FROM cache WHERE url_hash IN (SELECT hash FROM temp_hashes)")
            deleted_count = cursor.rowcount

            conn.commit()
            return deleted_count

        except sqlite3.Error as db_error:
            # ИСПРАВЛЕНИЕ: Унифицированный стиль обработки ошибок
            error_str = str(db_error).lower()
            if "disk i/o error" in error_str or "no such table" in error_str:
                app_logger.critical("Критическая ошибка БД при пакетном удалении: %s", db_error)
                raise
            app_logger.warning("Ошибка БД при пакетном удалении: %s", db_error)
            return 0
        finally:
            self._safe_close_cursor(cursor)

    def get_stats(self) -> dict[str, Any]:
        """Получение статистики кэша.

        Returns:
            Словарь со статистикой:
            - total_records: Общее количество записей
            - expired_records: Количество истекших записей
            - cache_size: Размер файла базы данных в байтах

        """
        if not self._pool:
            return {"total_records": 0, "expired_records": 0, "cache_size": 0}

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(self.COUNT_ALL_SQL)
            total = cursor.fetchone()[0]

            current_time = datetime.now(timezone.utc)

            cursor.execute(self.COUNT_EXPIRED_SQL, (current_time.isoformat(),))
            expired = cursor.fetchone()[0]

            try:
                cache_size = self._cache_file.stat().st_size if self._cache_file.exists() else 0
            except OSError:
                cache_size = 0

            return {"total_records": total, "expired_records": expired, "cache_size": cache_size}

        except sqlite3.Error as db_error:
            # ИСПРАВЛЕНИЕ: Унифицированный стиль обработки ошибок
            error_str = str(db_error).lower()
            if "disk i/o error" in error_str or "no such table" in error_str:
                app_logger.critical(
                    "Критическая ошибка БД при получении статистики кэша: %s", db_error
                )
                raise
            app_logger.warning("Ошибка при получении статистики кэша: %s", db_error)
            return {"total_records": 0, "expired_records": 0, "cache_size": 0}
        finally:
            self._safe_close_cursor(cursor)

    def close(self) -> None:
        """Закрывает все соединения и освобождает ресурсы.

        Важно: Вызывать перед завершением работы приложения.
        """
        if hasattr(self, "_pool") and self._pool is not None:
            self._pool.close()
            self._pool = None
            app_logger.debug("Менеджер кэша закрыт")

    def _cleanup_cache_manager(self) -> None:
        """Метод для гарантированной очистки CacheManager.

        Вызывается weakref.finalize() при уничтожении объекта сборщиком мусора.
        Закрывает пул соединений при очистке.
        """
        if hasattr(self, "_pool") and self._pool is not None:
            try:
                self._pool.close_all()
            except (sqlite3.Error, OSError, RuntimeError) as e:
                app_logger.debug("Ошибка при очистке пула в finalizer: %s", e)
            self._pool = None

    def __enter__(self) -> "CacheManager":
        """Возвращает экземпляр CacheManager для использования в контекстном менеджере.

        Returns:
            Экземпляр CacheManager.

        """
        return self

    def __exit__(
        self, _exc_type: type[BaseException] | None, _exc_val: BaseException | None, _exc_tb: Any
    ) -> None:
        """Закрывает все соединения при выходе из контекста.

        Args:
            _exc_type: Тип исключения (если было выброшено).
            _exc_val: Значение исключения (если было выброшено).
            _exc_tb: Трассировка исключения (если было выброшено).

        """
        self.close()

    def _hash_url(self, url: str) -> str:
        """Хеширование URL.

        ISSUE-004: Делегирует cache_utils.hash_url.
        """
        return hash_url(url)

    def _validate_hash(self, hash_val: str) -> bool:
        """Валидация хеша.

        ISSUE-004: Делегирует cache_utils.validate_hash.
        """
        return validate_hash(hash_val)

    def _get_cache_size_mb(self, conn: sqlite3.Connection | None = None) -> float:
        """Получает размер кэша в мегабайтах.

        ISSUE-004: Делегирует cache_utils.get_cache_size_mb.
        """
        return get_cache_size_mb(self._cache_file, conn)

    def _enforce_cache_size_limit(self, conn: sqlite3.Connection) -> None:
        """Принудительное ограничение размера кэша.

        C007: Оптимизация LRU eviction через увеличение размера пакета.

        Реализует LRU (Least Recently Used) политику eviction.

        Args:
            conn: SQLite соединение для выполнения запросов

        """
        try:
            cache_size_mb = self._get_cache_size_mb(conn)

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

                    # C007: Увеличенный размер пакета для снижения количества итераций
                    # O(n) -> O(n/batch_size) где batch_size увеличен
                    eviction_batch_size = LRU_EVICT_BATCH * 5

                    # D008: Валидация размера пакета
                    if not isinstance(eviction_batch_size, int) or eviction_batch_size <= 0:
                        app_logger.error(
                            "Некорректный размер пакета для LRU eviction: %s", eviction_batch_size
                        )
                        return

                    # Оптимизация: выполняем COUNT один раз в начале
                    cursor.execute("SELECT COUNT(*) FROM cache")
                    total_records = cursor.fetchone()[0]
                    # Оцениваем средний размер записи и общий размер после удалений
                    avg_record_size = cache_size_mb / total_records if total_records > 0 else 0.001

                    while eviction_iterations < _CACHE_LRU_MAX_ITERATIONS:
                        eviction_iterations += 1

                        # D008: Используем параметризованный запрос (уже безопасно)
                        cursor.execute(self.DELETE_LRU_SQL, (eviction_batch_size,))
                        deleted_count = cursor.rowcount
                        conn.commit()

                        if deleted_count == 0:
                            break

                        total_deleted += deleted_count
                        app_logger.debug(
                            "LRU eviction (итерация %d): удалено %d записей (всего: %d)",
                            eviction_iterations,
                            deleted_count,
                            total_deleted,
                        )

                        # Оптимизация: оцениваем размер без повторного stat()
                        remaining_records = total_records - total_deleted
                        cache_size_mb = (
                            remaining_records * avg_record_size if remaining_records > 0 else 0.0
                        )
                        if cache_size_mb <= MAX_CACHE_SIZE_MB:
                            break

                    if eviction_iterations >= _CACHE_LRU_MAX_ITERATIONS:
                        app_logger.warning(
                            "LRU eviction: достигнут лимит итераций (%d), текущий размер %.2f MB",
                            _CACHE_LRU_MAX_ITERATIONS,
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
                    self._safe_close_cursor(cursor)

        except OSError as os_error:
            app_logger.warning("Ошибка при проверке размера кэша: %s", os_error)
        except sqlite3.Error as db_error:
            app_logger.warning("Ошибка БД при LRU eviction: %s", db_error)


# Алиас для обратной совместимости
Cache = CacheManager
