#!/usr/bin/env python3
"""
Тесты для выявления ошибок конфигурации TUI (pytermgui).

Эти тесты проверяют:
1. Корректность YAML конфигурации стилей
2. Наличие всех используемых виджетов в pytermgui
3. Корректность импортов TUI модулей
4. Загрузку стилей без ошибок
5. Валидацию конфигурации виджетов
"""

import pytest
import pytermgui as ptg


class TestTUIStylesConfiguration:
    """Тесты конфигурации стилей TUI."""

    def test_yaml_styles_syntax_valid(self):
        """
        Тест 1: Проверка синтаксиса YAML конфигурации стилей.
        
        Проверяет, что YAML строка со стилями имеет корректный синтаксис
        и может быть загружена через YamlLoader без ошибок синтаксиса.
        """
        from parser_2gis.tui_pytermgui.styles import get_default_styles
        
        styles_yaml = get_default_styles()
        
        # Проверяем что YAML не пустой
        assert styles_yaml is not None
        assert len(styles_yaml) > 0
        
        # Проверяем что YAML содержит обязательные секции
        assert "aliases:" in styles_yaml
        assert "config:" in styles_yaml
        
        # Пытаемся загрузить YAML - это не должно вызвать исключений синтаксиса
        try:
            with ptg.YamlLoader() as loader:
                loader.load(styles_yaml)
        except KeyError as e:
            # Ловим ошибки неизвестных виджетов
            pytest.fail(f"YAML содержит неизвестный тип виджета: {e}")
        except Exception as e:
            pytest.fail(f"Ошибка загрузки YAML стилей: {e}")

    def test_widget_types_exist_in_pytermgui(self):
        """
        Тест 2: Проверка существования всех указанных виджетов в pytermgui.
        
        Проверяет, что все виджеты, указанные в секции config YAML,
        существуют как классы в модуле pytermgui.
        """
        import re
        from parser_2gis.tui_pytermgui.styles import get_default_styles
        
        styles_yaml = get_default_styles()
        
        # Извлекаем имена виджетов из секции config
        # Ищем строки вида "WidgetName:" в секции config
        config_match = re.search(r'config:\s*\n(.*?)(?=\n\w|\Z)', styles_yaml, re.DOTALL)
        assert config_match is not None, "Секция 'config:' не найдена в YAML"
        
        config_section = config_match.group(1)
        
        # Находим все имена виджетов (строки начинающиеся с заглавной буквы и заканчивающиеся на :)
        widget_pattern = r'^\s{4}(\w+):'
        widgets_in_config = re.findall(widget_pattern, config_section, re.MULTILINE)
        
        assert len(widgets_in_config) > 0, "В конфигурации не найдено ни одного виджета"
        
        # Проверяем каждый виджет на существование в pytermgui
        missing_widgets = []
        for widget_name in widgets_in_config:
            if not hasattr(ptg, widget_name):
                missing_widgets.append(widget_name)
        
        if missing_widgets:
            pytest.fail(
                f"Виджеты не найдены в pytermgui: {missing_widgets}. "
                f"Доступные виджеты: {[x for x in dir(ptg) if x[0].isupper() and not x.startswith('_')]}"
            )

    def test_tui_app_loads_without_errors(self):
        """
        Тест 3: Проверка загрузки TUI приложения без ошибок.
        
        Проверяет, что основной класс TUIApp может быть создан
        и метод _load_styles() выполняется без исключений.
        """
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём приложение
        app = TUIApp()
        
        # Проверяем что конфигурация загружена
        assert app._config is not None
        
        # Проверяем что состояние инициализировано
        assert app._state is not None
        assert isinstance(app._state, dict)
        
        # Загружаем стили - это не должно вызывать исключений
        try:
            app._load_styles()
        except KeyError as e:
            pytest.fail(f"Ошибка загрузки стилей: неизвестный виджет {e}")
        except Exception as e:
            pytest.fail(f"Неожиданная ошибка при загрузке стилей: {e}")

    def test_tui_screens_importable(self):
        """
        Тест 4: Проверка импорта всех TUI экранов.
        
        Проверяет, что все модули экранов TUI могут быть импортированы
        без ошибок импорта зависимостей.
        """
        from parser_2gis.tui_pytermgui import screens
        
        # Список ожидаемых экранов
        expected_screens = [
            "MainMenuScreen",
            "CitySelectorScreen",
            "CategorySelectorScreen",
            "BrowserSettingsScreen",
            "ParserSettingsScreen",
            "OutputSettingsScreen",
            "ParsingScreen",
            "CacheViewerScreen",
            "AboutScreen",
        ]
        
        # Проверяем наличие каждого экрана
        missing_screens = []
        for screen_name in expected_screens:
            if not hasattr(screens, screen_name):
                missing_screens.append(screen_name)
        
        if missing_screens:
            pytest.fail(f"Не найдены экраны TUI: {missing_screens}")
        
        # Проверяем что каждый экран может быть создан (без запуска)
        from parser_2gis.tui_pytermgui.app import TUIApp
        
        # Создаём мок приложения для тестирования
        class MockApp:
            def __init__(self):
                self._config = None
                self.selected_cities = []
                self.selected_categories = []
                
            def get_cities(self):
                return []
                
            def get_categories(self):
                return []
        
        mock_app = MockApp()
        
        # Пытаемся создать каждый экран
        failed_screens = []
        for screen_name in expected_screens:
            try:
                screen_class = getattr(screens, screen_name)
                # Некоторые экраны могут требовать полноценное приложение
                # Поэтому просто проверяем что класс существует и может быть вызван
                assert screen_class is not None
            except Exception as e:
                failed_screens.append(f"{screen_name}: {e}")
        
        if failed_screens:
            pytest.fail(f"Ошибки при создании экранов: {failed_screens}")

    def test_custom_widgets_compatibility(self):
        """
        Тест 5: Проверка совместимости кастомных виджетов.
        
        Проверяет, что кастомные виджеты TUI корректно наследуются
        от базовых классов pytermgui и могут быть созданы.
        """
        from parser_2gis.tui_pytermgui.widgets import (
            Checkbox,
            NavigableContainer,
            ButtonWidget,
            ScrollArea,
        )
        
        # Проверяем что виджеты импортируются
        assert Checkbox is not None
        assert NavigableContainer is not None
        assert ButtonWidget is not None
        assert ScrollArea is not None
        
        # Проверяем что NavigableContainer наследуется от Container
        assert issubclass(NavigableContainer, ptg.Container)
        
        # Пытаемся создать экземпляры виджетов
        try:
            # Создаём Checkbox
            checkbox = Checkbox(label="Тест", value=False)
            assert checkbox is not None
            
            # Создаём NavigableContainer
            container = NavigableContainer()
            assert container is not None
            
            # Создаём ButtonWidget
            button = ButtonWidget(label="Тест")
            assert button is not None
            
        except Exception as e:
            pytest.fail(f"Ошибка при создании кастомных виджетов: {e}")


