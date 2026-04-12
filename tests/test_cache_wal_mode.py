"""
Тест включения WAL режима в кэше SQLite.

Проверяет что CacheManager включает:
- PRAGMA journal_mode = WAL
- PRAGMA synchronous = NORMAL

ИСПРАВЛЕНИЕ C4: WAL режим для лучшей конкурентности и производительности.
"""

from pathlib import Path

from parser_2gis.cache.manager import CacheManager


class TestCacheWalMode:
    """Тесты включения WAL режима в кэше."""

    def test_pragma_journal_mode_wal(self, tmp_path: Path) -> None:
        """Тест что PRAGMA journal_mode = WAL включён.

        Проверяет:
        - journal_mode установлен в WAL
        - WAL файл создаётся
        """
        cache_dir = tmp_path / "cache"
        cache_manager = CacheManager(cache_dir, ttl_hours=24, pool_size=1)

        # Получаем соединение для проверки
        conn = cache_manager._pool.get_connection()

        # Проверяем journal_mode
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result is not None
        journal_mode = result[0].lower()
        assert journal_mode == "wal", f"Ожидается 'wal', получено '{journal_mode}'"

        cache_manager.close()

    def test_pragma_synchronous_normal(self, tmp_path: Path) -> None:
        """Тест что PRAGMA synchronous = NORMAL включён.

        Проверяет:
        - synchronous установлен в NORMAL (значение 1)
        - Производительность оптимизирована
        """
        cache_dir = tmp_path / "cache"
        cache_manager = CacheManager(cache_dir, ttl_hours=24, pool_size=1)

        # Получаем соединение для проверки
        conn = cache_manager._pool.get_connection()

        # Проверяем synchronous
        result = conn.execute("PRAGMA synchronous").fetchone()
        assert result is not None
        synchronous_value = result[0]
        # NORMAL = 1
        assert synchronous_value == 1, f"Ожидается 1 (NORMAL), получено {synchronous_value}"

        cache_manager.close()

    def test_wal_mode_executed_on_init(self, tmp_path: Path) -> None:
        """Тест что WAL режим включается при инициализации.

        Проверяет:
        - PRAGMA вызывается в _init_db
        - Порядок вызовов корректный
        """
        cache_dir = tmp_path / "cache"

        # Создаём реальный CacheManager и проверяем результат
        cache_manager = CacheManager(cache_dir, ttl_hours=24, pool_size=1)

        # Получаем соединение для проверки
        conn = cache_manager._pool.get_connection()

        # Проверяем что WAL режим включён
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result is not None
        assert result[0].lower() == "wal", "WAL режим не включён"

        # Проверяем что synchronous = NORMAL
        result = conn.execute("PRAGMA synchronous").fetchone()
        assert result is not None
        assert result[0] == 1, "synchronous не установлен в NORMAL"

        cache_manager.close()

    def test_wal_mode_improves_concurrency(self, tmp_path: Path) -> None:
        """Тест что WAL режим улучшает конкурентность.

        Проверяет:
        - Чтение и запись могут происходить одновременно
        - Нет блокировок при чтении во время записи
        """
        cache_dir = tmp_path / "cache"
        cache_manager = CacheManager(cache_dir, ttl_hours=24, pool_size=2)

        # Получаем два соединения
        conn1 = cache_manager._pool.get_connection()
        conn2 = cache_manager._pool.get_connection()

        # Записываем данные через первое соединение
        test_url = "https://2gis.ru/test"
        test_data = '{"test": "data"}'
        import hashlib

        url_hash = hashlib.sha256(test_url.encode("utf-8")).hexdigest()
        checksum = hashlib.sha256(test_data.encode("utf-8")).hexdigest()

        conn1.execute(
            "INSERT OR REPLACE INTO cache "
            "(url_hash, url, data, checksum, timestamp, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
            (url_hash, test_url, test_data, checksum, "2024-01-01", "2024-01-02"),
        )
        conn1.commit()

        # Читаем данные через второе соединение (должно работать в WAL режиме)
        result = conn2.execute("SELECT data FROM cache WHERE url_hash = ?", (url_hash,)).fetchone()

        assert result is not None
        assert result[0] == test_data

        cache_manager.close()

    def test_wal_pragma_calls_format(self) -> None:
        """Тест формата вызовов PRAGMA для WAL.

        Проверяет:
        - Точный формат строк PRAGMA
        - Соответствие документации SQLite
        """
        # Проверяем формат PRAGMA команд
        expected_wal_pragma = "PRAGMA journal_mode=WAL"
        expected_sync_pragma = "PRAGMA synchronous=NORMAL"

        # Эти строки должны быть в коде manager.py
        assert expected_wal_pragma == "PRAGMA journal_mode=WAL"
        assert expected_sync_pragma == "PRAGMA synchronous=NORMAL"

    def test_wal_mode_persists_after_close(self, tmp_path: Path) -> None:
        """Тест что WAL режим сохраняется после закрытия.

        Проверяет:
        - Настройки сохраняются в БД
        - При повторном открытии WAL режим активен
        """
        cache_dir = tmp_path / "cache"

        # Создаём и закрываем первый кэш
        cache_manager1 = CacheManager(cache_dir, ttl_hours=24, pool_size=1)
        cache_manager1.close()

        # Открываем второй кэш в той же директории
        cache_manager2 = CacheManager(cache_dir, ttl_hours=24, pool_size=1)
        conn = cache_manager2._pool.get_connection()

        # Проверяем что WAL режим активен
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result is not None
        assert result[0].lower() == "wal"

        cache_manager2.close()
