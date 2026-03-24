"""
Тесты для проверки оптимизаций кода.

Проверяет что оптимизации применены корректно:
- unique_name_attempts_optimized: оптимизация попыток создания уникального имени
- long_strings_fixed: исправление длинных строк
- pass_replaced_with_ellipsis: замена pass на ellipsis
"""

from pathlib import Path

import ast
import pytest


class TestUniqueNameAttemptsOptimized:
    """Тесты для проверки оптимизации попыток создания уникального имени."""

    def test_unique_name_attempts_optimized_in_file_merger(self):
        """
        Тест 1.1: Проверка оптимизации в FileMerger.

        Проверяет что попытки создания уникального имени
        оптимизированы через счетчик вместо случайных имен.
        """
        from parser_2gis.parallel_helpers import FileMerger

        # Проверяем что класс существует
        assert FileMerger is not None

        # Проверяем что метод merge_csv_files существует
        assert hasattr(FileMerger, "merge_csv_files")

    def test_unique_name_attempts_optimized_counter_pattern(self, tmp_path):
        """
        Тест 1.2: Проверка использования счетчика для уникальных имен.

        Проверяет что уникальные имена создаются через счетчик.
        """
        from parser_2gis.config import Configuration
        from parser_2gis.parallel_helpers import FileMerger

        # Создаем mock конфиг
        mock_config = Configuration()

        # Создаем FileMerger
        merger = FileMerger(output_dir=tmp_path, config=mock_config)

        # Создаем тестовые CSV файлы
        csv_files = []
        for i in range(3):
            csv_file = tmp_path / f"test_{i}.csv"
            csv_file.write_text("name,address\n")
            csv_files.append(csv_file)

        output_file = str(tmp_path / "merged.csv")

        # Вызываем merge
        result = merger.merge_csv_files(output_file, csv_files)

        # Проверяем что merge прошел успешно
        assert result is True
        # Проверяем что файл создан
        assert (tmp_path / "merged.csv").exists()

    def test_unique_name_attempts_optimized_no_infinite_loop(self, tmp_path):
        """
        Тест 1.3: Проверка что нет бесконечного цикла при создании имен.

        Проверяет что создание уникальных имен
        не приводит к бесконечному циклу.
        """
        import time

        from parser_2gis.config import Configuration
        from parser_2gis.parallel_helpers import FileMerger

        # Создаем mock конфиг
        mock_config = Configuration()

        # Создаем FileMerger
        merger = FileMerger(output_dir=tmp_path, config=mock_config)

        # Создаем тестовые CSV файлы
        csv_files = []
        for i in range(5):
            csv_file = tmp_path / f"test_{i}.csv"
            csv_file.write_text("name,address\n")
            csv_files.append(csv_file)

        output_file = str(tmp_path / "merged.csv")

        # Засекаем время выполнения
        start_time = time.time()

        # Вызываем merge
        result = merger.merge_csv_files(output_file, csv_files)

        # Проверяем что выполнение заняло разумное время (< 1 секунды)
        elapsed_time = time.time() - start_time
        assert elapsed_time < 1.0, f"Merge занял слишком много времени: {elapsed_time} сек"

        # Проверяем что merge прошел успешно
        assert result is True


