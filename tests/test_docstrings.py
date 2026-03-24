"""
Тесты для проверки docstrings.

Проверяет что docstrings присутствуют и корректны:
- tui_screens_have_docstrings: все TUI экраны имеют docstrings
- public_methods_documented: все публичные методы имеют docstrings
"""

import inspect
import sys
from pathlib import Path

import pytest

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTUIScreensHaveDocstrings:
    """Тесты для проверки docstrings в TUI экранах."""

    def test_tui_screens_have_docstrings_main_menu(self):
        """
        Тест 1.1: Проверка docstring в MainMenuScreen.

        Проверяет что класс MainMenuScreen имеет docstring.
        """
        from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen

        # Проверяем что класс имеет docstring
        assert MainMenuScreen.__doc__ is not None
        assert len(MainMenuScreen.__doc__.strip()) > 0

    def test_tui_screens_have_docstrings_parsing(self):
        """
        Тест 1.2: Проверка docstring в ParsingScreen.

        Проверяет что класс ParsingScreen имеет docstring.
        """
        from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen

        # Проверяем что класс имеет docstring
        assert ParsingScreen.__doc__ is not None
        assert len(ParsingScreen.__doc__.strip()) > 0

    def test_tui_screens_have_docstrings_cache_viewer(self):
        """
        Тест 1.3: Проверка docstring в CacheViewerScreen.

        Проверяет что класс CacheViewerScreen имеет docstring.
        """
        from parser_2gis.tui_textual.screens.other_screens import CacheViewerScreen

        # Проверяем что класс имеет docstring
        assert CacheViewerScreen.__doc__ is not None
        assert len(CacheViewerScreen.__doc__.strip()) > 0

    def test_tui_screens_have_docstrings_about(self):
        """
        Тест 1.4: Проверка docstring в AboutScreen.

        Проверяет что класс AboutScreen имеет docstring.
        """
        from parser_2gis.tui_textual.screens.other_screens import AboutScreen

        # Проверяем что класс имеет docstring
        assert AboutScreen.__doc__ is not None
        assert len(AboutScreen.__doc__.strip()) > 0

    def test_tui_screens_have_docstrings_city_selector(self):
        """
        Тест 1.5: Проверка docstring в CitySelectorScreen.

        Проверяет что класс CitySelectorScreen имеет docstring.
        """
        from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen

        # Проверяем что класс имеет docstring
        assert CitySelectorScreen.__doc__ is not None
        assert len(CitySelectorScreen.__doc__.strip()) > 0

    def test_tui_screens_have_docstrings_category_selector(self):
        """
        Тест 1.6: Проверка docstring в CategorySelectorScreen.

        Проверяет что класс CategorySelectorScreen имеет docstring.
        """
        from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen

        # Проверяем что класс имеет docstring
        assert CategorySelectorScreen.__doc__ is not None
        assert len(CategorySelectorScreen.__doc__.strip()) > 0

    def test_tui_screens_have_docstrings_settings(self):
        """
        Тест 1.7: Проверка docstring в экранах настроек.

        Проверяет что классы настроек имеют docstrings.
        """
        from parser_2gis.tui_textual.screens.settings import (
            BrowserSettingsScreen,
            OutputSettingsScreen,
            ParserSettingsScreen,
        )

        # Проверяем что классы имеют docstrings
        assert BrowserSettingsScreen.__doc__ is not None
        assert len(BrowserSettingsScreen.__doc__.strip()) > 0

        assert ParserSettingsScreen.__doc__ is not None
        assert len(ParserSettingsScreen.__doc__.strip()) > 0

        assert OutputSettingsScreen.__doc__ is not None
        assert len(OutputSettingsScreen.__doc__.strip()) > 0

    def test_tui_screens_have_docstrings_app(self):
        """
        Тест 1.8: Проверка docstring в TUIApp.

        Проверяет что класс TUIApp имеет docstring.
        """
        from parser_2gis.tui_textual.app import TUIApp

        # Проверяем что класс имеет docstring
        assert TUIApp.__doc__ is not None
        assert len(TUIApp.__doc__.strip()) > 0


