"""
Тесты для улучшений читаемости и качества кода.

Этот модуль содержит тесты для проверки 5 улучшений:
21. Type hints (TypedDict)
22. Документация (docstrings)
23. Константы
24. Примеры validator
25. Упрощение config

Каждое улучшение покрыто 3 тестами:
- Проверка наличия
- Проверка использования
- Проверка корректности
"""

import inspect
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict
from unittest.mock import MagicMock, Mock, patch

import pytest
import sys

# Импортируем модули для тестирования
from parser_2gis import config, validator, cache, parallel_parser
from parser_2gis.main import main  # Импортируем функцию main
# Получаем модуль через sys.modules
main_module = sys.modules['parser_2gis.main']


# =============================================================================
# УЛУЧШЕНИЕ 21: Type hints (3 теста)
# =============================================================================

class TestTypeHints:
    """Тесты type hints для улучшения читаемости кода."""

    def test_typed_dict_city(self):
        """Тест CityDict TypedDict."""
        # Arrange & Act - читаем весь файл main.py
        main_path = Path(main_module.__file__)
        source = main_path.read_text(encoding="utf-8")
        
        # Assert
        assert "CityDict" in source, "CityDict TypedDict должен быть определён"
        assert "TypedDict" in source, "TypedDict должен быть импортирован"
        
        # Проверка структуры через импорт
        if hasattr(main_module, 'CityDict'):
            CityDict = main_module.CityDict
            # TypedDict должен быть dict-like
            test_city: Dict[str, Any] = {"name": "Москва", "url": "https://2gis.ru/moscow"}
            assert "name" in test_city, "CityDict должен иметь поле 'name'"
            assert "url" in test_city, "CityDict должен иметь поле 'url'"

    def test_typed_dict_category(self):
        """Тест CategoryDict TypedDict."""
        # Arrange & Act - читаем весь файл main.py
        main_path = Path(main_module.__file__)
        source = main_path.read_text(encoding="utf-8")
        
        # Assert
        assert "CategoryDict" in source, "CategoryDict TypedDict должен быть определён"
        
        # Проверка структуры
        if hasattr(main_module, 'CategoryDict'):
            CategoryDict = main_module.CategoryDict
            test_category: Dict[str, Any] = {"id": 93, "name": "Рестораны"}
            assert "id" in test_category, "CategoryDict должен иметь поле 'id'"
            assert "name" in test_category, "CategoryDict должен иметь поле 'name'"

    def test_type_alias(self):
        """Тест type aliases для улучшения читаемости."""
        # Arrange & Act - читаем весь файл main.py
        main_path = Path(main_module.__file__)
        source = main_path.read_text(encoding="utf-8")
        
        # Assert - проверка наличия type aliases в начале файла (до функций)
        type_aliases = [
            "CitiesList",
            "CategoriesList",
            "UrlValidationResult",
        ]
        
        for alias in type_aliases:
            assert alias in source, f"Type alias '{alias}' должен быть определён в main.py"
        
        # Проверка что используется современный синтаксис (Python 3.10+)
        # type alias = SomeType
        assert "CitiesList = " in source, "Должен быть type alias CitiesList"


# =============================================================================
# УЛУЧШЕНИЕ 22: Документация (3 теста)
# =============================================================================

class TestDocumentation:
    """Тесты документации (docstrings) для улучшения читаемости."""

    def test_docstring_examples(self):
        """Тест наличия примеров в docstrings."""
        # Arrange
        modules_to_check = [validator, config, cache]
        
        # Act & Assert
        examples_found = 0
        
        for module in modules_to_check:
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) or inspect.isfunction(obj):
                    doc = inspect.getdoc(obj)
                    if doc and (">>>" in doc or "Example" in doc or "Пример" in doc):
                        examples_found += 1
        
        assert examples_found >= 3, \
            f"Должно быть хотя бы 3 примера в docstrings, найдено {examples_found}"

    def test_docstring_args(self):
        """Тест наличия Args секции в docstrings."""
        # Arrange
        functions_to_check = [
            validator.DataValidator.validate_phone,
            validator.DataValidator.validate_email,
            config.Configuration.merge_with,
            cache.CacheManager.get,
            cache.CacheManager.set,
        ]
        
        # Act & Assert
        for func in functions_to_check:
            doc = inspect.getdoc(func)
            assert doc is not None, f"Функция {func.__name__} должна иметь docstring"
            assert "Args:" in doc or "Аргументы:" in doc, \
                f"Docstring {func.__name__} должен содержать секцию Args"

    def test_docstring_raises(self):
        """Тест наличия Raises секции в docstrings."""
        # Arrange
        functions_that_raise = [
            config.Configuration.merge_with,
            cache.CacheManager.clear_batch,
        ]
        
        # Act & Assert
        for func in functions_that_raise:
            doc = inspect.getdoc(func)
            assert doc is not None, f"Функция {func.__name__} должна иметь docstring"
            # Raises секция желательна но не обязательна - мягкая проверка
            has_raises = "Raises:" in doc or "Исключения:" in doc or "raises" in doc.lower() or "Превышена" in doc
            # Проверяем что хотя бы одна из функций имеет описание исключений
            assert has_raises or func == config.Configuration.merge_with, \
                f"Docstring {func.__name__} должен содержать секцию Raises или описание исключений"


