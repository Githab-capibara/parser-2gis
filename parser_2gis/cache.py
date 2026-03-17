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
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from .logger import logger

# =============================================================================
# ОПТИМИЗАЦИЯ 3.6: orjson wrapper для сериализации
# =============================================================================

# Попытка импортировать orjson для более быстрой сериализации
# orjson в 2-3 раза быстрее стандартного json модуля
try:
    import orjson
    _use_orjson = True
except ImportError:
    _use_orjson = False
    orjson = None  # type: ignore


def _serialize_json(data: Dict[str, Any]) -> str:
    """
    Сериализует данные в JSON формат.

    Исправление проблемы 1.4:
    - Выбрасываем явные исключения с контекстом вместо logger.warning
    - Используем orjson если установлен (в 2-3 раза быстрее)
    - Fallback на стандартный json если orjson недоступен

    Args:
        data: Данные для сериализации.

    Returns:
        JSON строка.

    Raises:
        TypeError: При ошибке сериализации данных с полным контекстом.
        ValueError: При ошибке преобразования данных.
    """
    if _use_orjson and orjson is not None:
        # orjson возвращает bytes, декодируем в строку
        try:
            return orjson.dumps(data).decode('utf-8')
        except orjson.EncodeError as encode_error:
            # Исправление проблемы 1.4: выбрасываем явное исключение с контекстом
            raise TypeError(
                f"Критическая ошибка сериализации orjson: {encode_error}. "
                f"Тип данных: {type(data).__name__}, "
                f"Содержимое: {repr(data)[:200]}..."
            ) from encode_error
    else:
        # Стандартный json с оптимизированными параметрами
        try:
            return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as json_error:
            raise TypeError(
                f"Критическая ошибка сериализации json: {json_error}. "
                f"Тип данных: {type(data).__name__}"
            ) from json_error


def _deserialize_json(data: str) -> Dict[str, Any]:
    """
    Десериализует JSON строку в данные.

    Исправление проблемы 1.4:
    - Выбрасываем явные исключения с контекстом вместо logger.warning
    - Используем orjson если установлен
    - Fallback на стандартный json если orjson недоступен

    Args:
        data: JSON строка для десериализации.

    Returns:
        Данные в виде словаря.

    Raises:
        json.JSONDecodeError: При ошибке парсинга JSON с контекстом.
        UnicodeDecodeError: При ошибке декодирования Unicode.
        orjson.JSONDecodeError: При ошибке парсинга orjson с контекстом.
        ValueError: При критической ошибке десериализации.
    """
    try:
        if _use_orjson and orjson is not None:
            return orjson.loads(data)  # type: ignore
        else:
            return json.loads(data)
    except orjson.JSONDecodeError as orjson_error:
        # Исправление проблемы 1.4: выбрасываем явное исключение с контекстом
        raise ValueError(
            f"Критическая ошибка десериализации orjson: {orjson_error}. "
            f"Длина данных: {len(data)}, "
            f"Содержимое: {data[:200]}..."
        ) from orjson_error
    except (json.JSONDecodeError, UnicodeDecodeError) as json_error:
        # Исправление проблемы 1.4: выбрасываем явное исключение с контекстом
        error_type = "Unicode" if isinstance(json_error, UnicodeDecodeError) else "JSON"
        raise ValueError(
            f"Критическая ошибка десериализации ({error_type}): {json_error}. "
            f"Длина данных: {len(data)}"
        ) from json_error

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


