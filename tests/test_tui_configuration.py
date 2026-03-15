#!/usr/bin/env python3
"""
Тесты для проверки конфигурации TUI на pytermgui.

Эти тесты выявляют ошибки конфигурации до запуска приложения:
1. Ошибки в YAML конфигурации стилей
2. Неправильные типы виджетов
3. Отсутствие необходимых импортов
4. Ошибки в путях к файлам данных
5. Ошибки инициализации компонентов TUI

Примечание:
    Тесты требуют установки pytermgui:
    pip install pytermgui

    Если pytermgui не установлен, тесты будут пропущены.
"""

import pytest
from pathlib import Path
import sys

# Добавляем путь к модулю
sys.path.insert(0, str(Path(__file__).parent.parent))

# Проверяем доступность pytermgui
PYTERMGUI_AVAILABLE = False
try:
    import pytermgui as ptg
    PYTERMGUI_AVAILABLE = True
except ImportError:
    pass

# Пропускаем все тесты в этом файле, если pytermgui не установлен
pytestmark = pytest.mark.skipif(
    not PYTERMGUI_AVAILABLE,
    reason="pytermgui не установлен. Установите: pip install pytermgui"
)

# Условные импорты - выполняются только если pytermgui доступен
if PYTERMGUI_AVAILABLE:
    from parser_2gis.tui_pytermgui.styles import get_default_styles
    from parser_2gis.tui_pytermgui.app import TUIApp, Parser2GISTUI


class TestTUIStylesConfiguration:
    """Тесты конфигурации стилей TUI."""

    def test_styles_yaml_valid_format(self):
        """
        Тест 1: Проверка формата YAML конфигурации стилей.
        
        Проверяет, что YAML строка имеет правильную структуру
        с секциями aliases и config, а не неправильную секцию palette.
        """
        styles_yaml = get_default_styles()
        
        # Проверяем наличие секции aliases (правильный формат)
        assert 'aliases:' in styles_yaml, \
            "YAML должен содержать секцию 'aliases:' для определения цветов"
        
        # Проверяем отсутствие неправильной секции config.palette
        assert 'config:\n    palette:' not in styles_yaml, \
            "palette не должен быть вложен в config - это отдельная секция"
        
        # Проверяем наличие основных цветов
        assert 'primary:' in styles_yaml, "Должен быть определен цвет primary"
        assert 'secondary:' in styles_yaml, "Должен быть определен цвет secondary"
        assert 'text:' in styles_yaml, "Должен быть определен цвет text"

    def test_styles_yaml_loadable(self):
        """
        Тест 2: Проверка загрузки YAML конфигурации.
        
        Проверяет, что YAML строка может быть загружена через YamlLoader
        без ошибок KeyError для неизвестных виджетов.
        """
        styles_yaml = get_default_styles()
        
        # Пытаемся загрузить стили - это не должно вызывать исключений
        try:
            with ptg.YamlLoader() as loader:
                loader.load(styles_yaml)
        except KeyError as e:
            pytest.fail(f"YAML содержит неизвестный тип виджета: {e}")
        except Exception as e:
            pytest.fail(f"Ошибка загрузки YAML конфигурации: {e}")

    def test_styles_no_unknown_widgets(self):
        """
        Тест 3: Проверка отсутствия неизвестных виджетов в конфигурации.
        
        Проверяет, что в конфигурации указаны только существующие
        виджеты pytermgui.
        """
        styles_yaml = get_default_styles()
        
        # Список допустимых виджетов pytermgui
        allowed_widgets = {
            'Label', 'InputField', 'Button', 'Window', 'Container',
            'TextBox', 'Table', 'Checkbox', 'ProgressBar', 'Splitter',
            'Collapsible', 'TreeView', 'SelectField', 'DirectoryTree'
        }
        
        # Парсим YAML и проверяем виджеты
        import yaml
        config = yaml.safe_load(styles_yaml)
        
        if config and 'config' in config:
            for widget_name in config['config'].keys():
                # Пропускаем специальные конструкции
                if ' is_' in widget_name or widget_name.startswith('*'):
                    continue
                    
                assert widget_name in allowed_widgets, \
                    f"Неизвестный виджет в конфигурации: {widget_name}. " \
                    f"Допустимые виджеты: {allowed_widgets}"


