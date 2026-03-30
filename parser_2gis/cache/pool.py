"""
Модуль пула соединений для SQLite.

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

import queue
import sqlite3
import threading
import time
import weakref
from pathlib import Path
from typing import Dict, List, Optional

from ..constants import MAX_POOL_SIZE, MIN_POOL_SIZE, validate_env_int
from ..logger.logger import logger as app_logger


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


# Попытка импортировать psutil для мониторинга памяти
try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False
    psutil = None  # type: ignore


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
    finally:
        # Гарантия выполнения любой необходимой очистки
        # В данном случае очистка не требуется, но блок finally обеспечивает структуру
        pass


class ConnectionPool:
    """
    Пул соединений для SQLite с reuse и queue.Queue для управления.

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
        pool_size: Optional[int] = None,
        use_dynamic: bool = False,  # Для обратной совместимости
    ) -> None:
        """
        Инициализация пула соединений.

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

        self._local = threading.local()
        self._all_conns: List[sqlite3.Connection] = []
        # Используем RLock для реентерабельности
        # RLock позволяет одному и тому же потоку получать блокировку несколько раз
        self._lock = threading.RLock()
        # queue.Queue для управления соединениями
        self._connection_queue: queue.Queue[sqlite3.Connection] = queue.Queue(
            maxsize=self._pool_size
        )
        # Кэш времени создания соединений для отслеживания возраста
        self._connection_age: Dict[int, float] = {}
        # weakref.finalize() для гарантированной очистки ресурсов
        self._weak_ref = weakref.ref(self)
        self._finalizer = weakref.finalize(self, self._cleanup_pool, self._all_conns, self._lock)

    def get_connection(self) -> sqlite3.Connection:
        """
        Получает соединение для текущего потока с reuse.

        Оптимизация:
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
                    if age <= _CONNECTION_MAX_AGE_ENV:
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
                        if age > _CONNECTION_MAX_AGE_ENV:
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

        Оптимизация:
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
            check_same_thread=False,  # Потокобезопасность
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

    # Алиас для обратной совместимости с тестами
    close_all = close

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
                        except (sqlite3.Error, OSError) as e:
                            app_logger.warning("Не удалось закрыть соединение с БД: %s", e)
                    all_conns.clear()
            except (RuntimeError, TypeError) as e:
                # Интерпретатор завершается - игнорируем ошибки
                app_logger.debug("Ошибка при очистке пула соединений: %s", e)

    def __enter__(self) -> "ConnectionPool":
        """
        Контекстный менеджер: вход.

        Returns:
            Экземпляр ConnectionPool для использования в контекстном менеджере.

        Пример:
            >>> with ConnectionPool(Path("cache.db")) as pool:
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
            self.close()
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
            Всегда вызывайте close() явно или используйте контекстный менеджер.
        """
        # weakref.finalize() уже зарегистрирован в __init__ и вызовет _cleanup_pool
        # Этот метод используется только для логирования
        try:
            # Проверяем есть ли финализатор
            if hasattr(self, "_finalizer") and self._finalizer is not None:
                if self._finalizer.detach():
                    # Финализатор был успешно отделён и вызван
                    app_logger.debug("ConnectionPool очищен через weakref.finalize()")
                    return

            # Fallback: если финализатор не сработал
            if hasattr(self, "_all_conns") and self._all_conns:
                app_logger.warning(
                    "ConnectionPool уничтожается сборщиком мусора с %d незакрытыми соединениями. "
                    "Всегда вызывайте close() явно или используйте контекстный менеджер.",
                    len(self._all_conns),
                )
        except (MemoryError, KeyboardInterrupt, SystemExit):
            # Критические исключения - пробрасываем дальше
            raise
        except (RuntimeError, TypeError, ValueError, OSError) as del_error:
            # В __del__ нельзя выбрасывать исключения - только логируем
            app_logger.debug("Ошибка в __del__ ConnectionPool: %s", del_error)