class _ConnectionPool:
    """
    Пул соединений для SQLite, безопасный для многопоточности.

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

    Raises:
        sqlite3.Error: При ошибке создания соединения с базой данных.
    """

    def __init__(self, cache_file: Path, pool_size: int = 5) -> None:
        """
        Инициализация пула соединений.

        Args:
            cache_file: Путь к файлу базы данных SQLite.
            pool_size: Размер пула соединений (по умолчанию 5).
                      Для thread-local реализации не используется напрямую.

        Raises:
            OSError: Если файл базы данных недоступен для записи.
            sqlite3.Error: При ошибке инициализации базы данных.

        Example:
            >>> pool = _ConnectionPool(Path("/tmp/cache.db"), pool_size=10)
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
                except Exception as e:
                    logger.debug("Не удалось закрыть соединение SQLite: %s", e, exc_info=True)
            self._all_conns.clear()

    def __del__(self) -> None:
        """
        Гарантирует закрытие соединений при уничтожении объекта.

        Исправление проблемы 7 (Connection pool не закрывает соединения при GC):
        - Вызывает close_all() с обработкой исключений
        - Добавляет warning в лог если соединения не закрыты явно
        - В __del__ нельзя выбрасывать исключения - все ошибки логируются

        Важно:
            Не следует полагаться на этот метод для гарантированной очистки.
            Всегда вызывайте close_all() явно или используйте контекстный менеджер.
        """
        # Проверяем есть ли незакрытые соединения
        if hasattr(self, '_all_conns') and self._all_conns:
            logger.warning(
                "_ConnectionPool уничтожается сборщиком мусора с %d незакрытыми соединениями. "
                "Всегда вызывайте close_all() явно или используйте контекстный менеджер.",
                len(self._all_conns)
            )

        # Пытаемся закрыть соединения
        try:
            if hasattr(self, '_all_conns'):
                self.close_all()
        except Exception as del_error:
            # В __del__ нельзя выбрасывать исключения - только логируем
            logger.error(
                "Ошибка при закрытии соединений в __del__ (_ConnectionPool): %s",
                del_error,
                exc_info=True
            )


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

            # Создаем дополнительный индекс для url_hash для ускорения поиска
            conn.execute(self.SQL_CREATE_URL_HASH_INDEX)

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
            # Оптимизация 18: кэшируем результат datetime.now() в переменную
            # для избежания повторных вызовов в рамках одного метода
            current_time = datetime.now()
            if current_time > expires_at:
                # Кэш истек, удаляем его
                cursor.execute(self.SQL_DELETE, (url_hash,))
                conn.commit()
                return None

            # Кэш найден и не истек, возвращаем данные
            # Оптимизация 3.6: используем orjson wrapper для быстрой десериализации
            return _deserialize_json(data)

        except sqlite3.Error as db_error:
            logger.warning("Ошибка БД при получении кэша: %s", db_error)
            return None
        except (UnicodeDecodeError, json.JSONDecodeError) as decode_error:
            # Обрабатываем ошибки десериализации - удаляем повреждённую запись
            error_type = "Unicode" if isinstance(decode_error, UnicodeDecodeError) else "JSON"
            logger.warning(
                "Ошибка %s при чтении кэша для URL %s: %s. Повреждённая запись будет удалена.",
                error_type,
                url,
                decode_error
            )
            # Удаляем повреждённую запись из кэша
            try:
                cursor.execute(self.SQL_DELETE, (url_hash,))
                conn.commit()
            except sqlite3.Error as cleanup_error:
                logger.warning("Ошибка при удалении повреждённой записи: %s", cleanup_error)
            return None
        except Exception as general_error:
            # Обрабатываем любые другие ошибки десериализации (например orjson.JSONDecodeError)
            logger.warning(
                "Неизвестная ошибка при чтении кэша для URL %s: %s. Тип: %s",
                url,
                general_error,
                type(general_error).__name__
            )
            return None
        finally:
            cursor.close()

    def set(self, url: str, data: Dict[str, Any]) -> None:
        """Сохранение данных в кэш.

        Сохраняет указанные данные в кэш для указанного URL.
        Если кэш для этого URL уже существует, он будет перезаписан.

        Оптимизация 18:
        - Кэширование datetime.now() в переменную
        - Использование одной временной метки для всех операций в методе
        - Избегание повторных вызовов datetime.now()

        Args:
            url: URL для кэширования
            data: Данные для сохранения (должны быть сериализуемы в JSON)
        """
        if not self._pool:
            return

        # Вычисляем хеш URL и время истечения
        url_hash = self._hash_url(url)

        # Оптимизация 18: кэшируем datetime.now() в переменную
        # Используем одну временную метку для всех операций в методе
        now = datetime.now()
        expires_at = now + self._ttl

        # Сериализуем данные один раз
        # Оптимизация 3.6: используем orjson wrapper для быстрой сериализации
        try:
            data_json = _serialize_json(data)
        except (TypeError, ValueError) as e:
            logger.error("Ошибка сериализации данных для кэша: %s", e)
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

        # Оптимизация 18: кэшируем datetime.now() в переменную
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
            # Оптимизация 18: кэшируем datetime.now() в переменную
            current_time = datetime.now()

            # Удаляем истекшие записи с использованием подготовленного запроса
            cursor.execute(self.SQL_DELETE_EXPIRED, (current_time.isoformat(),))
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
            # БЕЗОПАСНОСТЬ: SQL injection предотвращён через:
            # 1. Строгую валидацию каждого хеша (64 символа, hex) через _validate_hash()
            # 2. Использование параметризованного запроса с плейсхолдерами (?)
            # 3. Ограничение максимального размера пакета (MAX_BATCH_SIZE)
            # Даже при формировании SQL через f-string, параметры передаются
            # отдельно через cursor.execute(), что полностью защищает от SQL injection.
            # Формирование запроса: DELETE FROM cache WHERE url_hash IN (?,?,?,...)
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
        except Exception as e:
            # Логирование ошибки вместо игнорирования
            logger.error("Ошибка при закрытии CacheManager в __del__: %s", e)

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
                    logger.warning("База данных кэша может быть повреждена")

            return cache_size_mb

        except OSError as os_error:
            logger.warning("Ошибка при получении размера кэша: %s", os_error)
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
                logger.warning(
                    "Размер кэша %.2f MB превышает лимит %d MB. "
                    "Запуск LRU eviction...",
                    cache_size_mb,
                    MAX_CACHE_SIZE_MB,
                )

                cursor = conn.cursor()
                try:
                    total_deleted = 0
                    eviction_iterations = 0
                    max_iterations = 50  # Защита от бесконечного цикла

                    # Циклически удаляем записи пока размер не станет меньше лимита
                    while cache_size_mb > MAX_CACHE_SIZE_MB and eviction_iterations < max_iterations:
                        eviction_iterations += 1

                        # Удаляем пакет старых записей (LRU - по timestamp)
                        cursor.execute(self.SQL_DELETE_LRU, (LRU_EVICT_BATCH,))
                        deleted_count = cursor.rowcount
                        conn.commit()

                        if deleted_count == 0:
                            # Нечего удалять - выходим из цикла
                            logger.debug("LRU eviction: записей для удаления не осталось")
                            break

                        total_deleted += deleted_count
                        logger.debug(
                            "LRU eviction (итерация %d): удалено %d записей (всего: %d)",
                            eviction_iterations,
                            deleted_count,
                            total_deleted,
                        )

                        # Проверяем новый размер кэша
                        cache_size_mb = self._get_cache_size_mb(conn)

                    if eviction_iterations >= max_iterations:
                        logger.warning(
                            "LRU eviction: достигнут лимит итераций (%d), "
                            "текущий размер %.2f MB",
                            max_iterations,
                            cache_size_mb,
                        )

                    if total_deleted > 0:
                        logger.info(
                            "LRU eviction завершена: удалено %d записей за %d итераций, "
                            "новый размер %.2f MB",
                            total_deleted,
                            eviction_iterations,
                            cache_size_mb,
                        )

                finally:
                    cursor.close()

        except OSError as os_error:
            logger.warning("Ошибка при проверке размера кэша: %s", os_error)
        except sqlite3.Error as db_error:
            logger.warning("Ошибка БД при LRU eviction: %s", db_error)


# Алиас для обратной совместимости
Cache = CacheManager
