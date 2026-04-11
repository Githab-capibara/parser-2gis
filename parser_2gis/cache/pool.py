"""Модуль пула соединений для SQLite.

Предоставляет класс ConnectionPool для управления пулом соединений
с базой данных SQLite с поддержкой reuse соединений.

Пример использования:
    >>> from pathlib import Path
    >>> from parser_2gis.cache import ConnectionPool
    >>> pool = ConnectionPool(Path("cache.db"))
    >>> conn = pool.get_connection()
    >>> pool.return_connection(conn)
    >>> pool.close()
"""

import functools
import queue
import sqlite3
import threading
import time
import weakref
from pathlib import Path
from typing import Any

from ..constants import MAX_POOL_SIZE, MIN_POOL_SIZE, validate_env_int
from ..logger.logger import logger as app_logger

# ИСПРАВЛЕНИЕ CRITICAL 23: Заменяем RLock на Lock где не нужна реентерабельность
# RLock используется только там, где требуется реентерабельность (например, вложенные вызовы)

# Попытка импортировать psutil для мониторинга памяти
_SQLITE_PRAGMA_JOURNAL_MODE: str = "WAL"
_SQLITE_PRAGMA_CACHE_SIZE: int = -64000  # 64MB в страницах по 4KB
_SQLITE_PRAGMA_SYNCHRONOUS: str = "NORMAL"
_SQLITE_PRAGMA_BUSY_TIMEOUT: int = 60000  # 60 секунд

# D009: Константы для расчёта размера пула соединений
_POOL_MEMORY_FRACTION: float = 0.10  # 10% доступной памяти
_POOL_MB_PER_CONNECTION: float = 2.0  # 2MB на одно соединение


# Lazy инициализация ENV-зависимых констант для предотвращения вызова на уровне модуля
def _get_max_pool_size_env() -> int:
    """Получает MAX_POOL_SIZE из ENV (lazy инициализация)."""
    if not hasattr(_get_max_pool_size_env, "_value"):
        _get_max_pool_size_env._value = validate_env_int(
            "PARSER_MAX_POOL_SIZE", default=20, min_value=5, max_value=50,
        )
    return _get_max_pool_size_env._value  # type: ignore[attr-defined]


def _get_min_pool_size_env() -> int:
    """Получает MIN_POOL_SIZE из ENV (lazy инициализация)."""
    if not hasattr(_get_min_pool_size_env, "_value"):
        _get_min_pool_size_env._value = validate_env_int(
            "PARSER_MIN_POOL_SIZE", default=5, min_value=1, max_value=10,
        )
    return _get_min_pool_size_env._value  # type: ignore[attr-defined]


def _get_connection_max_age_env() -> int:
    """Получает CONNECTION_MAX_AGE из ENV (lazy инициализация)."""
    if not hasattr(_get_connection_max_age_env, "_value"):
        _get_connection_max_age_env._value = validate_env_int(
            "PARSER_CONNECTION_MAX_AGE", default=300, min_value=60, max_value=3600,
        )
    return _get_connection_max_age_env._value  # type: ignore[attr-defined]


# Попытка импортировать psutil для мониторинга памяти
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@functools.cache
def _calculate_dynamic_pool_size() -> int:
    """Рассчитывает оптимальный размер пула соединений на основе доступной памяти.

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

    Примечание:
        H005: Результат кэшируется через lru_cache(maxsize=1) для предотвращения
        повторных вызовов psutil.virtual_memory() при каждом создании пула.

    """
    try:
        # Пытаемся получить информацию о памяти через psutil
        if not PSUTIL_AVAILABLE:
            raise ImportError("psutil не установлен")

        available_memory_mb = psutil.virtual_memory().available / (1024 * 1024)

        # Выделяем до 10% доступной памяти под пул соединений
        # Каждое соединение занимает ~2MB в среднем
        memory_for_pool_mb = available_memory_mb * _POOL_MEMORY_FRACTION
        connections_by_memory = int(memory_for_pool_mb / _POOL_MB_PER_CONNECTION)

        # Ограничиваем разумными пределами
        dynamic_size = max(MIN_POOL_SIZE, min(connections_by_memory, MAX_POOL_SIZE))

        app_logger.debug(
            "Динамический размер пула: %d (доступно памяти: %.2f MB)",
            dynamic_size,
            available_memory_mb,
        )

        return dynamic_size

    except (ImportError, MemoryError, OSError, ValueError, TypeError, Exception) as error:
        # Объединённая обработка ошибок: все типы ошибок возвращают MIN_POOL_SIZE
        error_type = type(error).__name__
        app_logger.debug("%s при расчёте размера пула: %s, используем минимум", error_type, error)
        return MIN_POOL_SIZE


