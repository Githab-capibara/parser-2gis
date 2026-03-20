"""
Тесты для проверки TUI layout в проекте parser-2gis.

Проверяют правильность центрирования, адаптивности и выравнивания элементов интерфейса.
"""

import re
from pathlib import Path
from typing import List, Tuple

import pytest

# Пытаемся импортировать textual, если нет - пропускаем тесты
try:
    from textual.app import App
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Button, Static

    from parser_2gis.tui_textual.app import TUIApp
    from parser_2gis.tui_textual.screens.category_selector import CategorySelectorScreen
    from parser_2gis.tui_textual.screens.city_selector import CitySelectorScreen
    from parser_2gis.tui_textual.screens.main_menu import MainMenuScreen
    from parser_2gis.tui_textual.screens.other_screens import (
        AboutScreen,
        CacheViewerScreen,
    )
    from parser_2gis.tui_textual.screens.parsing_screen import ParsingScreen
    from parser_2gis.tui_textual.screens.settings import (
        BrowserSettingsScreen,
        OutputSettingsScreen,
        ParserSettingsScreen,
    )

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    pytest.skip("textual not installed", allow_module_level=True)


class TestTUIMainMenuCentering:
    """
    Тест 1: Проверка центрирования элементов TUI.

    Проверяет, что все основные контейнеры имеют правильное центрирование
    (align: center middle).
    """

    def test_tui_main_menu_centering(self):
        """
        Проверка центрирования главного меню.

        Тест проверяет:
        - Наличие align: center middle в стилях MainMenuScreen
        - Центрирование контейнера .logo-container
        - Центрирование .menu-container
        """
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка центрирования самого экрана
        assert "MainMenuScreen {" in css, "MainMenuScreen должен иметь CSS стили"
        assert "align: center middle" in css, (
            "MainMenuScreen должен иметь центрирование 'align: center middle'"
        )

        # Проверка центрирования контейнера логотипа
        assert ".logo-container" in css, "Должен быть определён класс .logo-container"

        # Проверка центрирования контейнера меню
        assert ".menu-container" in css, "Должен быть определён класс .menu-container"

        # Извлекаем стили для .menu-container и проверяем центрирование
        menu_container_styles = self._extract_css_block(css, ".menu-container")
        assert "align: center middle" in menu_container_styles, (
            ".menu-container должен иметь центрирование 'align: center middle'"
        )

        # Извлекаем стили для .logo-container и проверяем центрирование
        logo_container_styles = self._extract_css_block(css, ".logo-container")
        assert "align: center middle" in logo_container_styles, (
            ".logo-container должен иметь центрирование 'align: center middle'"
        )

    def test_tui_all_screens_centering(self):
        """
        Проверка центрирования всех экранов приложения.

        Тест проверяет наличие align: center middle в стилях всех экранов.
        """
        screens_with_css = [
            (MainMenuScreen, "MainMenuScreen"),
            (CitySelectorScreen, "CitySelectorScreen"),
            (CategorySelectorScreen, "CategorySelectorScreen"),
            (ParsingScreen, "ParsingScreen"),
            (BrowserSettingsScreen, "BrowserSettingsScreen"),
            (ParserSettingsScreen, "ParserSettingsScreen"),
            (OutputSettingsScreen, "OutputSettingsScreen"),
            (CacheViewerScreen, "CacheViewerScreen"),
            (AboutScreen, "AboutScreen"),
        ]

        for screen_class, screen_name in screens_with_css:
            screen = screen_class()
            css = screen.CSS

            # Проверка центрирования экрана
            screen_block = self._extract_css_block(css, f"{screen_name} {{")
            assert "align: center middle" in screen_block, (
                f"{screen_name} должен иметь центрирование 'align: center middle'"
            )

    def test_tui_main_app_screen_centering(self):
        """
        Проверка центрирования в главном приложении TUIApp.

        Тест проверяет наличие align: center middle в базовых стилях Screen.
        """
        app = TUIApp()
        css = app.CSS

        # Проверка базовых стилей Screen
        screen_block = self._extract_css_block(css, "Screen {")
        assert "align: center middle" in screen_block, (
            "Базовые стили Screen должны иметь центрирование 'align: center middle'"
        )

    def _extract_css_block(self, css: str, selector: str) -> str:
        """
        Извлечь блок CSS по селектору.

        Args:
            css: Полный CSS текст
            selector: CSS селектор для поиска

        Returns:
            Строка с CSS правилами внутри блока
        """
        # Экранируем специальные символы в селекторе
        escaped_selector = re.escape(selector.rstrip(" {"))
        pattern = rf"{escaped_selector}\s*\{{([^}}]+)\}}"
        match = re.search(pattern, css)
        if match:
            return match.group(1)
        return ""


