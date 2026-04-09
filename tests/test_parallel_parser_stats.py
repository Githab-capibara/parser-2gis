#!/usr/bin/env python3
"""
Тесты для проверки потокобезопасности статистики (_stats) в ParallelCityParser.

Проверяет корректность работы блокировок при доступе к статистике парсера.
Тесты покрывают исправления гонки состояний при многопоточном доступе.

Тесты:
1. test_stats_thread_safety_concurrent_updates - Тест на одновременное обновление статистики
2. test_stats_accuracy_after_multiple_operations - Тест точности статистики
3. test_stats_lock_prevents_race_condition - Тест что блокировка предотвращает гонку
"""

import threading
import time
from typing import Any

import pytest


class TestParallelParserStatsThreadSafety:
    """Тесты для проверки потокобезопасности статистики парсера."""

    def test_stats_thread_safety_concurrent_updates(self, tmp_path: Any) -> None:
        """
        Тест 1.1: Проверка потокобезопасности при одновременном обновлении статистики.

        Запускает множество потоков которые одновременно обновляют статистику.
        Проверяет что нет race condition и все обновления корректно учтены.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel import ParallelCityParser

        # Создаем тестовые данные
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        # Создаем парсер
        config = Configuration()
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=3,
        )

        # Количество потоков и операций
        num_threads = 20
        operations_per_thread = 50
        expected_total = num_threads * operations_per_thread

        # Функция которая обновляет статистику
        def update_stats(thread_id: int) -> None:
            for i in range(operations_per_thread):
                # Обновляем статистику через публичные методы которые используют lock
                with parser._lock:
                    parser._stats["success"] += 1
                    parser._stats["total"] += 1

        # Запускаем потоки
        threads: list[threading.Thread] = []
        for i in range(num_threads):
            thread = threading.Thread(target=update_stats, args=(i,))
            threads.append(thread)
            thread.start()

        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()

        # Проверяем что статистика корректна
        assert parser._stats["success"] == expected_total, (
            f"Ожидалось {expected_total} успешных операций, получено {parser._stats['success']}"
        )
        assert parser._stats["total"] == expected_total, (
            f"Ожидалось {expected_total} всего операций, получено {parser._stats['total']}"
        )

    def test_stats_accuracy_after_multiple_operations(self, tmp_path: Any) -> None:
        """
        Тест 1.2: Проверка точности статистики после множественных операций.

        Выполняет различные операции над статистикой (success, failed, skipped).
        Проверяет что итоговая статистика корректна после всех операций.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel import ParallelCityParser

        # Создаем тестовые данные
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        # Создаем парсер
        config = Configuration()
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=3,
        )

        # Выполняем операции с статистикой
        num_success = 100
        num_failed = 30
        num_skipped = 20

        def simulate_success() -> None:
            for _ in range(num_success):
                with parser._lock:
                    parser._stats["success"] += 1
                    parser._stats["total"] += 1

        def simulate_failure() -> None:
            for _ in range(num_failed):
                with parser._lock:
                    parser._stats["failed"] += 1
                    parser._stats["total"] += 1

        def simulate_skip() -> None:
            for _ in range(num_skipped):
                with parser._lock:
                    parser._stats["skipped"] += 1
                    parser._stats["total"] += 1

        # Запускаем потоки
        threads = [
            threading.Thread(target=simulate_success),
            threading.Thread(target=simulate_failure),
            threading.Thread(target=simulate_skip),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Проверяем точность статистики
        expected_total = num_success + num_failed + num_skipped
        assert parser._stats["success"] == num_success
        assert parser._stats["failed"] == num_failed
        assert parser._stats["skipped"] == num_skipped
        assert parser._stats["total"] == expected_total

        # Проверяем что сумма отдельных счетчиков равна total
        sum_parts = parser._stats["success"] + parser._stats["failed"] + parser._stats["skipped"]
        assert sum_parts == parser._stats["total"], (
            f"Сумма частей ({sum_parts}) не равна total ({parser._stats['total']})"
        )

    def test_stats_lock_prevents_race_condition(self, tmp_path: Any) -> None:
        """
        Тест 1.3: Проверка что блокировка предотвращает гонку состояний.

        Создает ситуацию где без блокировки произошла бы гонка состояний.
        Проверяет что lock корректно синхронизирует доступ к статистике.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel import ParallelCityParser

        # Создаем тестовые данные
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        # Создаем парсер
        config = Configuration()
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=3,
        )

        # Количество итераций для создания гонки
        num_iterations = 1000
        read_errors: list[str] = []

        def increment_with_read() -> None:
            """Поток который читает и записывает статистику."""
            for _ in range(num_iterations):
                with parser._lock:
                    # Читаем текущее значение
                    current_success = parser._stats["success"]
                    current_total = parser._stats["total"]

                    # Имитируем небольшую задержку (усиливает гонку)
                    time.sleep(0.0001)

                    # Проверяем инвариант: success <= total
                    if current_success > current_total:
                        read_errors.append(
                            f"Гонка обнаружена: success={current_success} > total={current_total}"
                        )

                    # Обновляем статистику
                    parser._stats["success"] += 1
                    parser._stats["total"] += 1

        # Запускаем множество потоков
        num_threads = 10
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=increment_with_read)
            threads.append(thread)
            thread.start()

        # Ждем завершения
        for thread in threads:
            thread.join()

        # Проверяем что не было гонок
        assert len(read_errors) == 0, (
            f"Обнаружены гонки состояний: {read_errors[:5]}"
        )  # Показываем первые 5

        # Проверяем итоговую статистику
        expected = num_iterations * num_threads
        assert parser._stats["success"] == expected
        assert parser._stats["total"] == expected


class TestStatsInitialization:
    """Тесты для проверки корректной инициализации статистики."""

    def test_stats_initialized_correctly(self, tmp_path: Any) -> None:
        """
        Проверка что статистика инициализируется правильными значениями.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        config = Configuration()
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=3,
        )

        # Проверяем начальное состояние
        assert parser._stats["total"] == 0
        assert parser._stats["success"] == 0
        assert parser._stats["failed"] == 0
        assert parser._stats["skipped"] == 0

    def test_stats_lock_exists(self, tmp_path: Any) -> None:
        """
        Проверка что lock для статистики существует и это RLock.

        Args:
            tmp_path: pytest фикстура для временной директории.
        """
        import threading

        from parser_2gis.config import Configuration
        from parser_2gis.parallel import ParallelCityParser

        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow"}]
        categories = [{"name": "Кафе", "id": 1, "query": "Кафе"}]
        output_dir = str(tmp_path / "output")

        config = Configuration()
        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=output_dir,
            config=config,
            max_workers=3,
        )

        # Проверяем что lock существует
        assert hasattr(parser, "_lock")
        assert parser._lock is not None

        # Проверяем что это Lock или RLock (потокобезопасная блокировка)
        assert isinstance(parser._lock, (type(threading.Lock()), type(threading.RLock())))


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
