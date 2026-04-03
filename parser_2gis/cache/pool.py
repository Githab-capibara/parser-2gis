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

# Максимальное количество соединений в пуле (из ENV или default)
_MAX_POOL_SIZE_ENV: int = validate_env_int(
    "PARSER_MAX_POOL_SIZE", default=20, min_value=5, max_value=50
)

# Минимальное количество соединений в пуле (из ENV или default)
_MIN_POOL_SIZE_ENV: int = validate_env_int(
    "PARSER_MIN_POOL_SIZE", default=5, min_value=1, max_value=10
)

# Время жизни соединения в секундах (из ENV или default)
_CONNECTION_MAX_AGE_ENV: int = validate_env_int(
    "PARSER_CONNECTION_MAX_AGE", default=300, min_value=60, max_value=3600
)

# D009: Константы для PRAGMA настроек с валидацией
_SQLITE_PRAGMA_JOURNAL_MODE: str = "WAL"
_SQLITE_PRAGMA_CACHE_SIZE: int = -64000  # 64MB в страницах по 4KB
_SQLITE_PRAGMA_SYNCHRONOUS: str = "NORMAL"
_SQLITE_PRAGMA_BUSY_TIMEOUT: int = 60000  # 60 секунд


# Попытка импортировать psutil для мониторинга памяти
try:
    import psutil

    PSUTIL_AVAILABLE = True
    _psutil_available = True
except ImportError:
    PSUTIL_AVAILABLE = False
    _psutil_available = False