class TestTUIContainerResponsiveWidth:
    """
    Тест 2: Проверка адаптивности ширины контейнеров.

    Проверяет, что контейнеры используют адаптивную ширину
    (width: 100% с max-width/min-width) вместо фиксированных значений.
    """

    def test_tui_container_responsive_width(self):
        """
        Проверка адаптивности ширины контейнеров.

        Тест проверяет:
        - Наличие width: 100% у основных контейнеров
        - Наличие max-width для ограничения максимальной ширины
        - Наличие min-width для ограничения минимальной ширины
        """
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка .logo-container
        logo_container_styles = self._extract_css_block(css, ".logo-container")
        assert "width: 100%" in logo_container_styles, (
            ".logo-container должен иметь width: 100%"
        )
        assert "max-width:" in logo_container_styles, (
            ".logo-container должен иметь max-width для адаптивности"
        )
        assert "min-width:" in logo_container_styles, (
            ".logo-container должен иметь min-width для адаптивности"
        )

        # Проверка .menu-container
        menu_container_styles = self._extract_css_block(css, ".menu-container")
        assert "width: 100%" in menu_container_styles, (
            ".menu-container должен иметь width: 100%"
        )
        assert "max-width:" in menu_container_styles, (
            ".menu-container должен иметь max-width для адаптивности"
        )
        assert "min-width:" in menu_container_styles, (
            ".menu-container должен иметь min-width для адаптивности"
        )

    def test_tui_no_fixed_width_without_max(self):
        """
        Проверка отсутствия фиксированных ширин без max-width.

        Тест проверяет, что если у контейнера есть фиксированная ширина,
        то также должен быть определён max-width.
        """
        screens = [
            MainMenuScreen(),
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
        ]

        # Контейнеры для проверки
        containers_to_check = [
            "#main-menu",
            ".menu-container",
            "#city-selector-container",
            "#category-selector-container",
            "#parsing-container",
        ]

        for screen in screens:
            css = screen.CSS

            for container in containers_to_check:
                styles = self._extract_css_block(css, container)
                if styles:
                    # Если есть width: 100%, проверяем наличие max-width
                    if "width: 100%" in styles:
                        assert "max-width:" in styles, (
                            f"{container} в {screen.__class__.__name__} должен иметь max-width при width: 100%"
                        )

    def test_tui_title_container_responsive(self):
        """
        Проверка адаптивности title контейнера.

        Тест проверяет, что контейнеры заголовков используют адаптивную ширину.
        """
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка .logo-container
        logo_container_styles = self._extract_css_block(css, ".logo-container")
        assert "width: 100%" in logo_container_styles, (
            ".logo-container должен иметь width: 100%"
        )
        assert "max-width:" in logo_container_styles, (
            ".logo-container должен иметь max-width"
        )
        assert "min-width:" in logo_container_styles, (
            ".logo-container должен иметь min-width"
        )

        # Проверка .title (должна иметь width: 100%)
        title_styles = self._extract_css_block(css, ".title")
        assert "width: 100%" in title_styles, ".title должен иметь width: 100%"

        # Проверка .subtitle (должна иметь width: 100%)
        subtitle_styles = self._extract_css_block(css, ".subtitle")
        assert "width: 100%" in subtitle_styles, ".subtitle должен иметь width: 100%"

    def test_tui_settings_screens_responsive(self):
        """
        Проверка адаптивности экранов настроек.

        Тест проверяет, что все экраны настроек используют адаптивную ширину.
        """
        screens = [
            (BrowserSettingsScreen, "BrowserSettingsScreen"),
            (ParserSettingsScreen, "ParserSettingsScreen"),
            (OutputSettingsScreen, "OutputSettingsScreen"),
        ]

        for screen_class, screen_name in screens:
            screen = screen_class()
            css = screen.CSS

            container_id = f"#{screen_name.replace('Screen', '').lower().replace('_', '-')}-container"
            container_styles = self._extract_css_block(css, container_id)

            if container_styles:
                assert "width: 100%" in container_styles, (
                    f"{container_id} должен иметь width: 100%"
                )
                assert "max-width:" in container_styles, (
                    f"{container_id} должен иметь max-width"
                )
                assert "min-width:" in container_styles, (
                    f"{container_id} должен иметь min-width"
                )

    def _extract_css_block(self, css: str, selector: str) -> str:
        """
        Извлечь блок CSS по селектору.

        Args:
            css: Полный CSS текст
            selector: CSS селектор для поиска

        Returns:
            Строка с CSS правилами внутри блока
        """
        escaped_selector = re.escape(selector.rstrip(" {"))
        pattern = rf"{escaped_selector}\s*\{{([^}}]+)\}}"
        match = re.search(pattern, css)
        if match:
            return match.group(1)
        return ""


