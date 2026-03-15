"""
Тесты для проверки зависимостей и импортов.

Эти тесты выявляют ошибки на раннем этапе:
- Отсутствие необходимых зависимостей
- Ошибки импорта модулей
- Некорректная конфигурация YAML стилей
- Проблемы с инициализацией TUI компонентов
"""

import pytest
import sys
from pathlib import Path


# Добавляем проект в path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestYamlDependency:
    """Тесты для проверки YAML зависимости."""

    def test_yaml_module_import(self):
        """Проверка импорта yaml модуля."""
        try:
            import yaml
            assert hasattr(yaml, 'safe_load'), "yaml модуль не имеет safe_load"
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
        assert result['config']['key'] == 'value'
        assert result['config']['number'] == 42

    def test_yaml_loader_exists(self):
        """Проверка доступности YamlLoader из pytermgui."""
        try:
            import pytermgui as ptg
            assert hasattr(ptg, 'YamlLoader'), "pytermgui не имеет YamlLoader"
        except ImportError:
            pytest.fail("pytermgui не установлен")


class TestTUIStyles:
    """Тесты для проверки стилей TUI."""

    def test_styles_module_import(self):
        """Проверка импорта модуля стилей."""
        try:
            from parser_2gis.tui_pytermgui.styles import get_default_styles
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать стили: {e}")

    def test_get_default_styles_returns_string(self):
        """Проверка что get_default_styles возвращает строку."""
        from parser_2gis.tui_pytermgui.styles import get_default_styles
        
        result = get_default_styles()
        assert isinstance(result, str), "get_default_styles должна возвращать строку"
        assert len(result) > 0, "Стили не должны быть пустыми"

    def test_styles_yaml_valid(self):
        """Проверка валидности YAML стилей."""
        import yaml
        from parser_2gis.tui_pytermgui.styles import get_default_styles
        
        styles_yaml = get_default_styles()
        
        try:
            parsed = yaml.safe_load(styles_yaml)
            assert parsed is not None, "YAML не должен быть пустым"
            assert 'config' in parsed, "YAML должен содержать 'config'"
        except yaml.YAMLError as e:
            pytest.fail(f"Некорректный YAML в стилях: {e}")

    def test_styles_yaml_structure(self):
        """Проверка структуры YAML стилей."""
        import yaml
        from parser_2gis.tui_pytermgui.styles import get_default_styles
        
        styles_yaml = get_default_styles()
        parsed = yaml.safe_load(styles_yaml)
        
        # Проверяем наличие основных компонентов
        assert 'config' in parsed
        config = parsed['config']
        assert 'palette' in config, "Конфигурация должна содержать палитру"
        
        # Проверяем наличие основных цветов
        palette = config['palette']
        required_colors = ['primary', 'secondary', 'accent', 'error']
        for color in required_colors:
            assert color in palette, f"Палитра должна содержать цвет '{color}'"


class TestTUIAppImport:
    """Тесты для проверки импорта TUI приложения."""

    def test_tui_app_import(self):
        """Проверка импорта TUIApp."""
        try:
            from parser_2gis.tui_pytermgui.app import TUIApp
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать TUIApp: {e}")

    def test_tui_app_instantiation(self):
        """Проверка создания экземпляра TUIApp."""
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        app = TUIApp()
        assert app is not None
        assert hasattr(app, 'run')
        assert hasattr(app, 'get_config')

    def test_tui_wrapper_import(self):
        """Проверка импорта Parser2GISTUI."""
        try:
            from parser_2gis.tui_pytermgui.app import Parser2GISTUI
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать Parser2GISTUI: {e}")

    def test_tui_wrapper_instantiation(self):
        """Проверка создания экземпляра Parser2GISTUI."""
        from parser_2gis.tui_pytermgui.app import Parser2GISTUI
        
        app = Parser2GISTUI()
        assert app is not None
        assert hasattr(app, 'run')


class TestPytermguiComponents:
    """Тесты для проверки компонентов pytermgui."""

    def test_pytermgui_import(self):
        """Проверка импорта pytermgui."""
        try:
            import pytermgui as ptg
        except ImportError:
            pytest.fail("pytermgui не установлен. Установите: pip install pytermgui")
        
        # Проверяем основные компоненты
        assert hasattr(ptg, 'Window')
        assert hasattr(ptg, 'WindowManager')
        assert hasattr(ptg, 'YamlLoader')

    def test_window_creation(self):
        """Проверка создания окна."""
        import pytermgui as ptg
        
        window = ptg.Window("Test content")
        assert window is not None

    def test_yaml_loader_context_manager(self):
        """Проверка работы YamlLoader как контекстного менеджера."""
        import pytermgui as ptg
        
        yaml_content = """
        test:
            key: value
        """
        
        with ptg.YamlLoader() as loader:
            result = loader.load(yaml_content)
        
        # YamlLoader возвращает WidgetNamespace или dict в зависимости от контента
        assert result is not None
        # Проверяем что результат имеет атрибуты или ключи
        assert hasattr(result, '__dict__') or hasattr(result, '__getitem__')


class TestConfigurationLoading:
    """Тесты для проверки загрузки конфигурации."""

    def test_configuration_import(self):
        """Проверка импорта Configuration."""
        try:
            from parser_2gis.config import Configuration
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать Configuration: {e}")

    def test_configuration_default_creation(self):
        """Проверка создания конфигурации по умолчанию."""
        from parser_2gis.config import Configuration
        
        config = Configuration()
        assert config is not None
        assert hasattr(config, 'chrome')
        assert hasattr(config, 'parser')
        assert hasattr(config, 'writer')

    def test_configuration_load_config(self):
        """Проверка метода load_config."""
        from parser_2gis.config import Configuration
        
        config = Configuration.load_config()
        assert config is not None


class TestTUIScreensImport:
    """Тесты для проверки импорта экранов TUI."""

    def test_main_menu_screen_import(self):
        """Проверка импорта MainMenuScreen."""
        try:
            from parser_2gis.tui_pytermgui.screens import MainMenuScreen
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать MainMenuScreen: {e}")

    def test_city_selector_screen_import(self):
        """Проверка импорта CitySelectorScreen."""
        try:
            from parser_2gis.tui_pytermgui.screens import CitySelectorScreen
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать CitySelectorScreen: {e}")

    def test_category_selector_screen_import(self):
        """Проверка импорта CategorySelectorScreen."""
        try:
            from parser_2gis.tui_pytermgui.screens import CategorySelectorScreen
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать CategorySelectorScreen: {e}")

    def test_parsing_screen_import(self):
        """Проверка импорта ParsingScreen."""
        try:
            from parser_2gis.tui_pytermgui.screens import ParsingScreen
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать ParsingScreen: {e}")


class TestParallelParserImport:
    """Тесты для проверки импорта параллельного парсера."""

    def test_parallel_city_parser_import(self):
        """Проверка импорта ParallelCityParser."""
        try:
            from parser_2gis.parallel_parser import ParallelCityParser
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать ParallelCityParser: {e}")

    def test_parallel_parser_instantiation(self):
        """Проверка что ParallelCityParser имеет необходимые методы."""
        from parser_2gis.parallel_parser import ParallelCityParser
        
        # Проверяем наличие ключевых методов (без создания экземпляра)
        assert hasattr(ParallelCityParser, 'run')
        assert hasattr(ParallelCityParser, '__init__')
