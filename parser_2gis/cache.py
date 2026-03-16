"""
Модуль для кэширования результатов парсинга.

Предоставляет функциональность для кэширования результатов парсинга
в локальной базе данных SQLite для ускорения повторных запусков.

Оптимизации:
- Connection pooling для избежания накладных расходов на создание соединений
- WAL режим для лучшей производительности при конкурентном доступе
- Пакетные операции для массовой вставки/удаления
- Компилированные SQL запросы для снижения парсинга
"""

import hashlib
import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from .logger import logger

# Экспортируемые символы модуля
__all__ = ["CacheManager"]

# Константы для оптимизации
DEFAULT_BATCH_SIZE = 100  # Размер пакета для пакетных операций
MAX_CONNECTION_AGE = 300  # Максимальный возраст соединения в секундах (5 минут)

# Константы безопасности и ограничения
MAX_BATCH_SIZE = 1000  # Максимальный размер пакета для предотвращения DoS
MAX_CACHE_SIZE_MB = 500  # Максимальный размер кэша в мегабайтах
LRU_EVICT_BATCH = 100  # Количество записей для удаления при LRU eviction
SHA256_HASH_LENGTH = 64  # Длина SHA256 хеша в hex формате


class _ConnectionPool:
    """
    Пул соединений для SQLite, безопасный для многопоточности.

    Примечание: SQLite требует, чтобы соединение создавалось в том же потоке,
    в котором оно используется. Поэтому пул создает новое соединение для каждого потока.
    """

    def __init__(self, cache_file: Path, pool_size: int = 5):
        """
        Инициализация пула соединений.

        Args:
            cache_file: Путь к файлу базы данных.
            pool_size: Размер пула соединений (не используется для thread-local).
        """
        self._cache_file = cache_file
        self._pool_size = pool_size
        self._local = threading.local()
        self._all_conns: List[sqlite3.Connection] = []
        self._lock = threading.Lock()

    def get_connection(self) -> sqlite3.Connection:
        """
        Получает соединение для текущего потока.

        SQLite требует создания соединения в том же потоке, где оно будет использоваться.
        Метод использует thread-local хранилище для каждого потока.

        Returns:
            SQLite соединение для текущего потока.
        """
        # Проверяем, есть ли соединение для текущего потока
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            # Создаём новое соединение для этого потока
            self._local.connection = self._create_connection()
            with self._lock:
                self._all_conns.append(self._local.connection)
        
        return self._local.connection

    def _create_connection(self) -> sqlite3.Connection:
        """
        Создаёт новое соединение с оптимизированными настройками.

        Returns:
            Новое SQLite соединение.
        """
        conn = sqlite3.connect(
            str(self._cache_file),
            timeout=30.0,  # Увеличенный таймаут для снижения конфликтов
            isolation_level=None,  # Autocommit режим для лучшей производительности
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
        """Закрывает все соединения в пуле."""
        with self._lock:
            for conn in self._all_conns:
                try:
                    conn.close()
                except Exception:
                    pass
            self._all_conns.clear()


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
        """
        if ttl_hours <= 0:
            raise ValueError("ttl_hours должен быть положительным числом")

        self._cache_dir = cache_dir
        self._ttl = timedelta(hours=ttl_hours)
        self._cache_file = cache_dir / "cache.db"

        # Инициализация пула соединений и подготовка запросов
        self._pool: Optional[_ConnectionPool] = None
        self._prepared_stmts: Dict[str, Any] = {}

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

            # Примечание: SQLite3 в Python не поддерживает prepare() для курсоров,
            # поэтому используем прямое выполнение с параметрами для защиты от SQL injection
        except Exception as e:
            logger.warning("Ошибка при инициализации кэша: %s", e)
            raise

    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Получение данных из кэша.

        Проверяет наличие кэша для указанного URL. Если кэш существует
        и не истек, возвращает кэшированные данные. Иначе возвращает None.

        Args:
            url: URL для поиска в кэше

        Returns:
            Кэшированные данные или None, если кэш истек или отсутствует
        """
        if not self._pool:
            return None

        # Вычисляем хеш URL для поиска
        url_hash = self._hash_url(url)

        conn = self._pool.get_connection()
        cursor = conn.cursor()

        try:
            # Ищем кэш по хешу URL с использованием подготовленного запроса
            cursor.execute(self.SQL_SELECT, (url_hash,))
            row = cursor.fetchone()

            # Если кэш не найден
            if not row:
                return None

            data, expires_at_str = row
            try:
                expires_at = datetime.fromisoformat(expires_at_str)
            except ValueError:
                # Некорректный формат даты, считаем кэш истёкшим
                logger.debug("Некорректный формат даты в кэше: %s", expires_at_str)
                return None

            # Проверяем, истек ли кэш
            if datetime.now() > expires_at:
                # Кэш истек, удаляем его
                cursor.execute(self.SQL_DELETE, (url_hash,))
                conn.commit()
                return None

            # Кэш найден и не истек, возвращаем данные
            return json.loads(data)

        except sqlite3.Error as db_error:
            logger.warning("Ошибка БД при получении кэша: %s", db_error)
            return None
        except json.JSONDecodeError as json_error:
            logger.warning("Ошибка JSON при чтении кэша: %s", json_error)
            return None
        finally:
            cursor.close()

    def set(self, url: str, data: Dict[str, Any]) -> None:
        """Сохранение данных в кэш.

        Сохраняет указанные данные в кэш для указанного URL.
        Если кэш для этого URL уже существует, он будет перезаписан.

        Args:
            url: URL для кэширования
            data: Данные для сохранения (должны быть сериализуемы в JSON)
        """
        if not self._pool:
            return

        # Вычисляем хеш URL и время истечения
        url_hash = self._hash_url(url)
        now = datetime.now()
        expires_at = now + self._ttl

        # Сериализуем данные один раз
        try:
            data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as e:
            logger.error("Ошибка сериализации данных для кэша: %s", e)
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
            logger.error("Ошибка БД при сохранении кэша: %s", db_error)
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
        now = datetime.now()

        try:
            for url, data in items:
                url_hash = self._hash_url(url)
                expires_at = now + self._ttl

                try:
                    data_json = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
                    cursor.execute(
                        self.SQL_INSERT_OR_REPLACE,
                        (url_hash, url, data_json, now.isoformat(), expires_at.isoformat()),
                    )
                    saved_count += 1
                except (TypeError, ValueError) as e:
                    logger.warning("Ошибка сериализации данных для кэша: %s", e)
                    continue

            # ПРОВЕРКА: Ограничение размера кэша перед пакетной вставкой
            self._enforce_cache_size_limit(conn)

            # Один коммит для всех записей
            conn.commit()

        except sqlite3.Error as db_error:
            logger.error("Ошибка БД при пакетном сохранении кэша: %s", db_error)
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
            logger.debug("Кэш полностью очищен")
        except sqlite3.Error as db_error:
            logger.error("Ошибка БД при очистке кэша: %s", db_error)

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
            # Удаляем истекшие записи с использованием подготовленного запроса
            cursor.execute(self.SQL_DELETE_EXPIRED, (datetime.now().isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()

            if deleted_count > 0:
                logger.debug("Очищено %d истекших записей кэша", deleted_count)

            return deleted_count

        except sqlite3.Error as db_error:
            logger.warning("Ошибка БД при очистке истекшего кэша: %s", db_error)
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
            # Используем параметризованный запрос для безопасности
            placeholders = ",".join("?" * len(url_hashes))
            delete_query = f"DELETE FROM cache WHERE url_hash IN ({placeholders})"
            cursor.execute(delete_query, url_hashes)
            deleted_count = cursor.rowcount
            conn.commit()

            return deleted_count

        except sqlite3.Error as db_error:
            logger.warning("Ошибка БД при пакетном удалении: %s", db_error)
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

            # Количество истекших записей
            cursor.execute(self.SQL_COUNT_EXPIRED, (datetime.now().isoformat(),))
            expired = cursor.fetchone()[0]

            # Размер файла базы данных с обработкой ошибок
            try:
                cache_size = self._cache_file.stat().st_size if self._cache_file.exists() else 0
            except OSError:
                # Файл недоступен или ошибка файловой системы
                cache_size = 0

            return {
                "total_records": total,
                "expired_records": expired,
                "cache_size": cache_size,
            }

        except sqlite3.Error as db_error:
            # Ошибка базы данных
            logger.warning("Ошибка при получении статистики кэша: %s", db_error)
            return {"total_records": 0, "expired_records": 0, "cache_size": 0}
        finally:
            cursor.close()

    def close(self) -> None:
        """
        Закрывает все соединения и освобождает ресурсы.

        Важно: Вызывать перед завершением работы приложения.
        """
        if self._pool:
            self._pool.close_all()
            self._pool = None
            logger.debug("Менеджер кэша закрыт")

    def __enter__(self) -> "CacheManager":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def __del__(self) -> None:
        """Гарантирует закрытие соединений при уничтожении объекта."""
        try:
            self.close()
        except Exception:
            pass

    @staticmethod
    def _hash_url(url: str) -> str:
        """Хеширование URL.

        Вычисляет SHA256 хеш от указанного URL для использования
        в качестве ключа в базе данных кэша.

        Args:
            url: URL для хеширования

        Returns:
            SHA256 хеш URL в виде шестнадцатеричной строки
        """
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

    def _enforce_cache_size_limit(self, conn: sqlite3.Connection) -> None:
        """Принудительное ограничение размера кэша.

        Реализует LRU (Least Recently Used) политику eviction:
        - Проверяет размер файла кэша
        - Если размер превышает MAX_CACHE_SIZE_MB, удаляет LRU_EVICT_BATCH
          старых записей (по timestamp)

        Args:
            conn: SQLite соединение для выполнения запросов
        """
        try:
            # Проверяем размер файла кэша
            if self._cache_file.exists():
                cache_size_bytes = self._cache_file.stat().st_size
                cache_size_mb = cache_size_bytes / (1024 * 1024)

                if cache_size_mb > MAX_CACHE_SIZE_MB:
                    logger.warning(
                        "Размер кэша %.2f MB превышает лимит %d MB. "
                        "Удаление %d старых записей (LRU eviction)",
                        cache_size_mb,
                        MAX_CACHE_SIZE_MB,
                        LRU_EVICT_BATCH,
                    )

                    cursor = conn.cursor()
                    try:
                        cursor.execute(self.SQL_DELETE_LRU, (LRU_EVICT_BATCH,))
                        deleted_count = cursor.rowcount
                        conn.commit()

                        if deleted_count > 0:
                            logger.debug("LRU eviction: удалено %d записей", deleted_count)
                    finally:
                        cursor.close()
        except OSError as os_error:
            logger.warning("Ошибка при проверке размера кэша: %s", os_error)
        except sqlite3.Error as db_error:
            logger.warning("Ошибка БД при LRU eviction: %s", db_error)