class TestTUIButtonAlignment:
    """
    Тест 3: Проверка выравнивания кнопок.

    Проверяет, что кнопки выровнены по центру и имеют правильные отступы.
    """

    def test_tui_button_alignment(self):
        """
        Проверка выравнивания кнопок в главном меню.

        Тест проверяет:
        - Наличие align: center middle у .menu-button
        - Наличие правильных отступов (margin)
        - Ширину кнопок (width: 100%)
        """
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка стилей кнопки меню
        menu_button_styles = self._extract_css_block(css, ".menu-button")
        assert "width: 100%" in menu_button_styles, (
            ".menu-button должен иметь width: 100%"
        )
        assert "margin:" in menu_button_styles, ".menu-button должен иметь margin"
        assert "align: center middle" in menu_button_styles, (
            ".menu-button должен иметь центрирование 'align: center middle'"
        )

    def test_tui_button_row_alignment(self):
        """
        Проверка выравнивания кнопок в рядах (button-row).

        Тест проверяет, что контейнеры с кнопками имеют правильное выравнивание.
        """
        screens = [
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
        ]

        for screen in screens:
            css = screen.CSS

            # Проверка .button-row
            button_row_styles = self._extract_css_block(css, ".button-row")
            if button_row_styles:
                assert "width: 100%" in button_row_styles, (
                    f".button-row в {screen.__class__.__name__} должен иметь width: 100%"
                )
                assert "align: center middle" in button_row_styles, (
                    f".button-row в {screen.__class__.__name__} должен иметь центрирование"
                )

    def test_tui_button_margins(self):
        """
        Проверка отступов кнопок в рядах.

        Тест проверяет наличие правильных отступов у кнопок в button-row.
        """
        screens = [
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
            CacheViewerScreen(),
            AboutScreen(),
        ]

        for screen in screens:
            css = screen.CSS

            # Проверка стилей кнопок в button-row
            button_row_button_styles = self._extract_css_block(
                css, ".button-row Button"
            )
            if button_row_button_styles:
                assert "margin:" in button_row_button_styles, (
                    f"Кнопки в .button-row в {screen.__class__.__name__} должны иметь margin"
                )
                assert "min-width:" in button_row_button_styles, (
                    f"Кнопки в .button-row в {screen.__class__.__name__} должны иметь min-width"
                )

    def test_tui_horizontal_container_for_buttons(self):
        """
        Проверка использования Horizontal контейнеров для кнопок.

        Тест проверяет, что кнопки в рядах используют Horizontal контейнеры.
        """
        # Проверяем, что в CSS есть упоминание Horizontal контейнеров
        # через класс .button-row
        screens = [
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
        ]

        for screen in screens:
            css = screen.CSS

            # Проверка наличия .button-row
            assert ".button-row" in css, (
                f"{screen.__class__.__name__} должен иметь .button-row для кнопок"
            )

            # Проверка выравнивания
            button_row_styles = self._extract_css_block(css, ".button-row")
            assert "align: center middle" in button_row_styles, (
                f".button-row в {screen.__class__.__name__} должен иметь центрирование"
            )

    def test_tui_settings_buttons_alignment(self):
        """
        Проверка выравнивания кнопок в экранах настроек.

        Тест проверяет, что кнопки в экранах настроек выровнены правильно.
        """
        screens = [
            BrowserSettingsScreen(),
            ParserSettingsScreen(),
            OutputSettingsScreen(),
        ]

        for screen in screens:
            css = screen.CSS

            # Проверка .button-row
            button_row_styles = self._extract_css_block(css, ".button-row")
            assert "align: center middle" in button_row_styles, (
                f".button-row в {screen.__class__.__name__} должен иметь центрирование"
            )
            assert "margin-top:" in button_row_styles, (
                f".button-row в {screen.__class__.__name__} должен иметь margin-top"
            )

    def _extract_css_block(self, css: str, selector: str) -> str:
        """
        Извлечь блок CSS по селектору.

        Args:
            css: Полный CSS текст
            selector: CSS селектор для поиска

        Returns:
            Строка с CSS правилами внутри блока
        """
        escaped_selector = re.escape(selector.rstrip(" {"))
        pattern = rf"{escaped_selector}\s*\{{([^}}]+)\}}"
        match = re.search(pattern, css)
        if match:
            return match.group(1)
        return ""


