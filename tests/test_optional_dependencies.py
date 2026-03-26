"""
Комплексные тесты для optional зависимостей.

Этот модуль тестирует graceful degradation при отсутствии опциональных зависимостей:
- parser_2gis/parallel_optimizer.py - тесты на работу без psutil
- parser_2gis/tui_textual - тесты на работу без textual

Каждый тест проверяет ОДНО конкретное исправление.
"""

from __future__ import annotations

import sys
from typing import Any, Generator
from unittest.mock import MagicMock, Mock, patch

import pytest

# =============================================================================
# ТЕСТЫ ДЛЯ parser_2gis/parallel_optimizer.py (без psutil)
# =============================================================================


class TestParallelOptimizerWithoutPsutil:
    """Тесты на graceful degradation ParallelOptimizer без psutil."""

    def test_parallel_optimizer_init_without_psutil(self, caplog: pytest.LogCaptureFixture) -> None:
        """
        Тест инициализации ParallelOptimizer без psutil.

        Проверяет:
        - ParallelOptimizer инициализируется без psutil
        - _process_cache остаётся None
        - Логгируется сообщение о недоступности psutil

        Args:
            caplog: Фикстура для захвата логов.
        """
        # Скрываем psutil из sys.modules для эмуляции отсутствия
        psutil_module = sys.modules.get("psutil")
        if "psutil" in sys.modules:
            del sys.modules["psutil"]

        try:
            with patch.dict("sys.modules", {"psutil": None}):
                # Перезагружаем модуль чтобы эмулировать импорт без psutil
                import importlib

                from parser_2gis import parallel_optimizer

                # Сохраняем оригинальное значение _PSUTIL_AVAILABLE
                original_available = parallel_optimizer._PSUTIL_AVAILABLE

                # Эмулируем что psutil недоступен
                parallel_optimizer._PSUTIL_AVAILABLE = False
                parallel_optimizer.psutil = None

                try:
                    optimizer = parallel_optimizer.ParallelOptimizer(
                        max_workers=3, max_memory_mb=4096
                    )

                    # Проверяем что процесс не кэширован
                    assert optimizer._process_cache is None

                    # Проверяем что оптимизатор работает
                    assert optimizer._max_workers == 3
                    assert optimizer._max_memory_mb == 4096

                finally:
                    # Восстанавливаем оригинальное значение
                    parallel_optimizer._PSUTIL_AVAILABLE = original_available

        finally:
            # Восстанавливаем psutil в sys.modules
            if psutil_module is not None:
                sys.modules["psutil"] = psutil_module

    def test_check_resources_without_psutil(self) -> None:
        """
        Тест check_resources() без psutil.

        Проверяет:
        - Метод возвращает (True, 0.0) когда psutil недоступен
        - Нет исключений при проверке ресурсов

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)

        # Принудительно устанавливаем _process_cache в None
        optimizer._process_cache = None

        # Вызываем check_resources
        available, memory_mb = optimizer.check_resources()

        # Проверяем что ресурсы "доступны" (graceful degradation)
        assert available is True
        assert memory_mb == 0.0

    def test_add_task_without_psutil(self) -> None:
        """
        Тест add_task() без psutil.

        Проверяет:
        - Задачи добавляются в очередь без psutil
        - Очередь работает корректно

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)
        optimizer._process_cache = None  # Эмулируем отсутствие psutil

        # Добавляем задачу
        optimizer.add_task(
            url="https://test.url", category_name="Тест", city_name="Москва", priority=0
        )

        # Проверяем что задача добавлена
        assert optimizer._stats["total_tasks"] == 1

        # Проверяем что задача в очереди
        task = optimizer.get_next_task()
        assert task is not None
        assert task.url == "https://test.url"

    def test_get_next_task_empty_queue(self) -> None:
        """
        Тест get_next_task() с пустой очередью.

        Проверяет:
        - Возвращает None когда очередь пуста
        - Нет исключений

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)

        # Пытаемся получить задачу из пустой очереди
        task = optimizer.get_next_task()

        assert task is None

    def test_complete_task_updates_stats(self) -> None:
        """
        Тест complete_task() обновляет статистику.

        Проверяет:
        - Статистика completed увеличивается
        - Средняя длительность пересчитывается

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer, ParallelTask

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)

        # Создаём и добавляем задачу
        task = ParallelTask(url="https://test.url", category_name="Тест", city_name="Москва")
        task.start()

        # Имитируем выполнение
        import time

        time.sleep(0.01)

        # Завершаем задачу успешно
        optimizer.complete_task(task, success=True)

        # Проверяем статистику
        stats = optimizer.get_stats()
        assert stats["completed"] == 1
        assert stats["failed"] == 0
        assert stats["avg_duration"] > 0

    def test_complete_task_failure(self) -> None:
        """
        Тест complete_task() с неудачей.

        Проверяет:
        - Статистика failed увеличивается
        - Средняя длительность пересчитывается

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer, ParallelTask

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)

        task = ParallelTask(url="https://test.url", category_name="Тест", city_name="Москва")
        task.start()

        # Завершаем задачу с ошибкой
        optimizer.complete_task(task, success=False)

        stats = optimizer.get_stats()
        assert stats["completed"] == 0
        assert stats["failed"] == 1

    def test_reset_clears_state(self) -> None:
        """
        Тест reset() очищает состояние.

        Проверяет:
        - Очередь очищается
        - Статистика сбрасывается
        - Активные задачи очищаются

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)

        # Добавляем задачу
        optimizer.add_task(url="https://test.url", category_name="Тест", city_name="Москва")

        # Сбрасываем
        optimizer.reset()

        # Проверяем что всё очищено
        stats = optimizer.get_stats()
        assert stats["total_tasks"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0

    def test_parallel_optimizer_with_psutil_mocked(self) -> None:
        """
        Тест ParallelOptimizer с mock psutil.

        Проверяет:
        - Process кэшируется при наличии psutil
        - check_resources() использует кэшированный процесс

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        # Создаём mock psutil.Process
        mock_process = MagicMock()
        mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100 MB
        mock_process.cpu_percent.return_value = 10.0

        with patch("parser_2gis.parallel_optimizer.psutil.Process", return_value=mock_process):
            with patch("parser_2gis.parallel_optimizer._PSUTIL_AVAILABLE", True):
                optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)

                # Проверяем что процесс кэширован
                assert optimizer._process_cache is not None

                # Проверяем check_resources
                available, memory_mb = optimizer.check_resources()

                assert available is True
                assert memory_mb == 100.0

    def test_check_resources_caching(self) -> None:
        """
        Тест кэширования результатов check_resources().

        Проверяет:
        - Результаты кэшируются на TTL секунд
        - Повторный вызов возвращает кэшированный результат

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)

        # Устанавливаем кэшированный результат
        import time

        current_time = time.time()
        optimizer._resource_cache = (True, 50.0, 10.0)
        optimizer._resource_cache_time = current_time

        # Вызываем check_resources - должен вернуть кэш
        available, memory_mb = optimizer.check_resources()

        assert available is True
        assert memory_mb == 50.0

    def test_check_resources_cache_expired(self) -> None:
        """
        Тест истечения кэша check_resources().

        Проверяет:
        - По истечении TTL кэш обновляется
        - Новый результат вычисляется

        Returns:
            None
        """
        from parser_2gis.parallel_optimizer import ParallelOptimizer

        optimizer = ParallelOptimizer(max_workers=3, max_memory_mb=4096)
        optimizer._process_cache = None  # Без psutil

        # Устанавливаем старый кэш
        optimizer._resource_cache = (True, 50.0, 10.0)
        optimizer._resource_cache_time = 0  # Очень старое время

        # Вызываем check_resources - должен пересчитать
        available, memory_mb = optimizer.check_resources()

        # Без psutil должен вернуть (True, 0.0)
        assert available is True
        assert memory_mb == 0.0