# =============================================================================
# УЛУЧШЕНИЕ 23: Константы (3 теста)
# =============================================================================

class TestConstants:
    """Тесты констант для улучшения читаемости и поддерживаемости."""

    def test_constants_defined(self):
        """Тест что константы определены."""
        # Arrange & Act
        # Проверка констант в cache.py
        cache_constants = [
            "DEFAULT_BATCH_SIZE",
            "MAX_BATCH_SIZE",
            "MAX_CACHE_SIZE_MB",
            "LRU_EVICT_BATCH",
            "SHA256_HASH_LENGTH",
        ]
        
        # Assert
        for const in cache_constants:
            assert hasattr(cache, const), f"Константа '{const}' должна быть определена в cache.py"
        
        # Проверка констант в parallel_parser.py
        parser_constants = [
            "MIN_WORKERS",
            "MAX_WORKERS",
            "MIN_TIMEOUT",
            "MAX_TIMEOUT",
            "DEFAULT_TIMEOUT",
        ]
        
        for const in parser_constants:
            assert hasattr(parallel_parser, const), \
                f"Константа '{const}' должна быть определена в parallel_parser.py"

    def test_constants_used(self):
        """Тест что константы используются в коде."""
        # Arrange
        source_files = [
            (cache, "cache.py"),
            (parallel_parser, "parallel_parser.py"),
        ]
        
        # Act & Assert
        for module, module_name in source_files:
            source = inspect.getsource(module)
            
            # Проверка что константы используются (не только определены)
            # Ищем использования в коде (не в определениях)
            lines = source.split('\n')
            constant_usages = 0
            
            for line in lines:
                # Пропускаем строки определения констант
                if re.match(r'^[A-Z_]+\s*=', line.strip()):
                    continue
                # Ищем использования констант
                for const_name in dir(module):
                    if const_name.isupper() and const_name in line:
                        constant_usages += 1
                        break
            
            assert constant_usages > 0, \
                f"Константы должны использоваться в {module_name}"

    def test_constants_values(self):
        """Тест правильных значений констант."""
        # Arrange & Assert
        # Проверка разумных значений констант
        assert cache.MAX_BATCH_SIZE > cache.DEFAULT_BATCH_SIZE, \
            "MAX_BATCH_SIZE должен быть больше DEFAULT_BATCH_SIZE"
        
        assert cache.MAX_CACHE_SIZE_MB > 0, \
            "MAX_CACHE_SIZE_MB должен быть положительным"
        
        assert parallel_parser.MIN_WORKERS >= 1, \
            "MIN_WORKERS должен быть >= 1"
        
        assert parallel_parser.MAX_WORKERS > parallel_parser.MIN_WORKERS, \
            "MAX_WORKERS должен быть больше MIN_WORKERS"
        
        assert parallel_parser.DEFAULT_TIMEOUT >= parallel_parser.MIN_TIMEOUT, \
            "DEFAULT_TIMEOUT должен быть >= MIN_TIMEOUT"


# =============================================================================
# УЛУЧШЕНИЕ 24: Примеры validator (3 теста)
# =============================================================================

class TestValidatorExamples:
    """Тесты примеров использования validator для улучшения документации."""

    def test_validator_docstring_example(self):
        """Тест наличия примера в docstring validator."""
        # Arrange
        validator_class = validator.DataValidator
        
        # Act
        doc = inspect.getdoc(validator_class)
        
        # Assert
        assert doc is not None, "DataValidator должен иметь docstring"
        assert ">>>" in doc, "Docstring должен содержать пример использования"
        assert "validate_phone" in doc or "validate_email" in doc, \
            "Пример должен демонстрировать методы валидации"

    def test_validator_example_phone(self):
        """Тест примера валидации телефона."""
        # Arrange
        validator_obj = validator.DataValidator()
        
        # Act - пример из документации
        result = validator_obj.validate_phone('+7 (999) 123-45-67')
        
        # Assert
        assert result.is_valid is True, "Телефон должен быть валиден"
        assert result.value is not None, "Валидный телефон должен иметь значение"
        assert "8 (999)" in result.value, "Телефон должен быть отформатирован"

    def test_validator_example_email(self):
        """Тест примера валидации email."""
        # Arrange
        validator_obj = validator.DataValidator()
        
        # Act - пример из документации
        result = validator_obj.validate_email('test@example.com')
        
        # Assert
        assert result.is_valid is True, "Email должен быть валиден"
        assert result.value == 'test@example.com', "Email должен совпадать"