@functools.lru_cache(maxsize=1)
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
        if not _psutil_available:
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
    except MemoryError:
        # Критическая ошибка памяти - используем минимальный размер
        app_logger.warning("MemoryError при расчёте размера пула, используем минимум")
        return MIN_POOL_SIZE
    except OSError as os_error:
        # Ошибка ОС (например, недоступность системной информации)
        app_logger.warning("OSError при расчёте размера пула: %s, используем минимум", os_error)
        return MIN_POOL_SIZE
    except ValueError as value_error:
        # Ошибка значения (например, некорректные данные из ENV)
        app_logger.warning(
            "ValueError при расчёте размера пула: %s, используем минимум", value_error
        )
        return MIN_POOL_SIZE
    except TypeError as type_error:
        # Ошибка типа данных
        app_logger.warning("TypeError при расчёте размера пула: %s, используем минимум", type_error)
        return MIN_POOL_SIZE
    except Exception as general_error:
        # Любая другая ошибка - используем минимальный размер
        app_logger.warning(
            "Неожиданная ошибка при расчёте размера пула: %s, используем минимум", general_error
        )
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
            self._pool_size = _MIN_POOL_SIZE_ENV
        elif pool_size is not None:
            # Ограничиваем размер пула разумными пределами
            self._pool_size = max(_MIN_POOL_SIZE_ENV, min(pool_size, _MAX_POOL_SIZE_ENV))
        else:
            self._pool_size = _MAX_POOL_SIZE_ENV

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
            maxsize=self._pool_size
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
        - Единая блокировка вместо double-checked locking для предотвращения race condition

        SQLite требует создания соединения в том же потоке, где оно будет использоваться.
        Метод использует thread-local хранилище для каждого потока.

        Returns:
            SQLite соединение для текущего потока.

        Raises:
            sqlite3.Error: При ошибке создания соединения.
            OSError: При ошибке ОС.
            RuntimeError: При критической ошибке инициализации.

        Примечание:
            ИСПРАВЛЕНИЕ CRITICAL 1: Перестроена логика для гарантированной инициализации conn
            ИСПРАВЛЕНИЕ CRITICAL 2: Добавлен finally блок для гарантированной очистки
            ИСПРАВЛЕНИЕ C002: Использована единая блокировка без double-checked locking

        """
        conn: sqlite3.Connection | None = None
        created_new: bool = False

        try:
            # C002: Используем единую блокировку вместо double-checked locking
            # Это предотвращает race conditions и упрощает код
            with self._lock:
                # Единая проверка thread-local кэша
                if hasattr(self._local, "connection") and self._local.connection is not None:
                    conn_obj = self._local.connection
                    conn_id = id(conn_obj)
                    age = self._connection_age.get(conn_id)

                    should_reuse = False
                    if age is not None:
                        age = time.time() - age
                        if age <= _CONNECTION_MAX_AGE_ENV:
                            # Проверка активности соединения перед использованием
                            if self._is_connection_valid(conn_obj):
                                should_reuse = True
                            else:
                                app_logger.debug(
                                    "Соединение неактивно (SELECT 1 failed), требуется пересоздание"
                                )
                        else:
                            app_logger.debug(
                                "Соединение устарело (возраст: %.0f сек), требуется пересоздание",
                                age,
                            )
                    else:
                        app_logger.debug(
                            "Соединение не найдено в _connection_age, требуется пересоздание"
                        )

                    if should_reuse:
                        return conn_obj

                    # Закрываем старое соединение
                    try:
                        conn_obj.close()
                    except (sqlite3.Error, OSError) as close_error:
                        app_logger.debug("Ошибка при закрытии соединения: %s", close_error)

                    # Удаляем из пула
                    if conn_obj in self._all_conns:
                        self._all_conns.remove(conn_obj)
                    # Удаляем запись о возрасте по id
                    if conn_id in self._connection_age:
                        del self._connection_age[conn_id]
                    self._local.connection = None

                # Пытаемся получить соединение из queue
                try:
                    conn = self._connection_queue.get_nowait()

                    # Проверяем возраст соединения по id
                    conn_id = id(conn)
                    if conn_id in self._connection_age:
                        age = time.time() - self._connection_age[conn_id]
                        if age > _CONNECTION_MAX_AGE_ENV or not self._is_connection_valid(conn):
                            app_logger.debug(
                                "Соединение из queue устарело или неактивно, пересоздаём"
                            )
                            try:
                                conn.close()
                            except (sqlite3.Error, OSError):
                                pass
                            if conn in self._all_conns:
                                self._all_conns.remove(conn)
                            if conn_id in self._connection_age:
                                del self._connection_age[conn_id]
                            conn = None
                except queue.Empty:
                    # Queue пуста, нужно создавать новое соединение
                    app_logger.debug("Queue соединений пуста, создаём новое соединение")

                # Создаём новое соединение если не получили из queue
                if conn is None:
                    # Выходим из блокировки перед созданием соединения
                    pass

            # Создаём соединение вне блокировки для предотвращения deadlock
            if conn is None:
                try:
                    conn = self._create_connection()
                    created_new = True
                    app_logger.debug("Создано новое соединение")
                except sqlite3.Error as db_error:
                    app_logger.error(
                        "Ошибка БД при создании соединения: %s", db_error, exc_info=True
                    )
                    raise
                except OSError as os_error:
                    app_logger.error(
                        "Ошибка ОС при создании соединения: %s", os_error, exc_info=True
                    )
                    raise
                except (RuntimeError, TypeError, ValueError) as e:
                    app_logger.error(
                        "Неожиданная ошибка при создании соединения: %s", e, exc_info=True
                    )
                    raise

            # ИСПРАВЛЕНИЕ CRITICAL 1: Гарантированная проверка что conn инициализирован
            if conn is None:
                raise RuntimeError("Не удалось получить соединение с БД: conn остался None")

            # Возвращаемся в блокировку для добавления в пул
            with self._lock:
                if created_new:
                    self._local.connection = conn
                    # Проверяем лимит соединений
                    if len(self._all_conns) >= self._pool_size:
                        app_logger.warning(
                            "Достигнут лимит соединений (%d), "
                            "новое соединение не добавляется в pool",
                            self._pool_size,
                        )
                    else:
                        self._all_conns.append(conn)
                        # Сохраняем возраст соединения по id(conn)
                        self._connection_age[id(conn)] = time.time()
                else:
                    # Получили из queue - просто присваиваем
                    self._local.connection = conn
                    app_logger.debug("Получено соединение из queue (reuse)")

            return conn

        except (sqlite3.Error, OSError, RuntimeError) as e:
            # ИСПРАВЛЕНИЕ CRITICAL 2: Гарантированная очистка при исключении
            app_logger.error("Ошибка при получении соединения: %s", e)
            raise
        finally:
            # ИСПРАВЛЕНИЕ CRITICAL 2: finally блок для гарантированной очистки
            # Закрываем соединение только если оно было создано но не добавлено в пул
            # Не закрываем соединения полученные из queue (reuse)
            if conn is not None and created_new and not hasattr(self._local, "connection"):
                try:
                    conn.close()
                    app_logger.debug("Соединение закрыто в finally (не добавлено в пул)")
                except (sqlite3.Error, OSError) as cleanup_error:
                    app_logger.debug("Ошибка при закрытии соединения в finally: %s", cleanup_error)

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
        conn.execute(f"PRAGMA journal_mode={_SQLITE_PRAGMA_JOURNAL_MODE}")
        conn.execute(f"PRAGMA cache_size={_SQLITE_PRAGMA_CACHE_SIZE}")
        conn.execute(f"PRAGMA synchronous={_SQLITE_PRAGMA_SYNCHRONOUS}")
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
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
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