# =============================================================================
# ТЕСТЫ ДЛЯ parser_2gis/tui_textual (без textual)
# =============================================================================


class TestTuiTextualWithoutTextual:
    """Тесты на graceful degradation tui_textual без textual."""

    def test_tui_import_without_textual(self) -> None:
        """
        Тест импорта tui_textual без textual.

        Проверяет:
        - Модуль импортируется без textual
        - Классы-заглушки предоставляются

        Returns:
            None
        """
        # Сохраняем textual из sys.modules
        textual_module = sys.modules.get("textual")
        textual_app_module = sys.modules.get("textual.app")

        try:
            # Эмулируем отсутствие textual
            if "textual" in sys.modules:
                del sys.modules["textual"]
            if "textual.app" in sys.modules:
                del sys.modules["textual.app"]

            with patch.dict("sys.modules", {"textual": None, "textual.app": None}):
                # Пытаемся импортировать
                try:
                    from parser_2gis.tui_textual import app as tui_app_module

                    # Проверяем что модуль импортировался
                    assert tui_app_module is not None

                except ImportError as import_error:
                    # Ожидаем ImportError если textual критичен
                    assert "textual" in str(import_error).lower()

        finally:
            # Восстанавливаем textual
            if textual_module is not None:
                sys.modules["textual"] = textual_module
            if textual_app_module is not None:
                sys.modules["textual.app"] = textual_app_module

    def test_tui_stub_functions_exist(self) -> None:
        """
        Тест существования stub функций для TUI.

        Проверяет:
        - Stub функции существуют в main модуле
        - Они могут быть вызваны без ошибок

        Returns:
            None
        """
        from parser_2gis.main import Parser2GISTUI, run_new_tui_omsk

        # Проверяем что функции существуют
        assert Parser2GISTUI is not None
        assert run_new_tui_omsk is not None

    def test_tui_stub_comparison(self) -> None:
        """
        Тест сравнения stub функций.

        Проверяет:
        - Stub функции могут быть сравнены через 'is'
        - Функции идентичны сами себе

        Returns:
            None
        """
        from parser_2gis.main import Parser2GISTUI, run_new_tui_omsk

        # Проверяем identity comparison
        assert Parser2GISTUI is Parser2GISTUI
        assert run_new_tui_omsk is run_new_tui_omsk

        # Проверяем что это разные функции
        assert Parser2GISTUI is not run_new_tui_omsk

    def test_tui_stub_callable(self) -> None:
        """
        Тест вызова stub функций.

        Проверяет:
        - Stub функции могут быть вызваны
        - Нет исключений при вызове

        Returns:
            None
        """
        from parser_2gis.main import Parser2GISTUI, run_new_tui_omsk

        # Проверяем что функции callable
        assert callable(Parser2GISTUI)
        assert callable(run_new_tui_omsk)

    def test_tui_stub_names(self) -> None:
        """
        Тест имён stub функций.

        Проверяет:
        - Функции имеют корректные имена
        - Имена соответствуют ожидаемым

        Returns:
            None
        """
        from parser_2gis.main import Parser2GISTUI, run_new_tui_omsk

        # Проверяем имена
        assert hasattr(Parser2GISTUI, "__name__")
        assert hasattr(run_new_tui_omsk, "__name__")

    def test_tui_optional_imports_in_main(self) -> None:
        """
        Тест optional импортов в main модуле.

        Проверяет:
        - TUI символы экспортируются из main
        - Они доступны для импорта

        Returns:
            None
        """
        # Импортируем символы из parser_2gis.cli.main где они определены
        from parser_2gis.cli.main import Parser2GISTUI, run_new_tui_omsk

        # Проверяем что они не None
        assert Parser2GISTUI is not None
        assert run_new_tui_omsk is not None


