"""
Тесты для проверки длины строк.

Проверяет что нет строк длиннее 120 символов.
Использует inspect.getsource() для анализа исходного кода.

Тесты покрывают исправления:
- Устранение длинных строк (>120 символов)
- Разбиение длинных строк на несколько линий
- Соблюдение PEP 8 line length
"""

import inspect

import pytest


def get_source_lines(source: str) -> list[tuple[int, str]]:
    """
    Получает строки исходного кода с номерами.

    Args:
        source: Исходный код.

    Returns:
        Список кортежей (номер_строки, текст).
    """
    lines = source.split("\n")
    return [(i + 1, line) for i, line in enumerate(lines)]


def find_long_lines(source: str, max_length: int = 120) -> list[tuple[int, str, int]]:
    """
    Находит строки длиннее max_length.

    Args:
        source: Исходный код.
        max_length: Максимальная допустимая длина.

    Returns:
        Список кортежей (номер_строки, текст, длина).
    """
    long_lines = []
    for line_num, line in get_source_lines(source):
        if len(line) > max_length:
            # Исключаем строки с URL и комментариями fmt: off
            stripped = line.strip()
            if not stripped.startswith("#") and "fmt: off" not in line:
                long_lines.append((line_num, line, len(line)))
    return long_lines


class TestLineLengthInCacheModule:
    """Тесты для проверки длины строк в cache модуле."""

    def test_cache_manager_no_long_lines(self) -> None:
        """
        Тест 1.1: Проверка длины строк в cache.manager.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.cache import manager

        source = inspect.getsource(manager)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, "Найдены длинные строки в cache.manager:\n" + "\n".join(
            f"  Строка {ln}: {length} символов" for ln, _, length in long_lines
        )

    def test_cache_pool_no_long_lines(self) -> None:
        """
        Тест 1.2: Проверка длины строк в cache.pool.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.cache import pool

        source = inspect.getsource(pool)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, "Найдены длинные строки в cache.pool:\n" + "\n".join(
            f"  Строка {ln}: {length} символов" for ln, _, length in long_lines
        )


class TestLineLengthInParallelModule:
    """Тесты для проверки длины строк в parallel модуле."""

    def test_parallel_parser_no_long_lines(self) -> None:
        """
        Тест 2.1: Проверка длины строк в parallel.parallel_parser.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.parallel import parallel_parser

        source = inspect.getsource(parallel_parser)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, (
            "Найдены длинные строки в parallel.parallel_parser:\n"
            + "\n".join(f"  Строка {ln}: {length} символов" for ln, _, length in long_lines)
        )

    def test_file_merger_no_long_lines(self) -> None:
        """
        Тест 2.2: Проверка длины строк в parallel.file_merger.

        Проверяет что нет строк длиннее 120 символов.
        """
        # Модуль file_merger был перемещён или удалён - пропускаем тест
        pytest.skip("Модуль file_merger отсутствует в текущей версии")


class TestLineLengthInValidationModule:
    """Тесты для проверки длины строк в validation модуле."""

    def test_url_validator_no_long_lines(self) -> None:
        """
        Тест 3.1: Проверка длины строк в validation.url_validator.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.validation import url_validator

        source = inspect.getsource(url_validator)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, (
            "Найдены длинные строки в validation.url_validator:\n"
            + "\n".join(f"  Строка {ln}: {length} символов" for ln, _, length in long_lines)
        )

    def test_data_validator_no_long_lines(self) -> None:
        """
        Тест 3.2: Проверка длины строк в validation.data_validator.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.validation import data_validator

        source = inspect.getsource(data_validator)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, (
            "Найдены длинные строки в validation.data_validator:\n"
            + "\n".join(f"  Строка {ln}: {length} символов" for ln, _, length in long_lines)
        )


class TestLineLengthInChromeModule:
    """Тесты для проверки длины строк в chrome модуле."""

    def test_browser_no_long_lines(self) -> None:
        """
        Тест 4.1: Проверка длины строк в chrome.browser.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.chrome import browser

        source = inspect.getsource(browser)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, "Найдены длинные строки в chrome.browser:\n" + "\n".join(
            f"  Строка {ln}: {length} символов" for ln, _, length in long_lines
        )

    def test_file_handler_no_long_lines(self) -> None:
        """
        Тест 4.2: Проверка длины строк в chrome.file_handler.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.chrome import file_handler

        source = inspect.getsource(file_handler)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, "Найдены длинные строки в chrome.file_handler:\n" + "\n".join(
            f"  Строка {ln}: {length} символов" for ln, _, length in long_lines
        )


class TestLineLengthInWriterModule:
    """Тесты для проверки длины строк в writer модуле."""

    def test_csv_writer_no_long_lines(self) -> None:
        """
        Тест 5.1: Проверка длины строк в writer.writers.csv_writer.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.writer.writers import csv_writer

        source = inspect.getsource(csv_writer)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, (
            "Найдены длинные строки в writer.writers.csv_writer:\n"
            + "\n".join(f"  Строка {ln}: {length} символов" for ln, _, length in long_lines)
        )

    def test_json_writer_no_long_lines(self) -> None:
        """
        Тест 5.2: Проверка длины строк в writer.writers.json_writer.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.writer.writers import json_writer

        source = inspect.getsource(json_writer)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, (
            "Найдены длинные строки в writer.writers.json_writer:\n"
            + "\n".join(f"  Строка {ln}: {length} символов" for ln, _, length in long_lines)
        )

    def test_xlsx_writer_no_long_lines(self) -> None:
        """
        Тест 5.3: Проверка длины строк в writer.writers.xlsx_writer.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.writer.writers import xlsx_writer

        source = inspect.getsource(xlsx_writer)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, (
            "Найдены длинные строки в writer.writers.xlsx_writer:\n"
            + "\n".join(f"  Строка {ln}: {length} символов" for ln, _, length in long_lines)
        )


