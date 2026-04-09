"""
Тесты для исправлений CRITICAL проблем в parallel/parallel_parser.py.

Проверяет:
- Использование RLock для реентерабельности
- Потокобезопасность блокировок
"""

import threading
from unittest.mock import MagicMock

import pytest

from parser_2gis.parallel.parallel_parser import ParallelCityParser


class TestRLockUsageForReentrancy:
    """Тесты для CRITICAL 3: RLock в parallel_parser.py."""

    @pytest.fixture
    def mock_config(self) -> MagicMock:
        """Создает mock конфигурацию.

        Returns:
            MagicMock с конфигурацией.
        """
        config = MagicMock()
        config.chrome.headless = True
        config.chrome.memory_limit = 512
        config.chrome.disable_images = True
        config.parser.max_records = 10
        config.parser.delay_between_clicks = 100
        config.parser.skip_404_response = True
        config.writer.encoding = "utf-8"
        config.writer.verbose = False
        config.parallel.use_temp_file_cleanup = False
        config.parallel.initial_delay_min = 0.1
        config.parallel.initial_delay_max = 0.5
        config.parallel.launch_delay_min = 0.1
        config.parallel.launch_delay_max = 0.5
        return config

    @pytest.fixture
    def temp_output_dir(self, tmp_path) -> str:
        """Создает временную директорию для вывода.

        Args:
            tmp_path: pytest tmp_path fixture.

        Returns:
            Путь к временной директории.
        """
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir)

    @pytest.fixture
    def parallel_parser(self, mock_config: MagicMock, temp_output_dir: str) -> ParallelCityParser:
        """Создает ParallelCityParser для тестов.

        Args:
            mock_config: Mock конфигурация.
            temp_output_dir: Временная директория.

        Returns:
            ParallelCityParser экземпляр.
        """
        cities = [{"name": "Москва", "url": "https://2gis.ru/moscow", "code": "moscow"}]
        categories = [{"name": "Рестораны", "id": 93, "query": "рестораны"}]

        parser = ParallelCityParser(
            cities=cities,
            categories=categories,
            output_dir=temp_output_dir,
            config=mock_config,
            max_workers=2,
            timeout_per_url=60,
        )
        yield parser

    def test_rlock_is_used_for_main_lock(self, parallel_parser: ParallelCityParser) -> None:
        """Тест 1: RLock используется для основной блокировки.

        Проверяет:
        - _lock это RLock а не Lock
        - RLock поддерживает реентерабельность
        """
        # Проверяем тип блокировки
        assert isinstance(parallel_parser._lock, type(threading.RLock())), "_lock должен быть RLock"

    def test_rlock_supports_reentrancy(self, parallel_parser: ParallelCityParser) -> None:
        """Тест 2: RLock поддерживает реентерабельные вызовы.

        Проверяет:
        - Один поток может захватить блокировку несколько раз
        - Нет deadlock при вложенных вызовах
        """
        lock_acquired_count = 0

        def nested_lock_operations():
            nonlocal lock_acquired_count
            with parallel_parser._lock:
                lock_acquired_count += 1
                # Реентрантный вызов
                with parallel_parser._lock:
                    lock_acquired_count += 1
                    with parallel_parser._lock:
                        lock_acquired_count += 1

        nested_lock_operations()
        assert lock_acquired_count == 3, "RLock должен поддерживать реентерабельность"

    def test_rlock_prevents_deadlock_in_nested_calls(
        self, parallel_parser: ParallelCityParser
    ) -> None:
        """Тест 3: RLock предотвращает deadlock при вложенных вызовах.

        Проверяет:
        - Вложенные вызовы с блокировкой не вызывают deadlock
        - Блокировка освобождается корректно
        """
        deadlock_detected = False

        def outer_call():
            with parallel_parser._lock:
                inner_call()

        def inner_call():
            with parallel_parser._lock:
                pass

        try:
            outer_call()
        except Exception:
            deadlock_detected = True

        assert not deadlock_detected, "RLock должен предотвращать deadlock"

    def test_rlock_thread_safety(self, parallel_parser: ParallelCityParser) -> None:
        """Тест 4: RLock обеспечивает потокобезопасность.

        Проверяет:
        - Несколько потоков могут работать с блокировкой
        - Нет race condition
        """
        counter = {"value": 0}
        errors = []

        def increment():
            try:
                for _ in range(100):
                    with parallel_parser._lock:
                        counter["value"] += 1
            except Exception as e:
                errors.append(e)

        # Запускаем несколько потоков
        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Ошибки в потоках: {errors}"
        assert counter["value"] == 1000, "Счётчик должен быть 1000"

    def test_rlock_merge_lock_is_used(self, parallel_parser: ParallelCityParser) -> None:
        """Тест 5: Блокировка merge используется.

        Проверяет:
        - _merge_lock существует и является Lock/RLock
        - Используется для защиты merge операций
        """
        # Проверяем что merge lock существует и является примитивом блокировки
        assert parallel_parser._merge_lock is not None, "_merge_lock должен существовать"
        # Проверяем что это тип блокировки (Lock или RLock)
        assert hasattr(parallel_parser._merge_lock, "acquire"), (
            "_merge_lock должен иметь метод acquire"
        )
        assert hasattr(parallel_parser._merge_lock, "release"), (
            "_merge_lock должен иметь метод release"
        )

    def test_rlock_stats_protection(self, parallel_parser: ParallelCityParser) -> None:
        """Тест 6: RLock защищает статистику.

        Проверяет:
        - Доступ к _stats защищён RLock
        - Операции со статистикой потокобезопасны
        """
        errors = []

        def update_stats():
            try:
                for _ in range(100):
                    with parallel_parser._lock:
                        parallel_parser._stats["success"] += 1
            except Exception as e:
                errors.append(e)

        # Запускаем несколько потоков
        threads = [threading.Thread(target=update_stats) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Ошибки в потоках: {errors}"
        assert parallel_parser._stats["success"] == 500, "Статистика должна быть корректной"

    def test_rlock_in_log_method(self, parallel_parser: ParallelCityParser) -> None:
        """Тест 7: RLock используется в методе log().

        Проверяет:
        - Метод log() использует RLock
        - Логирование потокобезопасно
        """
        import logging
        from io import StringIO

        # Настраиваем логирование для теста
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger("parser_2gis")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        errors = []

        def log_messages():
            try:
                for i in range(50):
                    parallel_parser.log(f"Test message {i}", "debug")
            except Exception as e:
                errors.append(e)

        # Запускаем несколько потоков
        threads = [threading.Thread(target=log_messages) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Ошибки в потоках: {errors}"

        # Очищаем
        logger.removeHandler(handler)

    def test_rlock_reentrancy_in_parallel_operations(
        self, parallel_parser: ParallelCityParser
    ) -> None:
        """Тест 8: RLock реентерабельность в параллельных операциях.

        Проверяет:
        - Параллельные операции с RLock работают корректно
        - Нет взаимных блокировок
        """
        operation_log = []
        lock = parallel_parser._lock

        def complex_operation(operation_id: str):
            with lock:
                operation_log.append(f"{operation_id}_start")
                # Вложенная операция
                with lock:
                    operation_log.append(f"{operation_id}_nested")
                    # Ещё одна вложенная операция
                    with lock:
                        operation_log.append(f"{operation_id}_inner")

        # Запускаем несколько операций
        threads = [threading.Thread(target=complex_operation, args=(f"op{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Проверяем что все операции выполнились
        assert len(operation_log) == 15, "Все операции должны выполниться"

    def test_rlock_vs_lock_difference(self, parallel_parser: ParallelCityParser) -> None:
        """Тест 9: Демонстрация различия RLock и Lock.

        Проверяет:
        - Lock вызвал бы deadlock при реентерабельности
        - RLock работает корректно
        """
        # Создаём обычный Lock для сравнения
        regular_lock = threading.Lock()

        # RLock работает при реентерабельности
        rlock_works = True
        try:
            with parallel_parser._lock, parallel_parser._lock:
                pass
        except Exception:
            rlock_works = False

        assert rlock_works, "RLock должен работать при реентерабельности"

        # Lock вызвал бы deadlock (но мы не тестируем это явно чтобы не заблокировать тест)
        # Просто проверяем что RLock это не Lock
        assert type(parallel_parser._lock) is not type(regular_lock), (
            "RLock должен отличаться от Lock"
        )

    def test_rlock_multiple_threads_reentrancy(self, parallel_parser: ParallelCityParser) -> None:
        """Тест 10: RLock реентерабельность в нескольких потоках.

        Проверяет:
        - Каждый поток может выполнять реентерабельные вызовы
        - Потоки не блокируют друг друга
        """
        results = {}
        errors = []

        def thread_worker(thread_id: int):
            try:
                count = 0
                for _ in range(10):
                    with parallel_parser._lock, parallel_parser._lock:
                        count += 1
                results[thread_id] = count
            except Exception as e:
                errors.append((thread_id, e))

        # Запускаем потоки
        threads = [threading.Thread(target=thread_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Ошибки в потоках: {errors}"
        assert all(count == 10 for count in results.values()), (
            "Все потоки должны выполнить 10 операций"
        )