class TestTUILayoutIntegration:
    """
    Интеграционные тесты для проверки общего layout TUI.
    """

    def test_tui_all_screens_have_css(self):
        """
        Проверка наличия CSS стилей у всех экранов.

        Тест проверяет, что каждый экран имеет определённые CSS стили.
        """
        screens = [
            MainMenuScreen(),
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
            BrowserSettingsScreen(),
            ParserSettingsScreen(),
            OutputSettingsScreen(),
            CacheViewerScreen(),
            AboutScreen(),
        ]

        for screen in screens:
            assert hasattr(screen, "CSS"), (
                f"{screen.__class__.__name__} должен иметь CSS атрибут"
            )
            assert len(screen.CSS) > 0, (
                f"{screen.__class__.__name__} должен иметь непустые CSS стили"
            )

    def test_tui_consistent_naming(self):
        """
        Проверка согласованности имён CSS классов.

        Тест проверяет, что имена классов следуют единому стилю.
        """
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка наличия стандартных классов
        expected_classes = [
            ".logo",
            ".title",
            ".subtitle",
            ".menu-container",
            ".menu-button",
            ".divider",
        ]

        for class_name in expected_classes:
            assert class_name in css, f"MainMenuScreen должен иметь класс {class_name}"

    def test_tui_content_alignment_classes(self):
        """
        Проверка классов для выравнивания контента.

        Тест проверяет наличие content-align в стилях.
        """
        screen = MainMenuScreen()
        css = screen.CSS

        # Проверка наличия content-align
        assert "content-align:" in css, (
            "MainMenuScreen должен использовать content-align для выравнивания контента"
        )


class TestTUIResponsivePatterns:
    """
    Тесты для проверки паттернов адаптивного дизайна.
    """

    def test_tui_percentage_widths(self):
        """
        Проверка использования процентных ширин.

        Тест проверяет, что основные контейнеры используют width: 100%.
        """
        screens = [
            MainMenuScreen(),
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
        ]

        for screen in screens:
            css = screen.CSS
            assert "width: 100%" in css, (
                f"{screen.__class__.__name__} должен использовать width: 100%"
            )

    def test_tui_max_width_constraints(self):
        """
        Проверка ограничений максимальной ширины.

        Тест проверяет наличие max-width для ограничения ширины контейнеров.
        """
        screens = [
            MainMenuScreen(),
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
        ]

        for screen in screens:
            css = screen.CSS
            assert "max-width:" in css, (
                f"{screen.__class__.__name__} должен использовать max-width"
            )

    def test_tui_min_width_constraints(self):
        """
        Проверка ограничений минимальной ширины.

        Тест проверяет наличие min-width для предотвращения слишком узких контейнеров.
        """
        screens = [
            MainMenuScreen(),
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
        ]

        for screen in screens:
            css = screen.CSS
            assert "min-width:" in css, (
                f"{screen.__class__.__name__} должен использовать min-width"
            )

    def test_tui_height_constraints(self):
        """
        Проверка ограничений высоты.

        Тест проверяет использование height: auto и height: 1fr.
        """
        # MainMenuScreen использует только height: auto
        main_menu_screen = MainMenuScreen()
        main_menu_css = main_menu_screen.CSS

        # Проверка наличия height: auto
        assert "height: auto" in main_menu_css, (
            "MainMenuScreen должен использовать height: auto"
        )

        # Другие экраны используют height: 1fr для гибких контейнеров
        other_screens = [
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
        ]

        for screen in other_screens:
            css = screen.CSS
            assert "height: 1fr" in css, (
                f"{screen.__class__.__name__} должен использовать height: 1fr"
            )


