"""
Тесты для проверки зависимостей и импортов.

Эти тесты выявляют ошибки на раннем этапе:
- Отсутствие необходимых зависимостей
- Ошибки импорта модулей
- Проблемы с инициализацией TUI компонентов

Примечание:
    Тесты для TUI компонентов требуют установки textual:
    pip install textual

    Если textual не установлен, тесты будут пропущены.
"""

import pytest
import sys
from pathlib import Path

# Добавляем проект в path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Проверяем доступность textual
TEXTUAL_AVAILABLE = False
try:
    import textual

    TEXTUAL_AVAILABLE = True
except ImportError:
    pass


class TestYamlDependency:
    """Тесты для проверки YAML зависимости."""

    def test_yaml_module_import(self):
        """Проверка импорта yaml модуля."""
        try:
            import yaml

            assert hasattr(yaml, "safe_load"), "yaml модуль не имеет safe_load"
        except ImportError:
            pytest.fail("PyYAML не установлен. Установите: pip install pyyaml")

    def test_yaml_safe_load_functionality(self):
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
    """Тесты для проверки зависимости Textual."""

    @pytest.mark.skipif(
        not TEXTUAL_AVAILABLE,
        reason="textual не установлен. Установите: pip install textual",
    )
    def test_textual_import(self):
        """Проверка импорта textual."""
        import textual

        assert hasattr(textual, "__version__"), "textual не имеет __version__"

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_textual_app_class_exists(self):
        """Проверка наличия класса App в textual."""
        from textual.app import App

        assert App is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_textual_widgets_exist(self):
        """Проверка наличия виджетов в textual."""
        from textual.widgets import Button, Input, Label, Static

        assert Button is not None
        assert Input is not None
        assert Label is not None
        assert Static is not None


class TestTUIComponents:
    """Тесты для проверки компонентов TUI на Textual."""

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_tui_app_import(self):
        """Проверка импорта TUI приложения."""
        from parser_2gis.tui_textual import TUIApp

        assert TUIApp is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_tui_app_instantiation(self):
        """Проверка создания экземпляра TUI приложения."""
        from parser_2gis.tui_textual import TUIApp

        app = TUIApp()
        assert app is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_parser2gistui_wrapper_import(self):
        """Проверка импорта обёртки Parser2GISTUI."""
        from parser_2gis.tui_textual import Parser2GISTUI

        assert Parser2GISTUI is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_run_tui_function_exists(self):
        """Проверка наличия функции run_tui."""
        from parser_2gis.tui_textual import run_tui

        assert callable(run_tui)


class TestTUIScreens:
    """Тесты для проверки экранов TUI."""

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_main_menu_screen_import(self):
        """Проверка импорта главного меню."""
        from parser_2gis.tui_textual.screens import MainMenuScreen

        assert MainMenuScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_city_selector_screen_import(self):
        """Проверка импорта экрана выбора городов."""
        from parser_2gis.tui_textual.screens import CitySelectorScreen

        assert CitySelectorScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_category_selector_screen_import(self):
        """Проверка импорта экрана выбора категорий."""
        from parser_2gis.tui_textual.screens import CategorySelectorScreen

        assert CategorySelectorScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_parsing_screen_import(self):
        """Проверка импорта экрана парсинга."""
        from parser_2gis.tui_textual.screens import ParsingScreen

        assert ParsingScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_settings_screens_import(self):
        """Проверка импорта экранов настроек."""
        from parser_2gis.tui_textual.screens import (
            BrowserSettingsScreen,
            ParserSettingsScreen,
            OutputSettingsScreen,
        )

        assert BrowserSettingsScreen is not None
        assert ParserSettingsScreen is not None
        assert OutputSettingsScreen is not None

    @pytest.mark.skipif(not TEXTUAL_AVAILABLE, reason="textual не установлен")
    def test_other_screens_import(self):
        """Проверка импорта дополнительных экранов."""
        from parser_2gis.tui_textual.screens import CacheViewerScreen, AboutScreen

        assert CacheViewerScreen is not None
        assert AboutScreen is not None


class TestCoreImports:
    """Тесты для проверки основных импортов проекта."""

    def test_main_module_import(self):
        """Проверка импорта основного модуля."""
        from parser_2gis import main

        assert main is not None

    def test_config_import(self):
        """Проверка импорта конфигурации."""
        from parser_2gis.config import Configuration

        assert Configuration is not None

    def test_parallel_parser_import(self):
        """Проверка импорта параллельного парсера."""
        from parser_2gis.parallel_parser import ParallelCityParser

        assert ParallelCityParser is not None

    def test_cache_manager_import(self):
        """Проверка импорта менеджера кэша."""
        from parser_2gis.cache import CacheManager

        assert CacheManager is not None
