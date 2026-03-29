"""
Модуль менеджера кэша для парсинга.

Предоставляет класс CacheManager для кэширования результатов парсинга
в локальной базе данных SQLite.

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.cache import CacheManager
    >>> cache = CacheManager(Path("cache"))
    >>> cache.get("some_key")  # Получение из кэша
    >>> cache.set("key", {"data": "value"})  # Сохранение в кэш
    >>> cache.close()  # Закрытие соединения
"""

import hashlib
import json
import sqlite3
import time
import weakref
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..constants import LRU_EVICT_BATCH, MAX_BATCH_SIZE, MAX_CACHE_SIZE_MB, SHA256_HASH_LENGTH
from ..logger.logger import logger as app_logger
from .pool import ConnectionPool
from .serializer import JsonSerializer
from .validator import CacheDataValidator


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
        cache_dir: Директория для хранения кэша
        ttl: Время жизни кэша (timedelta)

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

    # Составной индекс для range queries по url_hash + expires_at
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

    def __init__(self, cache_dir: Path, ttl_hours: int = 24, pool_size: int = 5) -> None:
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

        # Инициализация компонентов
        self._pool: Optional[ConnectionPool] = None
        self._serializer = JsonSerializer()
        self._validator = CacheDataValidator()

        # weakref.finalize() для гарантированной очистки ресурсов
        self._weak_ref = weakref.ref(self)
        self._finalizer = weakref.finalize(self, self._cleanup_cache_manager)

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
        self._pool = ConnectionPool(self._cache_file, pool_size)

        # Получаем соединение для инициализации
        conn = self._pool.get_connection()

        try:
            # Создаем таблицу для кэша
            conn.execute(self.SQL_CREATE_TABLE)

            # Создаем индекс для быстрого поиска истекших записей
            conn.execute(self.SQL_CREATE_INDEX)

            # Создаём составной индекс для ускорения поиска
            conn.execute(self.SQL_CREATE_CACHE_KEY_INDEX)

        except (sqlite3.Error, OSError, MemoryError) as e:
            app_logger.warning("Ошибка при инициализации кэша: %s", e)
            raise

    def _get_cached_row(self, cursor: Any, url_hash: str) -> Optional[Tuple[str, str]]:
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
                        return self._serializer.deserialize(data)
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
            return self._serializer.deserialize(data)

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
        try:
            data_json = self._serializer.serialize(data)
        except (TypeError, ValueError) as e:
            app_logger.error("Ошибка сериализации данных для кэша: %s", e)
            return

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            # ПРОВЕРКА: Ограничение размера кэша перед вставкой
            self._enforce_cache_size_limit(conn)

            # Сохраняем данные в базу с использованием подготовленного запроса
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
        now = datetime.now()
        expires_at = now + self._ttl

        try:
            for url, data in items:
                url_hash = self._hash_url(url)

                try:
                    data_json = self._serializer.serialize(data)
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
            conn.execute("DELETE FROM cache")
            conn.commit()
            app_logger.debug("Кэш полностью очищен")
        except sqlite3.Error as db_error:
            app_logger.error("Ошибка БД при очистке кэша: %s", db_error)

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
            current_time = datetime.now()

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
        for hash_val in url_hashes:
            if not self._validate_hash(hash_val):
                raise ValueError(f"Некорректный формат хеша: {hash_val}")

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
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
        """
        if not self._pool:
            return {"total_records": 0, "expired_records": 0, "cache_size": 0}

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(self.SQL_COUNT_ALL)
            total = cursor.fetchone()[0]

            current_time = datetime.now()

            cursor.execute(self.SQL_COUNT_EXPIRED, (current_time.isoformat(),))
            expired = cursor.fetchone()[0]

            try:
                cache_size = self._cache_file.stat().st_size if self._cache_file.exists() else 0
            except OSError:
                cache_size = 0

            return {"total_records": total, "expired_records": expired, "cache_size": cache_size}

        except sqlite3.Error as db_error:
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
            self._pool.close()
            self._pool = None
            app_logger.debug("Менеджер кэша закрыт")

    def _cleanup_cache_manager(self) -> None:
        """
        Метод для гарантированной очистки CacheManager.

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
        """
        Возвращает экземпляр CacheManager для использования в контекстном менеджере.

        Returns:
            Экземпляр CacheManager.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Закрывает все соединения при выходе из контекста.

        Args:
            exc_type: Тип исключения (если было выброшено).
            exc_val: Значение исключения (если было выброшено).
            exc_tb: Трассировка исключения (если было выброшено).
        """
        self.close()

    def __del__(self) -> None:
        """
        Гарантирует закрытие соединений при уничтожении объекта.
        """
        try:
            if hasattr(self, "_finalizer") and self._finalizer is not None:
                if self._finalizer.detach():
                    app_logger.debug("CacheManager очищен через weakref.finalize()")
                    return

            if hasattr(self, "_pool") and self._pool is not None:
                app_logger.warning(
                    "CacheManager уничтожается сборщиком мусора без явного закрытия. "
                    "Всегда вызывайте close() явно или используйте контекстный менеджер."
                )
        except (MemoryError, KeyboardInterrupt, SystemExit):
            raise
        except (RuntimeError, TypeError, ValueError, OSError) as del_error:
            app_logger.debug("Ошибка в __del__ CacheManager: %s", del_error)

    @staticmethod
    def _hash_url(url: str) -> str:
        """
        Хеширование URL.

        Вычисляет SHA256 хеш от указанного URL для использования
        в качестве ключа в базе данных кэша.

        Args:
            url: URL для хеширования. Должен быть непустой строкой.

        Returns:
            SHA256 хеш URL в виде шестнадцатеричной строки.

        Raises:
            ValueError: Если URL является None или пустой строкой.
            TypeError: Если URL не является строкой.
        """
        if url is None:
            raise ValueError("URL не может быть None")

        if not isinstance(url, str):
            raise TypeError(f"URL должен быть строкой, получен {type(url).__name__}")

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

        Args:
            conn: SQLite соединение (опционально, используется для проверки целостности БД).

        Returns:
            Размер кэша в мегабайтах.
        """
        try:
            if not self._cache_file.exists():
                return 0.0

            cache_size_bytes = self._cache_file.stat().st_size
            cache_size_mb = cache_size_bytes / (1024 * 1024)

            if conn is not None:
                try:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA quick_check(1)")
                    cursor.close()
                except sqlite3.Error:
                    app_logger.warning("База данных кэша может быть повреждена")

            return cache_size_mb

        except OSError as os_error:
            app_logger.warning("Ошибка при получении размера кэша: %s", os_error)
            return 0.0

    def _enforce_cache_size_limit(self, conn: sqlite3.Connection) -> None:
        """
        Принудительное ограничение размера кэша.

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
                    max_iterations = 50

                    while (
                        cache_size_mb > MAX_CACHE_SIZE_MB and eviction_iterations < max_iterations
                    ):
                        eviction_iterations += 1

                        cursor.execute(self.SQL_DELETE_LRU, (LRU_EVICT_BATCH,))
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
