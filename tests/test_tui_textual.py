"""
Тесты для TUI Parser2GIS на Textual.

Содержит 10 тестов для проверки работы нового TUI интерфейса.
"""

import pytest

try:
    from textual.app import App

    from parser_2gis.tui_textual.app import Parser2GISTUI, TUIApp
    from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen
    from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen
    from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen
    from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen
    from parser_2gis.tui_textual.screens.settings import BrowserSettingsScreen

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)

# Проверка доступности pytest-asyncio
try:
    import importlib.util

    _spec = importlib.util.find_spec("pytest_asyncio")
    ASYNCIO_AVAILABLE = _spec is not None
except (ImportError, AttributeError):
    ASYNCIO_AVAILABLE = False
    pytest.skip("pytest-asyncio not installed", allow_module_level=True)


class TestTUIApp:
    """Тесты для основного приложения TUI."""

    @pytest.mark.asyncio
    async def test_app_initialization(self) -> None:
        """Тест 1: Проверка инициализации приложения."""
        app = TUIApp()
        assert app is not None
        assert isinstance(app, App)
        assert hasattr(app, "_config")
        assert hasattr(app, "_state")
        assert app.selected_cities == []
        assert app.selected_categories == []

    @pytest.mark.asyncio
    async def test_app_config_loading(self) -> None:
        """Тест 2: Проверка загрузки конфигурации."""
        app = TUIApp()
        config = app.get_config()
        assert config is not None
        assert hasattr(config, "chrome")
        assert hasattr(config, "parser")
        assert hasattr(config, "writer")

    @pytest.mark.asyncio
    async def test_app_state_management(self) -> None:
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
    async def test_app_cities_loading(self) -> None:
        """Тест 4: Проверка загрузки городов."""
        app = TUIApp()
        cities = app.get_cities()

        assert isinstance(cities, list)
        if cities:
            assert "name" in cities[0]
            assert "country_code" in cities[0]

    @pytest.mark.asyncio
    async def test_app_categories_loading(self) -> None:
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

    def test_main_menu_screen_creation(self) -> None:
        """Тест 6: Проверка создания главного меню."""
        screen = MainMenuScreen()
        assert screen is not None
        # Проверка, что экран имеет правильные атрибуты
        assert hasattr(screen, "compose")

    def test_city_selector_screen_creation(self) -> None:
        """Тест 7: Проверка создания экрана выбора городов."""
        screen = CitySelectorScreen()
        assert screen is not None
        assert hasattr(screen, "_cities")
        assert hasattr(screen, "_selected_indices")

    def test_category_selector_screen_creation(self) -> None:
        """Тест 8: Проверка создания экрана выбора категорий."""
        screen = CategorySelectorScreen()
        assert screen is not None
        assert hasattr(screen, "_categories")
        # Категории загружаются в on_mount, поэтому проверяем наличие атрибута
        assert hasattr(screen, "_filtered_categories")
        assert hasattr(screen, "_selected_indices")

    def test_browser_settings_screen_creation(self) -> None:
        """Тест 9: Проверка создания экрана настроек браузера."""
        screen = BrowserSettingsScreen()
        assert screen is not None
        assert hasattr(screen, "compose")

    def test_parsing_screen_creation(self) -> None:
        """Тест 10: Проверка создания экрана парсинга."""
        screen = ParsingScreen()
        assert screen is not None
        assert hasattr(screen, "_paused")
        # Проверяем наличие основных атрибутов
        assert hasattr(screen, "_start_time")
        assert hasattr(screen, "_success_count")


class TestTUINavigation:
    """Тесты для навигации в TUI."""

    def test_screen_registration(self) -> None:
        """Тест навигации между экранами."""
        _app = TUIApp()

        # Проверка, что все экраны зарегистрированы
        assert "main_menu" in _app.SCREENS
        assert "city_selector" in _app.SCREENS
        assert "category_selector" in _app.SCREENS
        assert "parsing" in _app.SCREENS
        assert "browser_settings" in _app.SCREENS
        assert "parser_settings" in _app.SCREENS
        assert "output_settings" in _app.SCREENS
        assert "cache_viewer" in _app.SCREENS
        assert "about" in _app.SCREENS


class TestTUIBindings:
    """Тесты для горячих клавиш."""

    def test_bindings_defined(self) -> None:
        """Тест горячих клавиш."""
        _app = TUIApp()

        # Проверка, что горячие клавиши определены
        assert len(_app.BINDINGS) > 0

        # Проверка наличия конкретных привязок
        binding_keys = [b.key for b in _app.BINDINGS]
        assert "q" in binding_keys
        assert "escape" in binding_keys
        assert "d" in binding_keys


class TestTUIIntegration:
    """Интеграционные тесты TUI."""

    def test_app_has_all_methods(self) -> None:
        """Тест полного рабочего процесса."""
        _app = TUIApp()

        # Проверка наличия всех необходимых методов
        assert hasattr(_app, "push_screen")
        assert hasattr(_app, "pop_screen")
        assert hasattr(_app, "get_config")
        assert hasattr(_app, "save_config")
        assert hasattr(_app, "get_cities")
        assert hasattr(_app, "get_categories")
        assert hasattr(_app, "update_state")
        assert hasattr(_app, "get_state")


class TestTUIUtils:
    """Тесты для утилит TUI."""

    def test_parser2gistui_wrapper(self) -> None:
        """Тест обёртки Parser2GISTUI."""
        wrapper = Parser2GISTUI()
        assert wrapper is not None
        assert hasattr(wrapper, "_app")
        assert isinstance(wrapper._app, TUIApp)

    def test_run_tui_function(self) -> None:
        """Тест функции run_tui."""
        from parser_2gis.tui_textual.app import run_tui

        assert callable(run_tui)
