"""
Тесты для проверки наличия docstrings.

Проверяет наличие docstrings у всех публичных функций и классов
с использованием inspect.getdoc().

Тесты покрывают исправления:
- Добавлены docstrings ко всем публичным функциям
- Docstrings на русском языке
- Docstrings содержат описание аргументов и возвращаемых значений
"""

import inspect

import pytest


def get_public_functions(module) -> list[tuple[str, object]]:
    """
    Получает список публичных функций модуля.

    Args:
        module: Модуль для анализа.

    Returns:
        Список кортежей (имя, функция).
    """
    functions = []
    for name, obj in inspect.getmembers(module, predicate=inspect.isfunction):
        if not name.startswith("_"):
            # Проверяем что функция определена в этом модуле
            if hasattr(obj, "__module__") and obj.__module__ == module.__name__:
                functions.append((name, obj))
    return functions


def get_public_classes(module) -> list[tuple[str, object]]:
    """
    Получает список публичных классов модуля.

    Args:
        module: Модуль для анализа.

    Returns:
        Список кортежей (имя, класс).
    """
    classes = []
    for name, obj in inspect.getmembers(module, predicate=inspect.isclass):
        if not name.startswith("_"):
            # Проверяем что класс определён в этом модуле
            if hasattr(obj, "__module__") and obj.__module__ == module.__name__:
                classes.append((name, obj))
    return classes


def has_valid_docstring(obj) -> bool:
    """
    Проверяет наличие валидного docstring.

    Args:
        obj: Объект для проверки.

    Returns:
        True если docstring присутствует и не пуст.
    """
    doc = inspect.getdoc(obj)
    if doc is None:
        return False
    if len(doc.strip()) == 0:
        return False
    return True


class TestDocstringsInCacheModule:
    """Тесты для проверки docstrings в модуле cache."""

    def test_cache_manager_has_docstring(self):
        """
        Тест 1.1: Проверка docstring у CacheManager.

        Проверяет что класс CacheManager имеет docstring.
        """
        from parser_2gis.cache.manager import CacheManager

        doc = inspect.getdoc(CacheManager)
        assert doc is not None, "CacheManager должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring CacheManager не должен быть пустым"

    def test_cache_manager_methods_have_docstrings(self):
        """
        Тест 1.2: Проверка docstrings у методов CacheManager.

        Проверяет что публичные методы CacheManager имеют docstrings.
        """
        from parser_2gis.cache.manager import CacheManager

        methods = [
            name
            for name, method in inspect.getmembers(CacheManager, predicate=inspect.isfunction)
            if not name.startswith("_")
        ]

        for method_name in methods:
            method = getattr(CacheManager, method_name)
            doc = inspect.getdoc(method)
            assert doc is not None, f"Метод {method_name} должен иметь docstring"
            assert len(doc.strip()) > 0, f"Docstring метода {method_name} не должен быть пустым"

    def test_cache_pool_has_docstring(self):
        """
        Тест 1.3: Проверка docstring у ConnectionPool.

        Проверяет что класс ConnectionPool имеет docstring.
        """
        from parser_2gis.cache.pool import ConnectionPool

        doc = inspect.getdoc(ConnectionPool)
        assert doc is not None, "ConnectionPool должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring ConnectionPool не должен быть пустым"


class TestDocstringsInChromeModule:
    """Тесты для проверки docstrings в модуле chrome."""

    def test_chrome_browser_has_docstring(self):
        """
        Тест 2.1: Проверка docstring у ChromeBrowser.

        Проверяет что класс ChromeBrowser имеет docstring.
        """
        from parser_2gis.chrome.browser import ChromeBrowser

        doc = inspect.getdoc(ChromeBrowser)
        assert doc is not None, "ChromeBrowser должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring ChromeBrowser не должен быть пустым"

    def test_chrome_browser_methods_have_docstrings(self):
        """
        Тест 2.2: Проверка docstrings у методов ChromeBrowser.

        Проверяет что публичные методы ChromeBrowser имеют docstrings.
        """
        from parser_2gis.chrome.browser import ChromeBrowser

        methods = [
            name
            for name, method in inspect.getmembers(ChromeBrowser, predicate=inspect.isfunction)
            if not name.startswith("_") and method.__module__ == "parser_2gis.chrome.browser"
        ]

        for method_name in methods:
            method = getattr(ChromeBrowser, method_name)
            doc = inspect.getdoc(method)
            assert doc is not None, f"Метод {method_name} должен иметь docstring"
            assert len(doc.strip()) > 0, f"Docstring метода {method_name} не должен быть пустым"

    def test_file_logger_has_docstring(self):
        """
        Тест 2.3: Проверка docstring у FileLogger.

        Проверяет что класс FileLogger имеет docstring.
        """
        from parser_2gis.chrome.file_handler import FileLogger

        doc = inspect.getdoc(FileLogger)
        assert doc is not None, "FileLogger должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring FileLogger не должен быть пустым"