class TestTUIAppInitialization:
    """Тесты инициализации приложения TUI."""

    def test_tui_app_create(self):
        """
        Тест 4: Проверка создания экземпляра TUIApp.
        
        Проверяет, что приложение может быть создано без ошибок
        и имеет необходимые атрибуты.
        """
        try:
            app = TUIApp()
        except Exception as e:
            pytest.fail(f"Не удалось создать экземпляр TUIApp: {e}")
        
        # Проверяем наличие необходимых атрибутов
        assert hasattr(app, '_config'), "Приложение должно иметь атрибут _config"
        assert hasattr(app, '_state'), "Приложение должно иметь атрибут _state"
        assert hasattr(app, '_running'), "Приложение должно иметь атрибут _running"
        
        # Проверяем начальное состояние
        assert app._running is False, "Приложение должно быть не запущено при создании"

    def test_tui_app_get_cities(self):
        """
        Тест 5: Проверка загрузки списка городов.
        
        Проверяет, что файл cities.json существует и может быть загружен.
        """
        app = TUIApp()
        
        try:
            cities = app.get_cities()
        except FileNotFoundError:
            pytest.fail("Файл cities.json не найден")
        except Exception as e:
            pytest.fail(f"Ошибка при загрузке cities.json: {e}")
        
        # Проверяем что города загружены
        assert isinstance(cities, list), "cities должен быть списком"
        assert len(cities) > 0, "Список городов не должен быть пустым"
        
        # Проверяем структуру первого города
        if len(cities) > 0:
            first_city = cities[0]
            assert 'code' in first_city, "Город должен иметь поле 'code'"
            assert 'name' in first_city, "Город должен иметь поле 'name'"


class TestTUIParser2GISWrapper:
    """Тесты обёртки Parser2GISTUI."""

    def test_parser2gis_tui_create(self):
        """
        Тест 6: Проверка создания Parser2GISTUI.
        
        Проверяет, что обёртка может быть создана без ошибок.
        """
        try:
            app = Parser2GISTUI()
        except Exception as e:
            pytest.fail(f"Не удалось создать экземпляр Parser2GISTUI: {e}")
        
        assert hasattr(app, '_app'), "Parser2GISTUI должен иметь атрибут _app"
        assert isinstance(app._app, TUIApp), "_app должен быть экземпляром TUIApp"


class TestTUIDataFiles:
    """Тесты файлов данных для TUI."""

    def test_categories_available(self):
        """
        Тест 7: Проверка доступности категорий.
        
        Проверяет, что категории 93 доступны и имеют правильную структуру.
        """
        from parser_2gis.data.categories_93 import CATEGORIES_93
        
        assert isinstance(CATEGORIES_93, list), "CATEGORIES_93 должен быть списком"
        assert len(CATEGORIES_93) > 0, "Список категорий не должен быть пустым"
        
        # Проверяем структуру первой категории
        first_category = CATEGORIES_93[0]
        assert 'name' in first_category, "Категория должна иметь поле 'name'"
        assert 'query' in first_category, "Категория должна иметь поле 'query'"
        assert 'rubric_code' in first_category, "Категория должна иметь поле 'rubric_code'"

    def test_cities_file_exists(self):
        """
        Тест 8: Проверка существования файла городов.
        
        Проверяет, что файл cities.json существует по ожидаемому пути.
        """
        cities_path = Path(__file__).parent.parent / 'parser_2gis' / 'data' / 'cities.json'
        
        assert cities_path.exists(), f"Файл городов не найден: {cities_path}"
        assert cities_path.is_file(), f"{cities_path} должен быть файлом, а не директорией"

    def test_cities_file_valid_json(self):
        """
        Тест 9: Проверка валидности JSON файла городов.
        
        Проверяет, что файл cities.json содержит валидный JSON.
        """
        import json
        
        cities_path = Path(__file__).parent.parent / 'parser_2gis' / 'data' / 'cities.json'
        
        try:
            with open(cities_path, 'r', encoding='utf-8') as f:
                cities = json.load(f)
        except json.JSONDecodeError as e:
            pytest.fail(f"cities.json содержит невалидный JSON: {e}")
        
        assert isinstance(cities, list), "cities.json должен содержать список"


# Запуск тестов через pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
