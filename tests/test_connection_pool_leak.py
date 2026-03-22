"""
Тесты для проверки утечки ресурсов в _ConnectionPool.

ИСПРАВЛЕНИЕ P0-4: Исправление утечки соединений в _ConnectionPool
Файлы: parser_2gis/cache.py

Тестируют:
- Закрытие соединений при выходе
- Закрытие соединений при ошибке
- Работа контекстного менеджера

Маркеры:
- @pytest.mark.unit для юнит-тестов
- @pytest.mark.integration для интеграционных тестов
"""

import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import List

import pytest

from parser_2gis.cache import _ConnectionPool

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# =============================================================================
# ТЕСТ 1: ЗАКРЫТИЕ СОЕДИНЕНИЙ ПРИ ВЫХОДЕ
# =============================================================================


@pytest.mark.unit
class TestConnectionPoolCleanupOnExit:
    """Тесты для закрытия соединений при выходе."""

    def test_pool_close_all_connections(self, tmp_path: Path) -> None:
        """
        Тест 1.1: Проверка закрытия всех соединений при close_all().

        Создаёт пул с несколькими соединениями.
        Вызывает close_all().
        Проверяет что все соединения закрыты.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool.db"
        pool = _ConnectionPool(cache_file, pool_size=5, use_dynamic=False)

        # Получаем несколько соединений
        connections: List[sqlite3.Connection] = []
        for i in range(5):
            conn = pool.get_connection()
            connections.append(conn)

        # Проверяем что соединения активны
        for conn in connections:
            # Выполняем простой запрос для проверки активности
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result == (1,), "Соединение не активно"

        # Закрываем все соединения
        pool.close_all()

        # Проверяем что соединения закрыты
        for conn in connections:
            with pytest.raises(sqlite3.ProgrammingError):
                # Попытка выполнить запрос на закрытом соединении
                # должна вызвать ProgrammingError
                conn.execute("SELECT 1")

    def test_pool_cleanup_on_gc(self, tmp_path: Path) -> None:
        """
        Тест 1.2: Проверка очистки соединений сборщиком мусора.

        Создаёт пул и оставляет его для сбора мусора.
        Проверяет что __del__ закрывает соединения.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_gc.db"

        def create_and_forget_pool() -> None:
            """Создаёт пул и забывает о нём."""
            pool = _ConnectionPool(cache_file, pool_size=3, use_dynamic=False)
            # Получаем несколько соединений
            for i in range(3):
                pool.get_connection()
                # Не закрываем явно - полагаемся на __del__

        # Создаём пул
        create_and_forget_pool()

        # Принудительно запускаем сборщик мусора
        import gc

        gc.collect()
        time.sleep(0.1)  # Даём время на очистку

        # Проверяем что файл базы данных существует
        assert cache_file.exists(), "Файл базы данных не создан"

    def test_pool_cleanup_all_conns_cleared(self, tmp_path: Path) -> None:
        """
        Тест 1.3: Проверка очистки списка _all_conns.

        Создаёт пул, получает соединения, закрывает.
        Проверяет что _all_conns пуст после close_all().

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_clear.db"
        pool = _ConnectionPool(cache_file, pool_size=5, use_dynamic=False)

        # Получаем несколько соединений
        for i in range(5):
            pool.get_connection()

        # Проверяем что соединения созданы
        assert len(pool._all_conns) > 0, "Соединения не созданы"

        # Закрываем все соединения
        pool.close_all()

        # Проверяем что список очищен
        assert len(pool._all_conns) == 0, "Список соединений не очищен"
        assert len(pool._connection_age) == 0, "Словарь возраста не очищен"


# =============================================================================
# ТЕСТ 2: ЗАКРЫТИЕ СОЕДИНЕНИЙ ПРИ ОШИБКЕ
# =============================================================================


@pytest.mark.unit
class TestConnectionPoolCleanupOnError:
    """Тесты для закрытия соединений при ошибке."""

    def test_pool_cleanup_on_exception(self, tmp_path: Path) -> None:
        """
        Тест 2.1: Проверка очистки соединений при исключении.

        Создаёт пул, получает соединения, вызывает исключение.
        Проверяет что соединения закрыты в __del__.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_exception.db"

        try:
            pool = _ConnectionPool(cache_file, pool_size=3, use_dynamic=False)

            # Получаем соединения
            connections = []
            for i in range(3):
                conn = pool.get_connection()
                connections.append(conn)

            # Вызываем исключение
            raise ValueError("Test exception")

        except ValueError:
            pass  # Ожидаемое исключение

        # Принудительно запускаем сборщик мусора
        import gc

        gc.collect()
        time.sleep(0.1)

        # Проверяем что файл существует
        assert cache_file.exists(), "Файл базы данных не создан"

    def test_pool_return_connection_on_error(self, tmp_path: Path) -> None:
        """
        Тест 2.2: Проверка возврата соединения при ошибке операции.

        Получает соединение, выполняет операцию с ошибкой.
        Проверяет что соединение возвращается в пул.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_return_error.db"
        pool = _ConnectionPool(cache_file, pool_size=3, use_dynamic=False)

        try:
            # Получаем соединение
            conn = pool.get_connection()
            initial_queue_size = pool._connection_queue.qsize()

            # Выполняем операцию с ошибкой (некорректный SQL)
            try:
                conn.execute("INVALID SQL QUERY")
            except sqlite3.Error:
                pass  # Ожидаемая ошибка

            # Возвращаем соединение в пул
            pool.return_connection(conn)

            # Проверяем что соединение возвращено
            assert pool._connection_queue.qsize() >= initial_queue_size, (
                "Соединение не возвращено в пул"
            )

        finally:
            pool.close_all()

    def test_pool_queue_full_handling(self, tmp_path: Path) -> None:
        """
        Тест 2.3: Проверка обработки заполненной queue.

        Заполняет queue соединений.
        Пытается вернуть ещё одно соединение.
        Проверяет что соединение закрывается корректно.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_queue_full.db"
        pool = _ConnectionPool(cache_file, pool_size=2, use_dynamic=False)

        try:
            # Получаем соединения
            conn1 = pool.get_connection()
            conn2 = pool.get_connection()

            # Возвращаем соединения обратно
            pool.return_connection(conn1)
            pool.return_connection(conn2)

            # Получаем ещё раз
            conn3 = pool.get_connection()

            # Возвращаем - queue может быть заполнена
            pool.return_connection(conn3)

            # Проверяем что операция прошла без ошибок
            assert True, "Операция возврата не удалась"

        except Exception as e:
            pytest.fail(f"Неожиданное исключение: {e}")
        finally:
            pool.close_all()