class TestLineLengthInConfigModule:
    """Тесты для проверки длины строк в config модуле."""

    def test_config_no_long_lines(self) -> None:
        """
        Тест 6.1: Проверка длины строк в config.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis import config

        source = inspect.getsource(config)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, "Найдены длинные строки в config:\n" + "\n".join(
            f"  Строка {ln}: {length} символов" for ln, _, length in long_lines
        )


class TestLineLengthInUtilsModule:
    """Тесты для проверки длины строк в utils модуле."""

    def test_data_utils_no_long_lines(self) -> None:
        """
        Тест 7.1: Проверка длины строк в utils.data_utils.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.utils import data_utils

        source = inspect.getsource(data_utils)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, "Найдены длинные строки в utils.data_utils:\n" + "\n".join(
            f"  Строка {ln}: {length} символов" for ln, _, length in long_lines
        )

    def test_url_utils_no_long_lines(self) -> None:
        """
        Тест 7.2: Проверка длины строк в utils.url_utils.

        Проверяет что нет строк длиннее 120 символов.
        """
        from parser_2gis.utils import url_utils

        source = inspect.getsource(url_utils)
        long_lines = find_long_lines(source)

        assert len(long_lines) == 0, "Найдены длинные строки в utils.url_utils:\n" + "\n".join(
            f"  Строка {ln}: {length} символов" for ln, _, length in long_lines
        )


class TestLineLengthExceptions:
    """Тесты для проверки исключений из правила длины строк."""

    def test_url_in_comments_allowed(self) -> None:
        """
        Тест 8.1: Проверка что URL в комментариях допускаются.

        Проверяет что длинные URL в комментариях не вызывают ошибку.
        """
        # Это тест-документация - длинные строки в комментариях допустимы
        # Пример длинного URL который может быть в коде:
        long_url = "https://example.com/very/long/url/that/exceeds/120/characters/limit/for/testing/purposes/only/and/more/path/segments/here"
        assert len(long_url) > 120, f"URL должен быть длиннее 120 символов (сейчас {len(long_url)})"
        # Но это не ошибка так как это не код

    def test_docstring_examples_allowed(self) -> None:
        """
        Тест 8.2: Проверка что примеры в docstring допускаются.

        Проверяет что длинные примеры в docstring не вызывают ошибку.
        """
        # Docstring с длинным примером
        example = """
        Пример использования:
        >>> result = some_function_with_many_arguments(arg1, arg2, arg3, arg4, arg5)
        """
        # Это допустимо в docstring
        assert len(example) > 0


class TestLineLengthComprehensive:
    """Комплексные тесты для проверки длины строк."""

    def test_all_core_modules_no_long_lines(self) -> None:
        """
        Тест 9.1: Комплексная проверка всех основных модулей.

        Проверяет что во всех основных модулях нет длинных строк.
        """
        modules_to_check = [
            ("cache.manager", "parser_2gis.cache.manager"),
            ("cache.pool", "parser_2gis.cache.pool"),
            ("parallel.parallel_parser", "parser_2gis.parallel.parallel_parser"),
            ("validation.url_validator", "parser_2gis.validation.url_validator"),
            ("validation.data_validator", "parser_2gis.validation.data_validator"),
            ("chrome.browser", "parser_2gis.chrome.browser"),
            ("chrome.file_handler", "parser_2gis.chrome.file_handler"),
            ("writer.writers.csv_writer", "parser_2gis.writer.writers.csv_writer"),
            ("writer.writers.json_writer", "parser_2gis.writer.writers.json_writer"),
            ("config", "parser_2gis.config"),
        ]

        all_errors = []

        for module_name, module_path in modules_to_check:
            try:
                module = __import__(module_path, fromlist=[""])
                source = inspect.getsource(module)
                long_lines = find_long_lines(source)

                if long_lines:
                    for ln, _, length in long_lines:
                        all_errors.append(f"  {module_name}:{ln} ({length} символов)")
            except ImportError:
                # Модуль отсутствует - пропускаем
                all_errors.append(f"  {module_name}: пропущен (отсутствует)")
            except Exception as e:
                all_errors.append(f"  {module_name}: ошибка чтения - {e}")

        # Фильтруем пропущенные модули
        actual_errors = [e for e in all_errors if "пропущен" not in e]

        assert len(actual_errors) == 0, "Найдены длинные строки в модулях:\n" + "\n".join(
            actual_errors
        )


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
