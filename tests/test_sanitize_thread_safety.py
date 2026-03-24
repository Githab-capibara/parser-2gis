"""Тесты для проверки потокобезопасности _sanitize_value."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Импорт функции _sanitize_value из модуля утилит санитизации
from parser_2gis.utils.sanitizers import _sanitize_value


class TestSanitizeValueThreadSafety:
    """Тесты для проверки потокобезопасности _sanitize_value."""

    def test_concurrent_sanitization_no_crash(self):
        """Параллельная санитизация не должна вызывать краш."""
        test_data = {
            "user": {"name": "John", "password": "secret123"},
            "tokens": ["token1", "token2"],
        }

        def sanitize_worker(worker_id):
            try:
                result = _sanitize_value(test_data.copy())
                return (worker_id, "success", result)
            except Exception as e:
                return (worker_id, "error", str(e))

        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(sanitize_worker, i) for i in range(50)]
            for future in as_completed(futures):
                results.append(future.result())

        errors = [r for r in results if r[1] == "error"]
        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_concurrent_calls_isolated(self):
        """Параллельные вызовы должны быть изолированы."""

        def create_test_data(password_value):
            return {"username": "user", "password": password_value}

        results = []

        def worker(password):
            result = _sanitize_value(create_test_data(password))
            results.append((password, result.get("password")))
            return result

        threads = [threading.Thread(target=worker, args=(f"pass{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20
        for orig_pwd, redacted_pwd in results:
            assert redacted_pwd == "<REDACTED>", f"Original: {orig_pwd}, Got: {redacted_pwd}"

    def test_deep_nesting_thread_safety(self):
        """Глубокая вложенность должна работать корректно в многопоточном режиме."""

        def create_nested_dict(depth):
            if depth == 0:
                return {"key": "value", "secret": "hidden"}
            return {f"level_{depth}": create_nested_dict(depth - 1)}

        test_cases = [create_nested_dict(5) for _ in range(5)]

        def worker(data, idx):
            return _sanitize_value(data)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, data, i) for i, data in enumerate(test_cases)]
            results = [f.result() for f in as_completed(futures)]

        assert len(results) == 5

    def test_large_collection_thread_safety(self):
        """Большие коллекции должны обрабатываться корректно."""

        def create_large_dict(size):
            return {f"key_{i}": f"value_{i}" for i in range(size)}

        test_data = create_large_dict(100)

        results = []

        def worker(data):
            return _sanitize_value(data)

        threads = [
            threading.Thread(target=lambda: results.append(worker(test_data))) for _ in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5

    def test_cyclic_reference_thread_safety(self):
        """Циклические ссылки должны обрабатываться корректно."""
        test_data = {"level1": {"level2": {}}}
        test_data["level1"]["level2"]["parent"] = test_data["level1"]

        def worker():
            return _sanitize_value(test_data)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_sensitive_data_not_leaked_between_threads(self):
        """Конфиденциальные данные не должны утекать между потоками."""
        passwords = ["pass1", "pass2", "pass3"]

        def worker(password, results_list):
            data = {"username": "user", "password": password}
            result = _sanitize_value(data)
            results_list.append(result)

        all_results = []

        threads = []
        for pwd in passwords:
            t = threading.Thread(target=worker, args=(pwd, all_results))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(all_results) == 3
        for result in all_results:
            assert result["password"] == "<REDACTED>"
            assert result["username"] == "user"