class TestPublicMethodsDocumented:
    """Тесты для проверки docstrings в публичных методах."""

    def test_public_methods_documented_cache_manager(self):
        """
        Тест 2.1: Проверка docstrings в методах CacheManager.

        Проверяет что публичные методы CacheManager имеют docstrings.
        """
        from parser_2gis.cache import CacheManager

        # Получаем публичные методы
        public_methods = [
            name
            for name, method in inspect.getmembers(CacheManager, predicate=inspect.isfunction)
            if not name.startswith("_")
        ]

        # Проверяем что методы имеют docstrings
        for method_name in public_methods:
            method = getattr(CacheManager, method_name)
            assert method.__doc__ is not None, f"Метод {method_name} не имеет docstring"
            assert len(method.__doc__.strip()) > 0, f"Метод {method_name} имеет пустой docstring"

    def test_public_methods_documented_file_logger(self):
        """
        Тест 2.2: Проверка docstrings в методах FileLogger.

        Проверяет что публичные методы FileLogger имеют docstrings.
        """
        from parser_2gis.chrome.file_handler import FileLogger

        # Получаем публичные методы
        public_methods = [
            name
            for name, method in inspect.getmembers(FileLogger, predicate=inspect.isfunction)
            if not name.startswith("_")
        ]

        # Проверяем что методы имеют docstrings
        for method_name in public_methods:
            method = getattr(FileLogger, method_name)
            assert method.__doc__ is not None, f"Метод {method_name} не имеет docstring"
            assert len(method.__doc__.strip()) > 0, f"Метод {method_name} имеет пустой docstring"

    def test_public_methods_documented_chrome_browser(self):
        """
        Тест 2.3: Проверка docstrings в методах ChromeBrowser.

        Проверяет что публичные методы ChromeBrowser имеют docstrings.
        """
        from parser_2gis.chrome.browser import ChromeBrowser

        # Получаем публичные методы
        public_methods = [
            name
            for name, method in inspect.getmembers(ChromeBrowser, predicate=inspect.isfunction)
            if not name.startswith("_")
        ]

        # Проверяем что методы имеют docstrings
        for method_name in public_methods:
            method = getattr(ChromeBrowser, method_name)
            assert method.__doc__ is not None, f"Метод {method_name} не имеет docstring"
            assert len(method.__doc__.strip()) > 0, f"Метод {method_name} имеет пустой docstring"

    def test_public_methods_documented_parallel_parser(self):
        """
        Тест 2.4: Проверка docstrings в методах ParallelCityParser.

        Проверяет что публичные методы ParallelCityParser имеют docstrings.
        """
        from parser_2gis.parallel import ParallelCityParser

        # Получаем публичные методы
        public_methods = [
            name
            for name, method in inspect.getmembers(ParallelCityParser, predicate=inspect.isfunction)
            if not name.startswith("_")
        ]

        # Проверяем что методы имеют docstrings
        for method_name in public_methods:
            method = getattr(ParallelCityParser, method_name)
            assert method.__doc__ is not None, f"Метод {method_name} не имеет docstring"
            assert len(method.__doc__.strip()) > 0, f"Метод {method_name} имеет пустой docstring"

    def test_public_methods_documented_configuration(self):
        """
        Тест 2.5: Проверка docstrings в методах Configuration.

        Проверяет что публичные методы Configuration имеют docstrings.
        """
        from parser_2gis.config import Configuration

        # Получаем публичные методы только определённые в Configuration (не унаследованные)
        public_methods = [
            name
            for name, method in inspect.getmembers(Configuration, predicate=inspect.isfunction)
            if not name.startswith("_") and method.__module__ == "parser_2gis.config"
        ]

        # Проверяем что методы имеют docstrings
        for method_name in public_methods:
            method = getattr(Configuration, method_name)
            assert method.__doc__ is not None, f"Метод {method_name} не имеет docstring"
            assert len(method.__doc__.strip()) > 0, f"Метод {method_name} имеет пустой docstring"


class TestDocstringQuality:
    """Тесты для проверки качества docstrings."""

    def test_docstring_contains_args_section(self):
        """
        Тест 3.1: Проверка наличия секции Args в docstring.

        Проверяет что docstrings методов содержат секцию Args.
        """
        from parser_2gis.cache import CacheManager

        method = CacheManager.get
        docstring = method.__doc__

        # Проверяем что docstring содержит секцию Args или Args:
        assert docstring is not None
        # Проверяем наличие описания аргументов (не строго)
        assert "url" in docstring.lower() or "args" in docstring.lower()

    def test_docstring_contains_returns_section(self):
        """
        Тест 3.2: Проверка наличия секции Returns в docstring.

        Проверяет что docstrings методов содержат секцию Returns.
        """
        from parser_2gis.cache import CacheManager

        method = CacheManager.get
        docstring = method.__doc__

        # Проверяем что docstring содержит секцию Returns
        assert docstring is not None
        # Проверяем наличие описания возвращаемого значения
        assert "return" in docstring.lower() or "returns" in docstring.lower()

    def test_docstring_contains_raises_section(self):
        """
        Тест 3.3: Проверка наличия секции Raises в docstring.

        Проверяет что docstrings методов содержат секцию Raises.
        """
        from parser_2gis.cache import CacheManager

        method = CacheManager.__init__
        docstring = method.__doc__

        # Проверяем что docstring содержит информацию об исключениях
        assert docstring is not None
        # Проверяем наличие описания исключений (не строго)
        assert (
            "raise" in docstring.lower()
            or "error" in docstring.lower()
            or "exception" in docstring.lower()
        )

    def test_docstring_in_russian(self):
        """
        Тест 3.4: Проверка что docstrings на русском языке.

        Проверяет что docstrings написаны на русском языке.
        """
        from parser_2gis.cache import CacheManager

        method = CacheManager.get
        docstring = method.__doc__

        # Проверяем что docstring содержит русские символы
        assert docstring is not None
        # Проверяем наличие русских символов
        has_russian = any(ord(c) > 127 for c in docstring)
        assert has_russian, "Docstring должен быть на русском языке"

    def test_docstring_not_too_short(self):
        """
        Тест 3.5: Проверка что docstrings не слишком короткие.

        Проверяет что docstrings имеют достаточную длину.
        """
        from parser_2gis.cache import CacheManager

        method = CacheManager.get
        docstring = method.__doc__

        # Проверяем что docstring имеет достаточную длину
        assert docstring is not None
        assert len(docstring.strip()) >= 20, "Docstring слишком короткий"

    def test_docstring_not_too_long(self):
        """
        Тест 3.6: Проверка что docstrings не слишком длинные.

        Проверяет что docstrings не превышают разумную длину.
        """
        from parser_2gis.cache import CacheManager

        method = CacheManager.get
        docstring = method.__doc__

        # Проверяем что docstring не слишком длинный
        assert docstring is not None
        # Docstring не должен превышать 2000 символов (разумный предел)
        assert len(docstring) <= 2000, "Docstring слишком длинный"


