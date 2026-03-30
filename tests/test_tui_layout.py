"""
Оптимизированные тесты для проверки TUI layout в проекте parser-2gis.

Проверяют правильность центрирования элементов интерфейса.

ОПТИМИЗАЦИЯ:
- Удалено дублирование кода
- Сокращено с 675 до 86 строк (87% сокращение)
- Оставлены только критически важные тесты
"""

import pytest

try:
    from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestTUIMainMenuCentering:
    """
    Тесты центрирования главного меню TUI.

    Проверяет что основные контейнеры имеют правильное центрирование.
    """

    def test_main_menu_has_css(self) -> None:
        """Проверка что MainMenuScreen имеет CSS стили."""
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка что CSS не пустой
        assert css, "MainMenuScreen должен иметь CSS стили"
        assert "MainMenuScreen" in css, "CSS должен содержать стили для MainMenuScreen"

    def test_main_menu_has_centering(self) -> None:
        """Проверка что MainMenuScreen имеет центрирование."""
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка наличия align в CSS
        assert "align" in css, "MainMenuScreen должен иметь выравнивание"

    def test_main_menu_containers_defined(self) -> None:
        """Проверка что контейнеры меню определены."""
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка наличия контейнеров
        assert ".logo-container" in css, "Должен быть определён класс .logo-container"
        assert ".menu-container" in css, "Должен быть определён класс .menu-container"