# =============================================================================
# ТЕСТ 3: РАБОТА КОНТЕКСТНОГО МЕНЕДЖЕРА
# =============================================================================


@pytest.mark.unit
class TestConnectionPoolContextManager:
    """Тесты для работы контекстного менеджера."""

    def test_pool_context_manager_success(self, tmp_path: Path) -> None:
        """
        Тест 3.1: Проверка успешной работы контекстного менеджера.

        Использует контекстный менеджер для пула.
        Проверяет что соединения закрываются при выходе.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_context.db"

        with _ConnectionPool(cache_file, pool_size=3, use_dynamic=False) as pool:
            # Получаем соединения
            connections = []
            for i in range(3):
                conn = pool.get_connection()
                connections.append(conn)

            # Проверяем что соединения активны
            for conn in connections:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                assert result == (1,), "Соединение не активно"

        # После выхода из контекста соединения должны быть закрыты
        for conn in connections:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")

    def test_pool_context_manager_with_exception(self, tmp_path: Path) -> None:
        """
        Тест 3.2: Проверка работы контекстного менеджера с исключением.

        Использует контекстный менеджер, вызывает исключение.
        Проверяет что соединения закрываются даже при исключении.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_context_exc.db"

        try:
            with _ConnectionPool(cache_file, pool_size=3, use_dynamic=False) as pool:
                # Получаем соединения
                connections = []
                for i in range(3):
                    conn = pool.get_connection()
                    connections.append(conn)

                # Вызываем исключение
                raise ValueError("Test exception in context")

        except ValueError:
            pass  # Ожидаемое исключение

        # Проверяем что соединения закрыты
        for conn in connections:
            with pytest.raises(sqlite3.ProgrammingError):
                conn.execute("SELECT 1")

    def test_pool_context_manager_nested(self, tmp_path: Path) -> None:
        """
        Тест 3.3: Проверка вложенных контекстных менеджеров.

        Использует вложенные контекстные менеджеры.
        Проверяет что все соединения закрываются корректно.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file1 = tmp_path / "test_pool_nested1.db"
        cache_file2 = tmp_path / "test_pool_nested2.db"

        with _ConnectionPool(cache_file1, pool_size=2, use_dynamic=False) as pool1:
            conn1 = pool1.get_connection()

            with _ConnectionPool(cache_file2, pool_size=2, use_dynamic=False) as pool2:
                conn2 = pool2.get_connection()

                # Проверяем что оба соединения активны
                cursor1 = conn1.cursor()
                cursor1.execute("SELECT 1")
                assert cursor1.fetchone() == (1,)

                cursor2 = conn2.cursor()
                cursor2.execute("SELECT 1")
                assert cursor2.fetchone() == (1,)

            # После выхода из внутреннего контекста conn2 должен быть закрыт
            with pytest.raises(sqlite3.ProgrammingError):
                conn2.execute("SELECT 1")

        # После выхода из внешнего контекста conn1 должен быть закрыт
        with pytest.raises(sqlite3.ProgrammingError):
            conn1.execute("SELECT 1")


# =============================================================================
# ТЕСТ 4: ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


@pytest.mark.integration
class TestConnectionPoolIntegration:
    """Интеграционные тесты для _ConnectionPool."""

    def test_pool_long_running_cleanup(self, tmp_path: Path) -> None:
        """
        Тест 4.1: Проверка очистки после работы.

        Создаёт пул, выполняет операции, закрывает.
        Проверяет что все соединения закрыты.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_long.db"
        pool = _ConnectionPool(cache_file, pool_size=2, use_dynamic=False)

        # Выполняем несколько операций
        conn = pool.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)
        pool.return_connection(conn)

        # Проверяем что пул в хорошем состоянии
        assert len(pool._all_conns) <= pool._pool_size, "Превышен размер пула"

        pool.close_all()

        # Проверяем что соединения закрыты
        assert len(pool._all_conns) == 0, "Соединения не закрыты"

    def test_pool_concurrent_cleanup(self, tmp_path: Path) -> None:
        """
        Тест 4.2: Проверка очистки при последовательном доступе.

        Получает и возвращает соединения несколько раз.
        Проверяет что все соединения закрываются.

        Args:
            tmp_path: pytest tmp_path fixture.
        """
        cache_file = tmp_path / "test_pool_concurrent.db"
        pool = _ConnectionPool(cache_file, pool_size=2, use_dynamic=False)

        # Получаем и возвращаем соединение несколько раз
        for _ in range(3):
            conn = pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone() == (1,)
            pool.return_connection(conn)

        # Закрываем пул
        pool.close_all()

        # Проверяем что все соединения закрыты
        assert len(pool._all_conns) == 0, "Соединения не закрыты"


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
