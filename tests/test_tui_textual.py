"""
Тесты для TUI Parser2GIS на Textual.

Содержит 10 тестов для проверки работы нового TUI интерфейса.
"""

import pytest
from textual.app import App
from textual.widgets import Button, Input, Checkbox, Static, Label
from textual.containers import Container

from parser_2gis.tui_textual.app import TUIApp, Parser2GISTUI
from parser_2gis.tui_textual.screens import (
    MainMenuScreen,
    CitySelectorScreen,
    CategorySelectorScreen,
    ParsingScreen,
    BrowserSettingsScreen,
    ParserSettingsScreen,
    OutputSettingsScreen,
    CacheViewerScreen,
    AboutScreen,
)


class TestTUIApp:
    """Тесты для основного приложения TUI."""

    @pytest.mark.asyncio
    async def test_app_initialization(self):
        """Тест 1: Проверка инициализации приложения."""
        app = TUIApp()
        assert app is not None
        assert isinstance(app, App)
        assert hasattr(app, "_config")
        assert hasattr(app, "_state")
        assert app.selected_cities == []
        assert app.selected_categories == []

    @pytest.mark.asyncio
    async def test_app_config_loading(self):
        """Тест 2: Проверка загрузки конфигурации."""
        app = TUIApp()
        config = app.get_config()
        assert config is not None
        assert hasattr(config, "chrome")
        assert hasattr(config, "parser")
        assert hasattr(config, "writer")

    @pytest.mark.asyncio
    async def test_app_state_management(self):
        """Тест 3: Проверка управления состоянием."""
        app = TUIApp()
        
        # Проверка начального состояния
        assert app.get_state("selected_cities") == []
        assert app.get_state("selected_categories") == []
        
        # Обновление состояния
        app.selected_cities = ["Москва", "СПб"]
        app.selected_categories = ["Аптеки", "Рестораны"]
        
        assert app.get_state("selected_cities") == ["Москва", "СПб"]
        assert app.get_state("selected_categories") == ["Аптеки", "Рестораны"]

    @pytest.mark.asyncio
    async def test_app_cities_loading(self):
        """Тест 4: Проверка загрузки городов."""
        app = TUIApp()
        cities = app.get_cities()
        
        assert isinstance(cities, list)
        if cities:
            assert "name" in cities[0]
            assert "country_code" in cities[0]

    @pytest.mark.asyncio
    async def test_app_categories_loading(self):
        """Тест 5: Проверка загрузки категорий."""
        app = TUIApp()
        categories = app.get_categories()
        
        assert isinstance(categories, list)
        assert len(categories) > 0
        
        # Проверка структуры категории
        if categories:
            assert "name" in categories[0]
            assert "query" in categories[0] or "rubric_code" in categories[0]


class TestTUIScreens:
    """Тесты для экранов TUI."""

    def test_main_menu_screen_creation(self):
        """Тест 6: Проверка создания главного меню."""
        app = TUIApp()
        screen = MainMenuScreen()
        assert screen is not None
        # Проверка, что экран имеет правильные атрибуты
        assert hasattr(screen, "compose")

    def test_city_selector_screen_creation(self):
        """Тест 7: Проверка создания экрана выбора городов."""
        app = TUIApp()
        screen = CitySelectorScreen()
        assert screen is not None
        assert hasattr(screen, "_cities")
        assert hasattr(screen, "_selected_indices")

    def test_category_selector_screen_creation(self):
        """Тест 8: Проверка создания экрана выбора категорий."""
        app = TUIApp()
        screen = CategorySelectorScreen()
        assert screen is not None
        assert hasattr(screen, "_categories")
        # Категории загружаются в on_mount, поэтому проверяем наличие атрибута
        assert hasattr(screen, "_filtered_categories")
        assert hasattr(screen, "_selected_indices")

    def test_browser_settings_screen_creation(self):
        """Тест 9: Проверка создания экрана настроек браузера."""
        app = TUIApp()
        screen = BrowserSettingsScreen()
        assert screen is not None
        assert hasattr(screen, "compose")

    def test_parsing_screen_creation(self):
        """Тест 10: Проверка создания экрана парсинга."""
        app = TUIApp()
        screen = ParsingScreen()
        assert screen is not None
        assert hasattr(screen, "_paused")
        # Проверяем наличие основных атрибутов
        assert hasattr(screen, "_start_time")
        assert hasattr(screen, "_success_count")


class TestTUINavigation:
    """Тесты для навигации в TUI."""

    def test_screen_registration(self):
        """Тест навигации между экранами."""
        app = TUIApp()
        
        # Проверка, что все экраны зарегистрированы
        assert "main_menu" in app.SCREENS
        assert "city_selector" in app.SCREENS
        assert "category_selector" in app.SCREENS
        assert "parsing" in app.SCREENS
        assert "browser_settings" in app.SCREENS
        assert "parser_settings" in app.SCREENS
        assert "output_settings" in app.SCREENS
        assert "cache_viewer" in app.SCREENS
        assert "about" in app.SCREENS


class TestTUIBindings:
    """Тесты для горячих клавиш."""

    def test_bindings_defined(self):
        """Тест горячих клавиш."""
        app = TUIApp()
        
        # Проверка, что горячие клавиши определены
        assert len(app.BINDINGS) > 0
        
        # Проверка наличия конкретных привязок
        binding_keys = [b.key for b in app.BINDINGS]
        assert "q" in binding_keys
        assert "escape" in binding_keys
        assert "d" in binding_keys


class TestTUIIntegration:
    """Интеграционные тесты TUI."""

    def test_app_has_all_methods(self):
        """Тест полного рабочего процесса."""
        app = TUIApp()
        
        # Проверка наличия всех необходимых методов
        assert hasattr(app, "push_screen")
        assert hasattr(app, "pop_screen")
        assert hasattr(app, "get_config")
        assert hasattr(app, "save_config")
        assert hasattr(app, "get_cities")
        assert hasattr(app, "get_categories")
        assert hasattr(app, "update_state")
        assert hasattr(app, "get_state")


class TestTUIUtils:
    """Тесты для утилит TUI."""

    def test_parser2gistui_wrapper(self):
        """Тест обёртки Parser2GISTUI."""
        wrapper = Parser2GISTUI()
        assert wrapper is not None
        assert hasattr(wrapper, "_app")
        assert isinstance(wrapper._app, TUIApp)

    def test_run_tui_function(self):
        """Тест функции run_tui."""
        from parser_2gis.tui_textual.app import run_tui
        assert callable(run_tui)