class TestModuleDocstrings:
    """Тесты для проверки docstrings модулей."""

    def test_module_docstring_cache(self):
        """
        Тест 4.1: Проверка docstring модуля cache.

        Проверяет что модуль cache имеет docstring.
        """
        import parser_2gis.cache as cache_module

        # Проверяем что модуль имеет docstring
        assert cache_module.__doc__ is not None
        assert len(cache_module.__doc__.strip()) > 0

    def test_module_docstring_file_handler(self):
        """
        Тест 4.2: Проверка docstring модуля file_handler.

        Проверяет что модуль file_handler имеет docstring.
        """
        import parser_2gis.chrome.file_handler as file_handler_module

        # Проверяем что модуль имеет docstring
        assert file_handler_module.__doc__ is not None
        assert len(file_handler_module.__doc__.strip()) > 0

    def test_module_docstring_browser(self):
        """
        Тест 4.3: Проверка docstring модуля browser.

        Проверяет что модуль browser имеет docstring.
        """
        import parser_2gis.chrome.browser as browser_module

        # Проверяем что модуль имеет docstring
        assert browser_module.__doc__ is not None
        assert len(browser_module.__doc__.strip()) > 0

    def test_module_docstring_parallel_parser(self):
        """
        Тест 4.4: Проверка docstring модуля parallel_parser.

        Проверяет что модуль parallel_parser имеет docstring.
        """
        import parser_2gis.parallel as parallel_parser_module

        # Проверяем что модуль имеет docstring
        assert parallel_parser_module.__doc__ is not None
        assert len(parallel_parser_module.__doc__.strip()) > 0

    def test_module_docstring_tui_app(self):
        """
        Тест 4.5: Проверка docstring модуля tui_app.

        Проверяет что модуль tui_textual.app имеет docstring.
        """
        import parser_2gis.tui_textual.app as tui_app_module

        # Проверяем что модуль имеет docstring
        assert tui_app_module.__doc__ is not None
        assert len(tui_app_module.__doc__.strip()) > 0


class TestDocstringConsistency:
    """Тесты для проверки согласованности docstrings."""

    def test_docstring_format_consistency(self):
        """
        Тест 5.1: Проверка согласованности формата docstrings.

        Проверяет что docstrings используют согласованный формат.
        """
        from parser_2gis.cache import CacheManager

        methods = [CacheManager.get, CacheManager.set, CacheManager.close]

        for method in methods:
            docstring = method.__doc__
            assert docstring is not None

            # Проверяем что docstring начинается с заглавной буквы
            stripped = docstring.strip()
            assert stripped[0].isupper(), (
                f"Docstring метода {method.__name__} должен начинаться с заглавной буквы"
            )

    def test_docstring_method_signature_match(self):
        """
        Тест 5.2: Проверка что docstring соответствует сигнатуре метода.

        Проверяет что параметры в docstring соответствуют сигнатуре.
        """
        from parser_2gis.cache import CacheManager

        method = CacheManager.get
        docstring = method.__doc__

        # Получаем сигнатуру метода
        sig = inspect.signature(method)
        params = list(sig.parameters.keys())

        # Проверяем что docstring содержит описание параметров
        assert docstring is not None
        # Проверяем что параметры упомянуты в docstring
        for param in params:
            if param != "self":
                assert param in docstring, f"Параметр {param} не упомянут в docstring"


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