class ConnectionPool:
    """Пул соединений для SQLite с reuse и queue.Queue для управления.

    Оптимизация:
    - Reuse соединений вместо создания новых
    - max_connections лимит (10-20 соединений)
    - queue.Queue для управления соединениями
    - Правильная очистка соединений
    - Connection pooling для снижения накладных расходов

    Примечание: SQLite требует, чтобы соединение создавалось в том же потоке,
    в котором оно используется. Поэтому пул создает новое соединение для каждого потока.

    Attributes:
        cache_file: Путь к файлу базы данных.
        pool_size: Размер пула соединений.

    Пример использования:
        >>> from pathlib import Path
        >>> pool = ConnectionPool(Path("cache.db"), pool_size=5)
        >>> conn = pool.get_connection()  # Получить соединение для текущего потока
        >>> pool.return_connection(conn)  # Вернуть соединение в пул
        >>> pool.close()  # Закрыть все соединения

    """

    def __init__(
        self,
        cache_file: Path,
        pool_size: int | None = None,
        *,
        use_dynamic: bool = False,  # Для обратной совместимости
    ) -> None:
        """Инициализация пула соединений.

        Args:
            cache_file: Путь к файлу базы данных SQLite.
            pool_size: Размер пула соединений (по умолчанию из ENV переменных).
            use_dynamic: Если True, использует MIN_POOL_SIZE (для обратной совместимости).

        Raises:
            OSError: Если файл базы данных недоступен для записи.
            sqlite3.Error: При ошибке инициализации базы данных.

        Example:
            >>> pool = ConnectionPool(Path("/tmp/cache.db"))
            >>> # Или с явным размером:
            >>> pool = ConnectionPool(Path("/tmp/cache.db"), pool_size=10)

        """
        self._cache_file = cache_file
        # Используем фиксированный размер пула из ENV или заданный вручную
        if use_dynamic:
            # Для обратной совместимости: use_dynamic=True возвращает MIN_POOL_SIZE
            self._pool_size = _get_min_pool_size_env()
        elif pool_size is not None:
            # Ограничиваем размер пула разумными пределами
            self._pool_size = max(
                _get_min_pool_size_env(), min(pool_size, _get_max_pool_size_env()),
            )
        else:
            self._pool_size = _get_max_pool_size_env()

        app_logger.debug("Используемый размер пула соединений: %d", self._pool_size)

        # Для совместимости с тестами
        self._max_size = self._pool_size

        self._local: threading.local = threading.local()
        self._all_conns: list[sqlite3.Connection] = []
        # ИСПРАВЛЕНИЕ CRITICAL 23: Используем Lock вместо RLock где не нужна реентерабельность
        # Lock более производительный и предотвращает случайные реентерабельные вызовы
        self._lock = threading.Lock()
        # queue.Queue для управления соединениями
        self._connection_queue: queue.Queue[sqlite3.Connection] = queue.Queue(
            maxsize=self._pool_size,
        )
        # Хранение возраста соединений по id(conn)
        self._connection_age: dict[int, float] = {}
        # weakref.finalize() для гарантированной очистки ресурсов
        self._weak_ref = weakref.ref(self)
        self._finalizer = weakref.finalize(self, self._cleanup_pool, self._all_conns, self._lock)

    def _is_connection_valid(self, conn: sqlite3.Connection) -> bool:
        """Проверяет активность соединения через SELECT 1.

        Args:
            conn: Соединение для проверки.

        Returns:
            True если соединение активно, False иначе.

        """
        try:
            conn.execute("SELECT 1")
            return True
        except (sqlite3.Error, OSError) as e:
            app_logger.debug("Соединение неактивно (ошибка проверки): %s", e)
            return False

    def get_connection(self) -> sqlite3.Connection:
        """Получает соединение для текущего потока с reuse.

        Оптимизация:
        - Reuse соединений вместо создания новых
        - Проверка возраста соединения и пересоздание при необходимости
        - queue.Queue для потокобезопасного управления
        - Оптимизированная блокировка: единый захват для проверки и регистрации

        SQLite требует создания соединения в том же потоке, где оно будет использоваться.
        Метод использует thread-local хранилище для каждого потока.

        Returns:
            SQLite соединение для текущего потока.

        Raises:
            sqlite3.Error: При ошибке создания соединения.
            OSError: При ошибке ОС.
            RuntimeError: При критической ошибке инициализации.

        """
        conn: sqlite3.Connection | None = None
        created_new: bool = False

        try:
            # Быстрая проверка thread-local кэша без блокировки
            # (thread-local уже потокобезопасен)
            if hasattr(self._local, "connection") and self._local.connection is not None:
                conn_obj = self._local.connection
                conn_id = id(conn_obj)
                # Проверяем возраст без блокировки (чтение атомарно)
                age = self._connection_age.get(conn_id)

                should_reuse = False
                if age is not None:
                    age = time.time() - age
                    if age <= _get_connection_max_age_env() and self._is_connection_valid(conn_obj):
                        should_reuse = True
                    # Если устарело — нужно пересоздать под блокировкой

                if should_reuse:
                    return conn_obj

                # Соединение устарело или неактивно — закрываем и пересоздаём
                with self._lock:
                    # Повторная проверка под блокировкой
                    if self._local.connection is not None:
                        try:
                            conn_obj.close()
                        except (sqlite3.Error, OSError) as close_error:
                            app_logger.debug("Ошибка при закрытии соединения: %s", close_error)

                        if conn_obj in self._all_conns:
                            self._all_conns.remove(conn_obj)
                        if conn_id in self._connection_age:
                            del self._connection_age[conn_id]
                        self._local.connection = None

            # Попытка получить соединение из queue вне блокировки
            # queue.Queue сам по себе потокобезопасен
            try:
                conn = self._connection_queue.get_nowait()
                conn_id = id(conn)
                age = self._connection_age.get(conn_id)
                if age is not None and (
                    time.time() - age > _get_connection_max_age_env()
                    or not self._is_connection_valid(conn)
                ):
                    app_logger.debug("Соединение из queue устарело или неактивно, пересоздаём")
                    try:
                        conn.close()
                    except (sqlite3.Error, OSError) as close_error:
                        app_logger.debug(
                            "Ошибка при закрытии устаревшего соединения (игнорируется): %s",
                            close_error,
                        )
                    with self._lock:
                        if conn in self._all_conns:
                            self._all_conns.remove(conn)
                        if conn_id in self._connection_age:
                            del self._connection_age[conn_id]
                    conn = None
            except queue.Empty:
                app_logger.debug("Queue соединений пуста, создаём новое соединение")

            # Создаём соединение вне блокировки для предотвращения deadlock
            if conn is None:
                try:
                    conn = self._create_connection()
                    created_new = True
                    app_logger.debug("Создано новое соединение")
                except sqlite3.Error as db_error:
                    app_logger.error(
                        "Ошибка БД при создании соединения: %s", db_error, exc_info=True,
                    )
                    raise
                except OSError as os_error:
                    app_logger.error(
                        "Ошибка ОС при создании соединения: %s", os_error, exc_info=True,
                    )
                    raise
                except (RuntimeError, TypeError, ValueError) as e:
                    app_logger.error(
                        "Неожиданная ошибка при создании соединения: %s", e, exc_info=True,
                    )
                    raise

            if conn is None:
                raise RuntimeError("Не удалось получить соединение с БД: conn остался None")

            # Регистрация нового соединения под блокировкой
            if created_new:
                with self._lock:
                    self._local.connection = conn
                    if len(self._all_conns) >= self._pool_size:
                        app_logger.warning(
                            "Достигнут лимит соединений (%d), "
                            "новое соединение не добавляется в pool",
                            self._pool_size,
                        )
                    else:
                        self._all_conns.append(conn)
                        self._connection_age[id(conn)] = time.time()
            else:
                self._local.connection = conn
                app_logger.debug("Получено соединение из queue (reuse)")

            return conn

        except (sqlite3.Error, OSError, RuntimeError) as e:
            app_logger.error("Ошибка при получении соединения: %s", e)
            raise

    def return_connection(self, conn: sqlite3.Connection) -> None:
        """Возвращает соединение в пул для reuse.

        ISSUE-079: Обновляет _connection_age при возврате соединения.

        Оптимизация:
        - Возврат соединения в queue для повторного использования
        - Правильная очистка соединений
        - ISSUE-079: Сброс возраста соединения для предотвращения преждевременного закрытия

        Args:
            conn: Соединение для возврата в пул.

        """
        try:
            # ISSUE-079: Сбрасываем возраст соединения при возврате в пул
            # Это предотвращает преждевременное закрытие ещё полезного соединения
            conn_id = id(conn)
            with self._lock:
                self._connection_age[conn_id] = time.time()

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
            # Удаляем запись о возрасте по id(conn)
            if id(conn) in self._connection_age:
                del self._connection_age[id(conn)]

    def _create_connection(self) -> sqlite3.Connection:
        """Создаёт новое соединение с оптимизированными настройками.

        ID:060: Заменён conn.executescript() на отдельные conn.execute() для каждого PRAGMA.
        executescript() выполняет неявный COMMIT, что может нарушить транзакции.

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
            timeout=60.0,  # HIGH 14: Увеличенный таймаут для снижения конфликтов
            isolation_level=None,  # Autocommit режим для лучшей производительности
            check_same_thread=False,  # Потокобезопасность
        )

        # ID:060: Отдельные execute() для каждого PRAGMA вместо executescript()
        # executescript() выполняет неявный COMMIT, что может нарушить транзакции
        # ИСПРАВЛЕНИЕ #3: Прямая подстановка констант без f-string для ясности
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(f"PRAGMA cache_size={_SQLITE_PRAGMA_CACHE_SIZE}")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(f"PRAGMA busy_timeout={_SQLITE_PRAGMA_BUSY_TIMEOUT}")

        return conn

    def close(self) -> None:
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
                    app_logger.warning("Ошибка БД при закрытии соединения: %s", db_error)
                except OSError as os_error:
                    app_logger.warning("Ошибка ОС при закрытии соединения: %s", os_error)
                except (RuntimeError, TypeError, ValueError) as e:
                    app_logger.warning("Неожиданная ошибка при закрытии соединения: %s", e)
            self._all_conns.clear()
            # Очищаем словарь возрастов соединений
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

    # Алиас для обратной совместимости с тестами
    close_all = close

    @staticmethod
    def _cleanup_pool(all_conns: list[sqlite3.Connection], lock: threading.RLock) -> None:
        """Статический метод для гарантированной очистки пула соединений.

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
                        except (sqlite3.Error, OSError) as e:
                            app_logger.warning("Не удалось закрыть соединение с БД: %s", e)
                    all_conns.clear()
            except (RuntimeError, TypeError) as e:
                # Интерпретатор завершается - игнорируем ошибки
                app_logger.debug("Ошибка при очистке пула соединений: %s", e)

    def __enter__(self) -> "ConnectionPool":
        """Контекстный менеджер: вход.

        Returns:
            Экземпляр ConnectionPool для использования в контекстном менеджере.

        Пример:
            >>> with ConnectionPool(Path("cache.db")) as pool:
            ...     conn = pool.get_connection()
            ...     # работа с соединением

        """
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any,
    ) -> None:
        """Контекстный менеджер: выход.

        Args:
            exc_type: Тип исключения (если произошло).
            exc_val: Значение исключения (если произошло).
            exc_tb: Трассировка исключения (если произошло).

        Примечание:
            Гарантирует закрытие всех соединений даже при возникновении исключений.
            Все ошибки при закрытии логируются но не пробрасываются.

        """
        try:
            self.close()
        except (RuntimeError, TypeError, ValueError, OSError, sqlite3.Error) as close_error:
            app_logger.error(
                "Ошибка при закрытии пула соединений в контекстном менеджере: %s",
                close_error,
                exc_info=True,
            )
        # Возвращаем None (подавляем исключения) чтобы не мешать основной логике