# Дополнительные тесты для проверки конкретных требований
class TestTUISpecificRequirements:
    """
    Тесты для проверки конкретных требований к TUI layout.
    """

    def test_screen_align_center_middle(self):
        """
        Проверка наличия align: center middle в Screen стилях.

        Тест проверяет все экраны на наличие правильного центрирования.
        """
        screens = [
            (MainMenuScreen, "MainMenuScreen"),
            (CitySelectorScreen, "CitySelectorScreen"),
            (CategorySelectorScreen, "CategorySelectorScreen"),
            (ParsingScreen, "ParsingScreen"),
            (BrowserSettingsScreen, "BrowserSettingsScreen"),
            (ParserSettingsScreen, "ParserSettingsScreen"),
            (OutputSettingsScreen, "OutputSettingsScreen"),
            (CacheViewerScreen, "CacheViewerScreen"),
            (AboutScreen, "AboutScreen"),
        ]

        for screen_class, screen_name in screens:
            screen = screen_class()
            css = screen.CSS

            screen_block = self._extract_css_block(css, f"{screen_name} {{")
            assert "align: center middle" in screen_block, (
                f"{screen_name} должен иметь 'align: center middle'"
            )

    def test_no_fixed_width_without_max_width(self):
        """
        Проверка отсутствия фиксированных ширин без max-width.

        Тест проверяет, что основные КОНТЕЙНЕРЫ с width: 100%
        также имеют max-width для адаптивности.
        Декоративные элементы (.logo, .title, .subtitle) исключаются.
        Вложенные контейнеры с height: 1fr также исключаются.
        """
        screens = [
            MainMenuScreen(),
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
        ]

        # Контейнеры которые должны иметь max-width при width: 100%
        # Только главные контейнеры экранов
        container_selectors = [
            ".menu-container",
            ".logo-container",
            "#city-selector-container",
            "#category-selector-container",
            "#parsing-container",
        ]

        for screen in screens:
            css = screen.CSS

            for selector in container_selectors:
                styles = self._extract_css_block(css, selector)
                if styles and "width: 100%" in styles:
                    assert "max-width:" in styles, (
                        f"{selector} в {screen.__class__.__name__} должен иметь max-width при width: 100%"
                    )

    def test_horizontal_container_for_buttons(self):
        """
        Проверка правильного использования Horizontal контейнеров для кнопок.

        Тест проверяет, что кнопки в рядах используют Horizontal контейнеры.
        """
        screens = [
            CitySelectorScreen(),
            CategorySelectorScreen(),
            ParsingScreen(),
            CacheViewerScreen(),
            AboutScreen(),
        ]

        for screen in screens:
            css = screen.CSS

            # Проверка наличия .button-row с правильным выравниванием
            button_row_styles = self._extract_css_block(css, ".button-row")
            if button_row_styles:
                assert "align: center middle" in button_row_styles, (
                    f".button-row в {screen.__class__.__name__} должен иметь центрирование"
                )

    def _extract_css_block(self, css: str, selector: str) -> str:
        """
        Извлечь блок CSS по селектору.

        Args:
            css: Полный CSS текст
            selector: CSS селектор для поиска

        Returns:
            Строка с CSS правилами внутри блока
        """
        escaped_selector = re.escape(selector.rstrip(" {"))
        pattern = rf"{escaped_selector}\s*\{{([^}}]+)\}}"
        match = re.search(pattern, css)
        if match:
            return match.group(1)
        return ""