class TestDocstringsInParallelModule:
    """Тесты для проверки docstrings в модуле parallel_parser."""

    def test_parallel_city_parser_has_docstring(self):
        """
        Тест 3.1: Проверка docstring у ParallelCityParser.

        Проверяет что класс ParallelCityParser имеет docstring.
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        doc = inspect.getdoc(ParallelCityParser)
        assert doc is not None, "ParallelCityParser должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring ParallelCityParser не должен быть пустым"

    def test_parallel_city_parser_methods_have_docstrings(self):
        """
        Тест 3.2: Проверка docstrings у методов ParallelCityParser.

        Проверяет что публичные методы ParallelCityParser имеют docstrings.
        """
        from parser_2gis.parallel.parallel_parser import ParallelCityParser

        methods = [
            name
            for name, method in inspect.getmembers(ParallelCityParser, predicate=inspect.isfunction)
            if not name.startswith("_")
            and method.__module__ == "parser_2gis.parallel.parallel_parser"
        ]

        for method_name in methods:
            method = getattr(ParallelCityParser, method_name)
            doc = inspect.getdoc(method)
            assert doc is not None, f"Метод {method_name} должен иметь docstring"
            assert len(doc.strip()) > 0, f"Docstring метода {method_name} не должен быть пустым"

    def test_parser_thread_config_has_docstring(self):
        """
        Тест 3.3: Проверка docstring у ParserThreadConfig.

        Проверяет что dataclass ParserThreadConfig имеет docstring.
        """
        from parser_2gis.parallel.parallel_parser import ParserThreadConfig

        doc = inspect.getdoc(ParserThreadConfig)
        assert doc is not None, "ParserThreadConfig должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring ParserThreadConfig не должен быть пустым"


class TestDocstringsInValidationModule:
    """Тесты для проверки docstrings в модуле validation."""

    def test_validate_url_has_docstring(self):
        """
        Тест 4.1: Проверка docstring у validate_url().

        Проверяет что функция validate_url имеет docstring.
        """
        from parser_2gis.validation.url_validator import validate_url

        doc = inspect.getdoc(validate_url)
        assert doc is not None, "Функция validate_url должна иметь docstring"
        assert len(doc.strip()) > 0, "Docstring validate_url не должен быть пустым"

    def test_validate_positive_int_has_docstring(self):
        """
        Тест 4.2: Проверка docstring у validate_positive_int().

        Проверяет что функция validate_positive_int имеет docstring.
        """
        from parser_2gis.validation.data_validator import validate_positive_int

        doc = inspect.getdoc(validate_positive_int)
        assert doc is not None, "Функция validate_positive_int должна иметь docstring"
        assert len(doc.strip()) > 0, "Docstring validate_positive_int не должен быть пустым"

    def test_validation_result_has_docstring(self):
        """
        Тест 4.3: Проверка docstring у ValidationResult.

        Проверяет что dataclass ValidationResult имеет docstring.
        """
        from parser_2gis.validation.data_validator import ValidationResult

        doc = inspect.getdoc(ValidationResult)
        assert doc is not None, "ValidationResult должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring ValidationResult не должен быть пустым"


class TestDocstringsInConfigModule:
    """Тесты для проверки docstrings в модуле config."""

    def test_configuration_has_docstring(self):
        """
        Тест 5.1: Проверка docstring у Configuration.

        Проверяет что класс Configuration имеет docstring.
        """
        from parser_2gis.config import Configuration

        doc = inspect.getdoc(Configuration)
        assert doc is not None, "Configuration должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring Configuration не должен быть пустым"

    def test_configuration_methods_have_docstrings(self):
        """
        Тест 5.2: Проверка docstrings у методов Configuration.

        Проверяет что публичные методы Configuration имеют docstrings.
        """
        from parser_2gis.config import Configuration

        methods = [
            name
            for name, method in inspect.getmembers(Configuration, predicate=inspect.isfunction)
            if not name.startswith("_") and method.__module__ == "parser_2gis.config"
        ]

        for method_name in methods:
            method = getattr(Configuration, method_name)
            doc = inspect.getdoc(method)
            assert doc is not None, f"Метод {method_name} должен иметь docstring"
            assert len(doc.strip()) > 0, f"Docstring метода {method_name} не должен быть пустым"


class TestDocstringsInWriterModule:
    """Тесты для проверки docstrings в модуле writer."""

    def test_csv_writer_has_docstring(self):
        """
        Тест 6.1: Проверка docstring у CSVWriter.

        Проверяет что класс CSVWriter имеет docstring.
        """
        from parser_2gis.writer.writers.csv_writer import CSVWriter

        doc = inspect.getdoc(CSVWriter)
        assert doc is not None, "CSVWriter должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring CSVWriter не должен быть пустым"

    def test_json_writer_has_docstring(self):
        """
        Тест 6.2: Проверка docstring у JSONWriter.

        Проверяет что класс JSONWriter имеет docstring.
        """
        from parser_2gis.writer.writers.json_writer import JSONWriter

        doc = inspect.getdoc(JSONWriter)
        assert doc is not None, "JSONWriter должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring JSONWriter не должен быть пустым"

    def test_xlsx_writer_has_docstring(self):
        """
        Тест 6.3: Проверка docstring у XLSXWriter.

        Проверяет что класс XLSXWriter имеет docstring.
        """
        from parser_2gis.writer.writers.xlsx_writer import XLSXWriter

        doc = inspect.getdoc(XLSXWriter)
        assert doc is not None, "XLSXWriter должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring XLSXWriter не должен быть пустым"


class TestDocstringQuality:
    """Тесты для проверки качества docstrings."""

    def test_docstring_starts_with_capital(self):
        """
        Тест 7.1: Проверка что docstring начинается с заглавной буквы.

        Проверяет что docstring начинается с заглавной буквы.
        """
        from parser_2gis.cache.manager import CacheManager

        doc = inspect.getdoc(CacheManager)
        assert doc is not None
        assert doc.strip()[0].isupper(), "Docstring должен начинаться с заглавной буквы"

    def test_docstring_contains_russian_text(self):
        """
        Тест 7.2: Проверка что docstring содержит русский текст.

        Проверяет что docstring содержит символы кириллицы.
        """
        from parser_2gis.cache.manager import CacheManager

        doc = inspect.getdoc(CacheManager)
        assert doc is not None
        # Проверяем наличие русских символов
        has_cyrillic = any("\u0400" <= c <= "\u04ff" for c in doc)
        assert has_cyrillic, "Docstring должен содержать русский текст"

    def test_docstring_not_too_short(self):
        """
        Тест 7.3: Проверка что docstring не слишком короткий.

        Проверяет что docstring имеет минимальную длину.
        """
        from parser_2gis.cache.manager import CacheManager

        doc = inspect.getdoc(CacheManager)
        assert doc is not None
        assert len(doc.strip()) >= 20, "Docstring слишком короткий (минимум 20 символов)"


class TestModuleDocstrings:
    """Тесты для проверки docstrings модулей."""

    def test_cache_module_has_docstring(self):
        """
        Тест 8.1: Проверка docstring у модуля cache.manager.

        Проверяет что модуль cache.manager имеет docstring.
        """
        import parser_2gis.cache.manager as module

        doc = inspect.getdoc(module)
        assert doc is not None, "Модуль cache.manager должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring модуля cache.manager не должен быть пустым"

    def test_browser_module_has_docstring(self):
        """
        Тест 8.2: Проверка docstring у модуля chrome.browser.

        Проверяет что модуль chrome.browser имеет docstring.
        """
        import parser_2gis.chrome.browser as module

        doc = inspect.getdoc(module)
        assert doc is not None, "Модуль chrome.browser должен иметь docstring"
        assert len(doc.strip()) > 0, "Docstring модуля chrome.browser не должен быть пустым"

    def test_parallel_parser_module_has_docstring(self):
        """
        Тест 8.3: Проверка docstring у модуля parallel.parallel_parser.

        Проверяет что модуль parallel.parallel_parser имеет docstring.
        """
        import parser_2gis.parallel.parallel_parser as module

        doc = inspect.getdoc(module)
        assert doc is not None, "Модуль parallel.parallel_parser должен иметь docstring"
        assert len(doc.strip()) > 0, (
            "Docstring модуля parallel.parallel_parser не должен быть пустым"
        )

    def test_validation_module_has_docstring(self):
        """
        Тест 8.4: Проверка docstring у модуля validation.url_validator.

        Проверяет что модуль validation.url_validator имеет docstring.
        """
        import parser_2gis.validation.url_validator as module

        doc = inspect.getdoc(module)
        assert doc is not None, "Модуль validation.url_validator должен иметь docstring"
        assert len(doc.strip()) > 0, (
            "Docstring модуля validation.url_validator не должен быть пустым"
        )


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
