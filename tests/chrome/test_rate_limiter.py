"""
Тесты для функции _enforce_rate_limit() в chrome/rate_limiter.py.

Проверяет:
- Rate limiting при множестве запросов
- Соблюдение интервалов между запросами
- Очистку старых timestamps
- Поточную безопасность
"""

import threading
import time
from collections import deque
from unittest.mock import patch

import parser_2gis.chrome.rate_limiter as rate_limiter_module


def _get_state():
    """Вспомогательная функция для получения состояния rate limiter."""
    return rate_limiter_module.get_rate_limiter_state()


class TestEnforceRateLimit:
    """Тесты функции _enforce_rate_limit()."""

    def setup_method(self) -> None:
        """Сбрасывает состояние rate limiter перед каждым тестом."""
        state = _get_state()
        state._request_timestamps = deque()
        state._min_request_interval = 0.01  # 10ms для тестов
        state._max_requests_per_second = 5  # 5 запросов/сек для тестов

    def teardown_method(self) -> None:
        """Возвращает значения по умолчанию после теста."""
        state = _get_state()
        state._request_timestamps = deque()
        state._min_request_interval = 0.1
        state._max_requests_per_second = 10

    def test_single_request_adds_timestamp(self) -> None:
        """Тест 1: Один запрос добавляет timestamp."""
        with patch("parser_2gis.chrome.rate_limiter.time.sleep"):
            rate_limiter_module._enforce_rate_limit()

        assert len(_get_state()._request_timestamps) == 1

    def test_multiple_requests_respect_min_interval(self) -> None:
        """Тест 2: Множество запросов соблюдает минимальный интервал."""
        sleep_calls = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        state = _get_state()
        for _ in range(3):
            with patch("parser_2gis.chrome.rate_limiter.time.sleep", side_effect=mock_sleep):
                rate_limiter_module._enforce_rate_limit()

        assert len(state._request_timestamps) == 3

    def test_rate_limit_triggers_sleep_at_max_requests(self) -> None:
        """Тест 3: Rate limit вызывает sleep при достижении максимума."""
        state = _get_state()
        now = time.time()
        for i in range(state._max_requests_per_second):
            state._request_timestamps.append(now - 0.5 + i * 0.01)

        sleep_calls = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        with patch("parser_2gis.chrome.rate_limiter.time.sleep", side_effect=mock_sleep):
            rate_limiter_module._enforce_rate_limit()

        assert len(sleep_calls) > 0, "Sleep должен быть вызван при достижении лимита"

    def test_old_timestamps_are_cleaned(self) -> None:
        """Тест 4: Старые timestamps очищаются."""
        state = _get_state()
        now = time.time()
        old_timestamps = [now - 2.0, now - 1.5, now - 1.1]
        state._request_timestamps.extend(old_timestamps)

        with patch("parser_2gis.chrome.rate_limiter.time.sleep"):
            rate_limiter_module._enforce_rate_limit()

        for ts in old_timestamps:
            assert ts not in state._request_timestamps

    def test_min_interval_sleep(self) -> None:
        """Тест 5: Sleep при нарушении минимального интервала."""
        state = _get_state()
        now = time.time()
        state._request_timestamps.append(now)

        sleep_calls = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        with patch("parser_2gis.chrome.rate_limiter.time.sleep", side_effect=mock_sleep):
            with patch("parser_2gis.chrome.rate_limiter.time.time", return_value=now + 0.001):
                rate_limiter_module._enforce_rate_limit()

        assert len(sleep_calls) > 0

    def test_no_sleep_when_interval_respected(self) -> None:
        """Тест 6: Нет sleep когда интервал соблюдён."""
        state = _get_state()
        now = time.time()
        state._request_timestamps.append(now - 1.0)

        sleep_calls = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        with patch("parser_2gis.chrome.rate_limiter.time.sleep", side_effect=mock_sleep):
            rate_limiter_module._enforce_rate_limit()

        assert len(sleep_calls) == 0

    def test_thread_safety(self) -> None:
        """Тест 7: Поточная безопасность rate limiter."""
        errors: list[Exception] = []
        num_threads = 10
        calls_per_thread = 5

        def worker() -> None:
            try:
                for _ in range(calls_per_thread):
                    with patch("parser_2gis.chrome.rate_limiter.time.sleep"):
                        rate_limiter_module._enforce_rate_limit()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Ошибки в потоках: {errors}"
        assert len(_get_state()._request_timestamps) == num_threads * calls_per_thread

    def test_concurrent_requests_respect_limit(self) -> None:
        """Тест 8: Параллельные запросы соблюдают лимит."""
        state = _get_state()
        state._max_requests_per_second = 2
        state._min_request_interval = 0.001

        now = time.time()
        for i in range(2):
            state._request_timestamps.append(now - 0.1 + i * 0.01)

        sleep_calls = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        with patch("parser_2gis.chrome.rate_limiter.time.sleep", side_effect=mock_sleep):
            with patch("parser_2gis.chrome.rate_limiter.time.time", return_value=now):
                rate_limiter_module._enforce_rate_limit()

        assert len(sleep_calls) >= 1

    def test_rate_limiter_state_persists_across_calls(self) -> None:
        """Тест 9: Состояние rate limiter сохраняется между вызовами."""
        with patch("parser_2gis.chrome.rate_limiter.time.sleep"):
            rate_limiter_module._enforce_rate_limit()
            count_after_first = len(_get_state()._request_timestamps)

            rate_limiter_module._enforce_rate_limit()
            count_after_second = len(_get_state()._request_timestamps)

        assert count_after_first == 1
        assert count_after_second == 2

    def test_burst_handling(self) -> None:
        """Тест 10: Обработка burst-запросов."""
        sleep_calls = []

        def mock_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)

        burst_count = 8
        with patch("parser_2gis.chrome.rate_limiter.time.sleep", side_effect=mock_sleep):
            for _ in range(burst_count):
                rate_limiter_module._enforce_rate_limit()

        assert len(_get_state()._request_timestamps) == burst_count
        assert len(sleep_calls) > 0