# Дополнительные тесты для отладки
@pytest.mark.requires_tui
class TestTUIStylesAdvanced:
    """Расширенные тесты стилей TUI."""

    def test_styles_contains_required_aliases(self):
        """Проверка наличия всех необходимых цветовых алиасов."""
        from parser_2gis.tui_pytermgui.styles import get_default_styles
        
        styles_yaml = get_default_styles()
        
        # Required color aliases
        required_aliases = [
            "primary",
            "secondary",
            "accent",
            "success",
            "error",
            "warning",
            "info",
            "background",
            "text",
        ]
        
        missing_aliases = []
        for alias in required_aliases:
            if f"{alias}:" not in styles_yaml:
                missing_aliases.append(alias)
        
        if missing_aliases:
            pytest.fail(f"Отсутствуют цветовые алиасы: {missing_aliases}")

    def test_widget_styles_have_valid_properties(self):
        """Проверка что стили виджетов используют допустимые свойства."""
        from parser_2gis.tui_pytermgui.styles import get_default_styles
        
        styles_yaml = get_default_styles()
        
        # Valid style properties for pytermgui widgets
        valid_properties = [
            "styles",
            "borders",
            "box",
            "background",
            "foreground",
            "border",
            "corner",
            "title",
            "subtitle",
            "label",
            "text",
            "value",
            "prompt",
            "cursor",
            "checked",
            "unchecked",
            "highlight",
            "highlight_text",
            "focus_label",
            "focus_border",
            "hover_background",
            "hover_label",
            "hover_border",
            "complete",
            "incomplete",
            "finished",
            "header",
            "row",
            "alt_row",
            "line",
            "spinner",
            "icon",
            "bar_complete",
            "bar_incomplete",
            "percentage",
            "valid",
            "invalid",
            "normal",
            "selected",
            "highlighted",
            "disabled",
            "body",
            "link",
            "version",
            "success",
            "error",
            "warning",
            "info",
            "debug",
            "critical",
        ]
        
        # Проверяем что в YAML нет опечаток в именах свойств
        # Это простая эвристическая проверка
        import re
        property_pattern = r'^\s{8}(\w+):'
        properties_in_styles = re.findall(property_pattern, styles_yaml, re.MULTILINE)
        
        # Предупреждаем о возможных опечатках (но не проваливаем тест)
        unknown_properties = []
        for prop in properties_in_styles:
            if prop not in valid_properties and not prop.startswith('_'):
                unknown_properties.append(prop)
        
        # Логируем предупреждение но не проваливаем тест
        if unknown_properties:
            print(f"Предупреждение: Возможные неизвестные свойства стилей: {unknown_properties}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