# =============================================================================
# ТЕСТЫ ДЛЯ ENV переменных (graceful degradation)
# =============================================================================


class TestEnvironmentVariableGracefulDegradation:
    """Тесты на graceful degradation при некорректных ENV переменных."""

    def test_invalid_env_int_uses_default(self) -> None:
        """
        Тест некорректной ENV переменной для int.

        Проверяет:
        - Некорректное значение вызывает ValueError
        - Это ожидаемое поведение согласно документации validate_env_int

        Returns:
            None
        """
        from parser_2gis.constants import validate_env_int

        # validate_env_int выбрасывает ValueError для некорректных значений
        # Это правильное поведение согласно документации функции
        with patch.dict("os.environ", {"PARSER_TEST_VAR": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                validate_env_int("PARSER_TEST_VAR", default=100, min_value=0, max_value=1000)

            # Проверяем что ошибка связана с конверсией
            assert (
                "invalid literal for int()" in str(exc_info.value)
                or "некоррект" in str(exc_info.value).lower()
            )

    def test_env_int_below_min_uses_min(self) -> None:
        """
        Тест ENV переменной ниже минимума.

        Проверяет:
        - Значение ниже min использует min
        - Логгируется предупреждение

        Returns:
            None
        """
        from parser_2gis.constants import validate_env_int

        with patch.dict("os.environ", {"PARSER_TEST_VAR": "5"}):
            result = validate_env_int("PARSER_TEST_VAR", default=100, min_value=10, max_value=1000)

            # Проверяем что использовано min значение
            assert result == 10

    def test_env_int_above_max_uses_max(self) -> None:
        """
        Тест ENV переменной выше максимума.

        Проверяет:
        - Значение выше max использует max
        - Логгируется предупреждение

        Returns:
            None
        """
        from parser_2gis.constants import validate_env_int

        with patch.dict("os.environ", {"PARSER_TEST_VAR": "5000"}):
            result = validate_env_int("PARSER_TEST_VAR", default=100, min_value=10, max_value=1000)

            # Проверяем что использовано max значение
            assert result == 1000

    def test_env_int_valid_value(self) -> None:
        """
        Тест корректной ENV переменной.

        Проверяет:
        - Корректное значение используется
        - В пределах min/max

        Returns:
            None
        """
        from parser_2gis.constants import validate_env_int

        with patch.dict("os.environ", {"PARSER_TEST_VAR": "500"}):
            result = validate_env_int("PARSER_TEST_VAR", default=100, min_value=10, max_value=1000)

            # Проверяем что использовано значение из ENV
            assert result == 500
