"""
Тесты для проверки зависимостей и импортов.

Объединённый модуль: проверка импорта основных и опциональных зависимостей,
а также работоспособности TUI компонентов.
"""

import sys
from pathlib import Path

import pytest

# Добавляем проект в path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Проверяем доступность textual
TEXTUAL_AVAILABLE = False
try:
    import textual  # noqa: F401

    TEXTUAL_AVAILABLE = True
except ImportError:
    pass


class TestYamlDependency:
    """Тесты для проверки YAML зависимости."""

    def test_yaml_module_import(self) -> None:
        """Проверка импорта yaml модуля."""
        try:
            import yaml

            assert hasattr(yaml, "safe_load"), "yaml модуль не имеет safe_load"
        except ImportError:
            pytest.fail("PyYAML не установлен. Установите: pip install pyyaml")

    def test_yaml_safe_load_functionality(self) -> None:
        """Проверка работоспособности yaml.safe_load."""
        import yaml

        test_data = """
        config:
            key: value
            number: 42
        """
        result = yaml.safe_load(test_data)
        assert result["config"]["key"] == "value"
        assert result["config"]["number"] == 42


class TestTextualDependency:
    """Тесты для проверки зависимости Textual (объединённые из test_optional_deps_tui.py)."""

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_textual_import_and_version(self) -> None:
        """Проверка импорта textual и минимальной версии."""
        from packaging import version

        assert hasattr(textual, "__version__"), "textual не имеет __version__"
        min_version = version.parse("0.50.0")
        actual_version = version.parse(textual.__version__)
        assert actual_version >= min_version, (
            f"Версия textual ({actual_version}) меньше минимальной ({min_version})"
        )

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_textual_app_class_exists(self) -> None:
        """Проверка наличия класса App в textual."""
        from textual.app import App

        assert App is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_textual_widgets_exist(self) -> None:
        """Проверка наличия основных виджетов в textual."""
        from textual.app import App, ComposeResult  # noqa: F401
        from textual.containers import Container, VerticalScroll  # noqa: F401
        from textual.widgets import Button, Footer, Header, Input, Label, Static

        # Проверяем что все импорты прошли успешно
        assert all(x is not None for x in [App, Button, Footer, Header, Input, Label, Static])


class TestTUIComponents:
    """Тесты для проверки компонентов TUI на Textual."""

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_tui_app_import_and_instantiation(self) -> None:
        """Проверка импорта и создания экземпляра TUI приложения."""
        from parser_2gis.tui_textual import TUIApp

        app = TUIApp()
        assert app is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_parser2gistui_wrapper_import(self) -> None:
        """Проверка импорта обёртки Parser2GISTUI."""
        from parser_2gis.tui_textual import Parser2GISTUI

        assert Parser2GISTUI is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_run_tui_function_exists(self) -> None:
        """Проверка наличия функции run_tui."""
        from parser_2gis.tui_textual import run_tui

        assert callable(run_tui)


class TestTUIScreens:
    """Тесты для проверки экранов TUI."""

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_main_menu_screen_import(self) -> None:
        """Проверка импорта главного меню."""
        from parser_2gis.tui_textual.screens import MainMenuScreen

        assert MainMenuScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_city_selector_screen_import(self) -> None:
        """Проверка импорта экрана выбора городов."""
        from parser_2gis.tui_textual.screens import CitySelectorScreen

        assert CitySelectorScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_category_selector_screen_import(self) -> None:
        """Проверка импорта экрана выбора категорий."""
        from parser_2gis.tui_textual.screens import CategorySelectorScreen

        assert CategorySelectorScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_parsing_screen_import(self) -> None:
        """Проверка импорта экрана парсинга."""
        from parser_2gis.tui_textual.screens import ParsingScreen

        assert ParsingScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_settings_screens_import(self) -> None:
        """Проверка импорта экранов настроек."""
        from parser_2gis.tui_textual.screens import (
            BrowserSettingsScreen,
            OutputSettingsScreen,
            ParserSettingsScreen,
        )

        assert BrowserSettingsScreen is not None
        assert ParserSettingsScreen is not None
        assert OutputSettingsScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_other_screens_import(self) -> None:
        """Проверка импорта дополнительных экранов."""
        from parser_2gis.tui_textual.screens import AboutScreen, CacheViewerScreen

        assert CacheViewerScreen is not None
        assert AboutScreen is not None


class TestCoreImports:
    """Тесты для проверки основных импортов проекта (объединённые)."""

    @pytest.mark.parametrize(
        "import_path, expected_name",
        [
            ("parser_2gis:main", "main"),
            ("parser_2gis.config:Configuration", "Configuration"),
            ("parser_2gis.parallel:ParallelCityParser", "ParallelCityParser"),
            ("parser_2gis.cache:CacheManager", "CacheManager"),
        ],
    )
    def test_core_imports(self, import_path: str, expected_name: str) -> None:
        """Параметризированная проверка основных импортов."""
        module_path, attr_name = import_path.split(":")
        module = __import__(module_path, fromlist=[attr_name])
        obj = getattr(module, attr_name)
        assert obj is not None, f"{expected_name} не должен быть None"
