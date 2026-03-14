"""
Тесты для новых улучшений парсера.

Тесты проверяют:
- Новые параметры ParserOptions
- AdaptiveLimits (адаптивные лимиты)
- SmartRetryManager (интеллектуальный retry)
- EndOfResultsDetector (детектор окончания)
- ParallelOptimizer (оптимизатор)
- BrowserHealthMonitor (монитор браузера)
"""

from unittest.mock import Mock

import pytest

from parser_2gis.parser.options import ParserOptions
from parser_2gis.parser.adaptive_limits import AdaptiveLimits
from parser_2gis.parser.smart_retry import SmartRetryManager
from parser_2gis.parser.end_of_results import EndOfResultsDetector
from parser_2gis.parallel_optimizer import ParallelOptimizer, ParallelTask
from parser_2gis.chrome.health_monitor import BrowserHealthMonitor


class TestParserOptions:
    """Тесты для новых параметров ParserOptions."""

    def test_default_stop_on_first_404(self):
        """Тест значения по умолчанию для stop_on_first_404."""
        options = ParserOptions()
        assert options.stop_on_first_404 is False

    def test_default_max_consecutive_empty_pages(self):
        """Тест значения по умолчанию для max_consecutive_empty_pages."""
        options = ParserOptions()
        assert options.max_consecutive_empty_pages == 3

    def test_custom_stop_on_first_404_true(self):
        """Тест установки stop_on_first_404 в True."""
        options = ParserOptions(stop_on_first_404=True)
        assert options.stop_on_first_404 is True

    def test_custom_max_consecutive_empty_pages(self):
        """Тест установки max_consecutive_empty_pages."""
        options = ParserOptions(max_consecutive_empty_pages=5)
        assert options.max_consecutive_empty_pages == 5

    def test_invalid_max_consecutive_empty_pages(self):
        """Тест валидации max_consecutive_empty_pages (должен быть >= 1)."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ParserOptions(max_consecutive_empty_pages=0)


class TestAdaptiveLimits:
    """Тесты для AdaptiveLimits."""

    def test_initialization_default(self):
        """Тест инициализации с базовым лимитом по умолчанию."""
        limits = AdaptiveLimits()
        assert limits.get_adaptive_limit() == 3
        assert limits.get_city_size() is None

    def test_initialization_custom_base(self):
        """Тест инициализации с кастомным базовым лимитом."""
        limits = AdaptiveLimits(base_limit=5)
        assert limits.get_adaptive_limit() == 5

    def test_add_records_count(self):
        """Тест добавления количества записей."""
        limits = AdaptiveLimits()
        limits.add_records_count(10)
        limits.add_records_count(15)
        limits.add_records_count(20)

        stats = limits.get_stats()
        assert stats['records_on_first_pages'] == [10, 15, 20]

    def test_determine_small_city(self):
        """Тест определения маленького города (<= 10 записей)."""
        limits = AdaptiveLimits()
        limits.add_records_count(5)
        limits.add_records_count(8)
        limits.add_records_count(7)

        assert limits.get_city_size() == 'small'
        assert limits.get_adaptive_limit() == 2

    def test_determine_medium_city(self):
        """Тест определения среднего города (<= 50 записей)."""
        limits = AdaptiveLimits()
        limits.add_records_count(20)
        limits.add_records_count(30)
        limits.add_records_count(25)

        assert limits.get_city_size() == 'medium'
        assert limits.get_adaptive_limit() == 3

    def test_determine_large_city(self):
        """Тест определения крупного города (<= 200 записей)."""
        limits = AdaptiveLimits()
        limits.add_records_count(100)
        limits.add_records_count(150)
        limits.add_records_count(120)

        assert limits.get_city_size() == 'large'
        assert limits.get_adaptive_limit() == 5

    def test_determine_huge_city(self):
        """Тест определения огромного города (> 200 записей)."""
        limits = AdaptiveLimits()
        limits.add_records_count(300)
        limits.add_records_count(400)
        limits.add_records_count(350)

        assert limits.get_city_size() == 'huge'
        assert limits.get_adaptive_limit() == 7

    def test_get_stats(self):
        """Тест получения статистики."""
        limits = AdaptiveLimits(base_limit=5)
        limits.add_records_count(10)
        limits.add_records_count(20)
        limits.add_records_count(15)  # Третья запись для определения города

        stats = limits.get_stats()
        assert stats['base_limit'] == 5
        assert stats['city_size'] == 'medium'
        assert stats['records_on_first_pages'] == [10, 20, 15]
        assert stats['avg_records'] == 15.0

    def test_reset(self):
        """Тест сброса состояния."""
        limits = AdaptiveLimits()
        limits.add_records_count(10)
        limits.add_records_count(20)

        limits.reset()

        stats = limits.get_stats()
        assert stats['records_on_first_pages'] == []
        assert stats['city_size'] is None
        assert stats['adaptive_limit'] == 3  # Базовый лимит


class TestSmartRetryManager:
    """Тесты для SmartRetryManager."""

    def test_initialization_default(self):
        """Тест инициализации с max_retries по умолчанию."""
        retry = SmartRetryManager()
        assert retry.get_retry_count() == 0
        assert retry.get_total_records() == 0

    def test_initialization_custom_max_retries(self):
        """Тест инициализации с кастомным max_retries."""
        retry = SmartRetryManager(max_retries=5)
        assert retry.get_retry_count() == 0

    def test_should_retry_network_error(self):
        """Тест retry для сетевой ошибки (502, 503, 504)."""
        retry = SmartRetryManager(max_retries=3)

        # 502 ошибка
        assert retry.should_retry('502 Bad Gateway', records_on_page=0) is True

        # 503 ошибка
        assert retry.should_retry('503 Service Unavailable', records_on_page=0) is True

        # 504 ошибка
        assert retry.should_retry('504 Gateway Timeout', records_on_page=0) is True

    def test_should_retry_timeout(self):
        """Тест retry для Timeout ошибки."""
        retry = SmartRetryManager(max_retries=3)
        assert retry.should_retry('TimeoutError', records_on_page=0) is True

    def test_should_retry_404_with_records(self):
        """Тест retry для 404 если были записи."""
        retry = SmartRetryManager(max_retries=3)
        retry.add_records(10)

        assert retry.should_retry('404 Not Found', records_on_page=0) is True

    def test_should_not_retry_404_without_records(self):
        """Тест NO retry для 404 если не было записей."""
        retry = SmartRetryManager(max_retries=3)

        assert retry.should_retry('404 Not Found', records_on_page=0) is False

    def test_should_not_retry_403(self):
        """Тест NO retry для 403 (блокировка)."""
        retry = SmartRetryManager(max_retries=3)

        assert retry.should_retry('403 Forbidden', records_on_page=10) is False

    def test_should_not_retry_after_max_retries(self):
        """Тест NO retry после превышения лимита попыток."""
        retry = SmartRetryManager(max_retries=2)

        # Первая попытка
        assert retry.should_retry('Error', records_on_page=0) is True

        # Вторая попытка
        assert retry.should_retry('Error', records_on_page=0) is True

        # Третья попытка - должно быть False
        assert retry.should_retry('Error', records_on_page=0) is False

    def test_add_records(self):
        """Тест добавления записей."""
        retry = SmartRetryManager()
        retry.add_records(10)
        retry.add_records(20)
        retry.add_records(30)

        assert retry.get_total_records() == 60

    def test_get_stats(self):
        """Тест получения статистики."""
        retry = SmartRetryManager(max_retries=3)
        retry.add_records(50)
        retry.should_retry('Test error', records_on_page=10)

        stats = retry.get_stats()
        assert stats['retry_count'] == 1
        assert stats['max_retries'] == 3
        assert stats['total_records'] == 50
        assert stats['records_on_last_page'] == 10
        assert stats['last_error'] == 'Test error'

    def test_reset(self):
        """Тест сброса состояния."""
        retry = SmartRetryManager()
        retry.add_records(50)
        retry.should_retry('Error', records_on_page=10)

        retry.reset()

        assert retry.get_retry_count() == 0
        assert retry.get_total_records() == 0
        assert retry.get_stats()['last_error'] is None


class TestEndOfResultsDetector:
    """Тесты для EndOfResultsDetector."""

    def test_initialization(self):
        """Тест инициализации детектора."""
        mock_remote = Mock()
        detector = EndOfResultsDetector(mock_remote)

        assert detector is not None
        assert detector._chrome_remote == mock_remote

    def test_is_end_of_results_false(self):
        """Тест определения когда НЕ конец результатов."""
        mock_remote = Mock()
        mock_dom = Mock()
        mock_dom.text = "Организации: Тест 1, Тест 2, Тест 3"
        mock_remote.get_document.return_value = mock_dom

        detector = EndOfResultsDetector(mock_remote)

        result = detector.is_end_of_results()
        assert result is False

    def test_is_end_of_results_true_pattern(self):
        """Тест определения конца по паттерну."""
        mock_remote = Mock()
        mock_dom = Mock()
        mock_dom.text = "Показаны все организации. Больше ничего нет."
        mock_remote.get_document.return_value = mock_dom

        detector = EndOfResultsDetector(mock_remote)

        result = detector.is_end_of_results()
        assert result is True

    def test_has_pagination_true(self):
        """Тест обнаружения пагинации."""
        mock_remote = Mock()
        mock_dom = Mock()
        mock_link = Mock()
        mock_link.local_name = 'a'
        mock_link.attributes = {'href': '/search/test/page/2'}
        mock_dom.search.return_value = [mock_link]
        mock_remote.get_document.return_value = mock_dom

        detector = EndOfResultsDetector(mock_remote)

        result = detector.has_pagination()
        assert result is True

    def test_has_pagination_false(self):
        """Тест отсутствия пагинации."""
        mock_remote = Mock()
        mock_dom = Mock()
        mock_link = Mock()
        mock_link.local_name = 'a'
        mock_link.attributes = {'href': '/search/test'}
        mock_dom.search.return_value = []
        mock_remote.get_document.return_value = mock_dom

        detector = EndOfResultsDetector(mock_remote)

        result = detector.has_pagination()
        assert result is False


class TestParallelTask:
    """Тесты для ParallelTask."""

    def test_initialization_default_priority(self):
        """Тест инициализации с приоритетом по умолчанию."""
        task = ParallelTask(
            url='https://2gis.ru/moscow/search/Тест',
            category_name='Тест',
            city_name='Москва'
        )

        assert task.url == 'https://2gis.ru/moscow/search/Тест'
        assert task.category_name == 'Тест'
        assert task.city_name == 'Москва'
        assert task.priority == 0
        assert task.start_time is None
        assert task.end_time is None

    def test_initialization_custom_priority(self):
        """Тест инициализации с высоким приоритетом."""
        task = ParallelTask(
            url='https://2gis.ru/moscow/search/Тест',
            category_name='Тест',
            city_name='Москва',
            priority=1
        )

        assert task.priority == 1

    def test_start_and_finish(self):
        """Тест отметки начала и завершения."""
        task = ParallelTask(
            url='https://2gis.ru/moscow/search/Тест',
            category_name='Тест',
            city_name='Москва'
        )

        assert task.duration() == 0

        task.start()
        assert task.start_time is not None
        assert task.duration() > 0  # Длительность > 0 после start

        import time
        time.sleep(0.01)  # Небольшая пауза

        task.finish()
        assert task.end_time is not None
        assert task.duration() > 0


class TestParallelOptimizer:
    """Тесты для ParallelOptimizer."""

    def test_initialization_default(self):
        """Тест инициализации с параметрами по умолчанию."""
        optimizer = ParallelOptimizer()

        assert optimizer._max_workers == 3
        assert optimizer._max_memory_mb == 4096

    def test_initialization_custom(self):
        """Тест инициализации с кастомными параметрами."""
        optimizer = ParallelOptimizer(max_workers=5, max_memory_mb=2048)

        assert optimizer._max_workers == 5
        assert optimizer._max_memory_mb == 2048

    def test_add_task_normal_priority(self):
        """Тест добавления задачи с обычным приоритетом."""
        optimizer = ParallelOptimizer()
        optimizer.add_task(
            url='https://2gis.ru/moscow/search/Тест',
            category_name='Тест',
            city_name='Москва',
            priority=0
        )

        stats = optimizer.get_stats()
        assert stats['total_tasks'] == 1

    def test_add_task_high_priority(self):
        """Тест добавления задачи с высоким приоритетом."""
        optimizer = ParallelOptimizer()
        optimizer.add_task(
            url='https://2gis.ru/moscow/search/Тест',
            category_name='Тест',
            city_name='Москва',
            priority=1
        )

        stats = optimizer.get_stats()
        assert stats['total_tasks'] == 1

    def test_get_next_task(self):
        """Тест получения следующей задачи."""
        optimizer = ParallelOptimizer()
        optimizer.add_task(
            url='https://2gis.ru/moscow/search/Тест',
            category_name='Тест',
            city_name='Москва'
        )

        task = optimizer.get_next_task()
        assert task is not None
        assert task.url == 'https://2gis.ru/moscow/search/Тест'
        assert task.start_time is not None

    def test_get_next_task_empty(self):
        """Тест получения задачи из пустой очереди."""
        optimizer = ParallelOptimizer()

        task = optimizer.get_next_task()
        assert task is None

    def test_get_stats(self):
        """Тест получения статистики."""
        optimizer = ParallelOptimizer()
        optimizer.add_task('url1', 'cat1', 'city1')
        optimizer.add_task('url2', 'cat2', 'city2')

        stats = optimizer.get_stats()
        assert stats['total_tasks'] == 2
        assert stats['pending_tasks'] == 2
        assert stats['active_tasks'] == 0
        assert stats['progress'] == 0.0

    def test_reset(self):
        """Тест сброса оптимизатора."""
        optimizer = ParallelOptimizer()
        optimizer.add_task('url1', 'cat1', 'city1')
        optimizer.add_task('url2', 'cat2', 'city2')

        optimizer.reset()

        stats = optimizer.get_stats()
        assert stats['total_tasks'] == 0
        assert stats['pending_tasks'] == 0
        assert stats['active_tasks'] == 0


class TestBrowserHealthMonitor:
    """Тесты для BrowserHealthMonitor."""

    def test_initialization(self):
        """Тест инициализации монитора."""
        mock_browser = Mock()
        monitor = BrowserHealthMonitor(mock_browser, enable_auto_restart=False)

        assert monitor._browser == mock_browser
        assert monitor._enable_auto_restart is False
        assert monitor._critical_errors_count == 0

    def test_record_activity(self):
        """Тест записи активности."""
        mock_browser = Mock()
        monitor = BrowserHealthMonitor(mock_browser)

        time_before = monitor._last_activity_time

        monitor.record_activity()

        assert monitor._last_activity_time >= time_before

    def test_get_critical_errors_count(self):
        """Тест получения количества критических ошибок."""
        mock_browser = Mock()
        monitor = BrowserHealthMonitor(mock_browser)

        assert monitor.get_critical_errors_count() == 0

    def test_reset(self):
        """Тест сброса монитора."""
        mock_browser = Mock()
        monitor = BrowserHealthMonitor(mock_browser)

        monitor.reset()

        assert monitor.get_critical_errors_count() == 0

    def test_enable_auto_restart(self):
        """Тест включения/отключения авто-перезапуска."""
        mock_browser = Mock()
        monitor = BrowserHealthMonitor(mock_browser, enable_auto_restart=False)

        assert monitor._enable_auto_restart is False

        monitor.enable_auto_restart(True)
        assert monitor._enable_auto_restart is True

        monitor.enable_auto_restart(False)
        assert monitor._enable_auto_restart is False