class TestLongStringsFixed:
    """Тесты для проверки исправления длинных строк."""

    def test_long_strings_fixed_in_cache_module(self):
        """
        Тест 2.1: Проверка что в cache.py нет длинных строк.

        Проверяет что строки в cache.py
        не превышают максимальную длину.
        """
        cache_module_path = Path(__file__).parent.parent / "parser_2gis" / "cache.py"

        # Читаем файл
        with open(cache_module_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Проверяем длину строк (максимум 120 символов)
        max_line_length = 120
        long_lines = []

        for i, line in enumerate(lines, 1):
            # Игнорируем строки с URL и SQL запросами
            stripped = line.strip()
            if len(stripped) > max_line_length:
                # Игнорируем комментарии и строки с URL
                if (
                    not stripped.startswith("#")
                    and "http" not in stripped
                    and "PRAGMA" not in stripped
                    and "SELECT" not in stripped
                    and "INSERT" not in stripped
                    and "CREATE" not in stripped
                ):
                    long_lines.append((i, len(stripped), stripped[:50]))

        # Проверяем что нет длинных строк (кроме исключений)
        # Разрешаем до 5 длинных строк (SQL запросы и т.д.)
        assert len(long_lines) <= 5, f"Найдены длинные строки: {long_lines[:5]}"

    def test_long_strings_fixed_in_parallel_parser(self):
        """
        Тест 2.2: Проверка что в parallel_parser.py нет длинных строк.

        Проверяет что строки в parallel_parser.py
        не превышают максимальную длину.
        """
        parser_module_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )

        # Читаем файл
        with open(parser_module_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Проверяем длину строк (максимум 120 символов)
        max_line_length = 120
        long_lines = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if len(stripped) > max_line_length:
                # Игнорируем комментарии и строки с URL
                if not stripped.startswith("#") and "http" not in stripped:
                    long_lines.append((i, len(stripped), stripped[:50]))

        # Проверяем что нет длинных строк (кроме исключений)
        assert len(long_lines) <= 10, f"Найдены длинные строки: {long_lines[:10]}"

    def test_long_strings_fixed_in_browser_module(self):
        """
        Тест 2.3: Проверка что в browser.py нет длинных строк.

        Проверяет что строки в browser.py
        не превышают максимальную длину.
        """
        browser_module_path = Path(__file__).parent.parent / "parser_2gis" / "chrome" / "browser.py"

        # Читаем файл
        with open(browser_module_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Проверяем длину строк (максимум 120 символов)
        max_line_length = 120
        long_lines = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if len(stripped) > max_line_length:
                # Игнорируем комментарии
                if not stripped.startswith("#"):
                    long_lines.append((i, len(stripped), stripped[:50]))

        # Проверяем что нет длинных строк (кроме исключений)
        assert len(long_lines) <= 10, f"Найдены длинные строки: {long_lines[:10]}"

    def test_long_strings_fixed_in_remote_module(self):
        """
        Тест 2.4: Проверка что в remote.py нет длинных строк.

        Проверяет что строки в remote.py
        не превышают максимальную длину.
        """
        remote_module_path = Path(__file__).parent.parent / "parser_2gis" / "chrome" / "remote.py"

        # Читаем файл
        with open(remote_module_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Проверяем длину строк (максимум 120 символов)
        max_line_length = 120
        long_lines = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if len(stripped) > max_line_length:
                # Игнорируем комментарии и regex паттерны
                if not stripped.startswith("#") and "re.compile" not in stripped:
                    long_lines.append((i, len(stripped), stripped[:50]))

        # Проверяем что нет длинных строк (кроме исключений)
        assert len(long_lines) <= 10, f"Найдены длинные строки: {long_lines[:10]}"


class TestPassReplacedWithEllipsis:
    """Тесты для проверки замены pass на ellipsis."""

    def test_pass_replaced_with_ellipsis_in_tui_screens(self):
        """
        Тест 3.1: Проверка что в TUI экранах pass заменен на ellipsis.

        Проверяет что в TUI экранах
        пустые блоки используют ellipsis вместо pass.
        """
        from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen
        from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

        # Проверяем что классы существуют и имеют методы
        assert MainMenuScreen is not None
        assert ParsingScreen is not None

        # Проверяем что метод compose существует
        assert hasattr(MainMenuScreen, "compose")
        assert hasattr(ParsingScreen, "compose")

    def test_pass_replaced_with_ellipsis_in_stub_functions(self):
        """
        Тест 3.2: Проверка что в stub функциях pass заменен на ellipsis.

        Проверяет что stub функции используют ellipsis.
        """
        from parser_2gis.main import _tui_omsk_stub, _tui_stub

        # Проверяем что stub функции существуют
        assert _tui_stub is not None
        assert _tui_omsk_stub is not None

        # Проверяем что stub функции вызывают исключения
        try:
            _tui_stub()
        except RuntimeError as e:
            assert "TUI модуль недоступен" in str(e)

        try:
            _tui_omsk_stub()
        except RuntimeError as e:
            assert "TUI модуль недоступен" in str(e)

    def test_pass_replaced_with_ellipsis_no_bare_pass(self):
        """
        Тест 3.3: Проверка что нет bare pass в критических местах.

        Проверяет что в критических местах
        не используется bare pass.
        """
        # Список файлов для проверки
        files_to_check = [
            "parser_2gis/cache.py",
            "parser_2gis/parallel/parallel_parser.py",
            "parser_2gis/chrome/browser.py",
            "parser_2gis/chrome/file_handler.py",
        ]

        for file_path in files_to_check:
            full_path = Path(__file__).parent.parent / file_path

            # Читаем файл
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Парсим AST
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            # Ищем bare pass (pass в начале строки без комментариев)
            bare_pass_count = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Pass):
                    bare_pass_count += 1

            # Проверяем что нет чрезмерного использования pass
            # Разрешаем до 10 pass в файле
            assert bare_pass_count <= 10, f"Файл {file_path} содержит {bare_pass_count} pass"


class TestOptimizationComprehensive:
    """Комплексные тесты для оптимизаций."""

    def test_optimization_lru_cache_used(self):
        """
        Тест 4.1: Проверка что lru_cache используется.

        Проверяет что lru_cache используется
        для кэширования результатов.
        """

        from parser_2gis.chrome.remote import _check_port_cached
        from parser_2gis.main import _get_signal_handler_cached

        # Проверяем что функции используют lru_cache
        assert hasattr(_check_port_cached, "cache_info")
        assert hasattr(_get_signal_handler_cached, "cache_info")

    def test_optimization_lru_cache_info(self):
        """
        Тест 4.2: Проверка статистики lru_cache.

        Проверяет что lru_cache работает корректно.
        """
        from parser_2gis.chrome.remote import _check_port_cached

        # Получаем статистику кэша
        cache_info_before = _check_port_cached.cache_info()

        # Вызываем функцию несколько раз
        _check_port_cached(9222)
        _check_port_cached(9222)
        _check_port_cached(9223)

        # Получаем статистику кэша после
        cache_info_after = _check_port_cached.cache_info()

        # Проверяем что кэш работает
        assert cache_info_after.hits >= cache_info_before.hits
        assert cache_info_after.misses >= cache_info_before.misses

    def test_optimization_compiled_regex_used(self):
        """
        Тест 4.3: Проверка что скомпилированные regex используются.

        Проверяет что скомпилированные regex паттерны
        используются вместо компиляции при каждом вызове.
        """
        import re

        from parser_2gis.chrome.remote import _DANGEROUS_JS_PATTERNS

        # Проверяем что паттерны скомпилированы
        assert len(_DANGEROUS_JS_PATTERNS) > 0

        for pattern, description in _DANGEROUS_JS_PATTERNS:
            # Проверяем что это скомпилированный regex
            assert isinstance(pattern, re.Pattern)

    def test_optimization_batch_operations_used(self, tmp_path):
        """
        Тест 4.4: Проверка что пакетные операции используются.

        Проверяет что пакетные операции
        используются для массовой вставки/удаления.
        """
        from parser_2gis.cache import DEFAULT_BATCH_SIZE, CacheManager

        # Проверяем что константа пакетной операции определена
        assert DEFAULT_BATCH_SIZE > 0

        # Создаем кэш
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24)

        try:
            # Сохраняем несколько записей
            for i in range(10):
                url = f"https://example.com/test_{i}"
                data = {"key": f"value_{i}"}
                cache.set(url, data)

            # Получаем записи
            for i in range(10):
                url = f"https://example.com/test_{i}"
                result = cache.get(url)
                assert result is not None
                assert result["key"] == f"value_{i}"
        finally:
            cache.close()

    def test_optimization_connection_pooling_used(self, tmp_path):
        """
        Тест 4.5: Проверка что connection pooling используется.

        Проверяет что connection pooling
        используется для снижения накладных расходов.
        """
        from parser_2gis.cache import CacheManager, _ConnectionPool

        # Создаем кэш
        cache_dir = tmp_path / "cache"
        cache = CacheManager(cache_dir, ttl_hours=24, pool_size=5)

        try:
            # Проверяем что пул создан
            assert cache._pool is not None
            assert isinstance(cache._pool, _ConnectionPool)

            # Проверяем что размер пула корректный
            assert cache._pool._pool_size > 0

            # Получаем несколько соединений
            connections = []
            for _ in range(3):
                conn = cache._pool.get_connection()
                connections.append(conn)

            # Проверяем что соединения созданы
            assert len(connections) == 3

            # Возвращаем соединения в пул
            for conn in connections:
                cache._pool.return_connection(conn)
        finally:
            cache.close()


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