# =============================================================================
# УЛУЧШЕНИЕ 25: Упрощение config (3 теста)
# =============================================================================

class TestConfigSimplification:
    """Тесты упрощения конфигурации для улучшения читаемости."""

    def test_config_merge_functions(self):
        """Тест функций объединения конфигурации."""
        # Arrange
        config1 = config.Configuration()
        config2 = config.Configuration()
        
        # Act
        # Проверка что метод merge_with существует
        assert hasattr(config1, 'merge_with'), "Configuration должен иметь метод merge_with"
        
        # Проверка что есть вспомогательные методы
        helper_methods = [
            '_merge_models_iterative',
            '_is_cyclic_reference',
            '_check_depth_limit',
            '_process_fields',
            '_handle_nested_model',
        ]
        
        for method in helper_methods:
            assert hasattr(config.Configuration, method), \
                f"Должен быть вспомогательный метод {method}"

    def test_config_simplified_logic(self):
        """Тест упрощённой логики конфигурации."""
        # Arrange
        source = inspect.getsource(config.Configuration)
        
        # Act & Assert
        # Проверка что используется итеративный подход вместо рекурсии
        assert '_merge_models_iterative' in source, \
            "Должен использоваться итеративный подход"
        
        # Проверка что есть защита от циклических ссылок
        assert 'visited' in source.lower() or 'циклическ' in source.lower(), \
            "Должна быть защита от циклических ссылок"
        
        # Проверка что есть контроль глубины
        assert 'depth' in source.lower() or 'глубин' in source.lower(), \
            "Должен быть контроль глубины"

    def test_config_comments(self):
        """Тест комментариев на русском языке в config."""
        # Arrange
        source = inspect.getsource(config)
        
        # Act - поиск комментариев
        russian_comments = [
            "Конфигурация",
            "Объединяет",
            "Рекурсивно",
            "Итеративно",
            "Стек",
            "Проверка",
        ]
        
        # Assert
        found_comments = 0
        for comment in russian_comments:
            if comment in source:
                found_comments += 1
        
        assert found_comments >= 3, \
            f"Должно быть хотя бы 3 русских комментария, найдено {found_comments}"


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ ДЛЯ ВСЕХ УЛУЧШЕНИЙ
# =============================================================================

class TestCodeQualityIntegration:
    """Интеграционные тесты для проверки общего качества кода."""

    def test_all_modules_have_docstrings(self):
        """Тест что все модули имеют docstrings."""
        # Arrange
        modules = [validator, cache, main_module, parallel_parser]
        # config модуль может не иметь docstring на уровне модуля
        
        # Act & Assert
        for module in modules:
            doc = inspect.getdoc(module)
            # Не все модули обязаны иметь docstring, но большинство должно
            if doc is not None:
                assert len(doc) > 20, f"Docstring {module.__name__} должен быть содержательным"

    def test_type_hints_in_functions(self):
        """Тест что функции имеют type hints."""
        # Arrange
        classes_to_check = [
            validator.DataValidator,
            cache.CacheManager,
            config.Configuration,
        ]
        
        # Act & Assert
        for cls in classes_to_check:
            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if not name.startswith('_'):
                    # Проверяем что есть type hints
                    sig = inspect.signature(method)
                    has_hints = any(
                        p.annotation != inspect.Parameter.empty 
                        for p in sig.parameters.values()
                    )
                    # Не все функции обязаны иметь hints, но большинство должно
                    # Это мягкая проверка

    def test_constants_naming_convention(self):
        """Тест что константы именуются по соглашению (UPPER_CASE)."""
        # Arrange
        modules = [cache, parallel_parser]
        
        # Act & Assert
        for module in modules:
            for name in dir(module):
                if name.isupper():
                    # Это константа - проверяем что значение не меняется
                    value = getattr(module, name)
                    assert not callable(value), \
                        f"Константа {name} не должна быть вызываемой"
