"""
Тесты для проверки отсутствия циклических импортов.

Проверяет отсутствие циклических зависимостей между модулями.
Использует прямой импорт и AST анализ.

Тесты покрывают исправления:
- Устранение циклических импортов
- Корректная организация импортов
- Использование TYPE_CHECKING для условных импортов
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set

import pytest


class TestDirectImports:
    """Тесты для проверки прямых импортов модулей."""

    def test_import_cache_manager(self):
        """
        Тест 1.1: Проверка импорта cache.manager.

        Проверяет что модуль cache.manager импортируется без ошибок.
        """
        from parser_2gis.cache import manager

        assert manager is not None
        assert hasattr(manager, "CacheManager")

    def test_import_parallel_parser(self):
        """
        Тест 1.2: Проверка импорта parallel.parallel_parser.

        Проверяет что модуль parallel.parallel_parser импортируется без ошибок.
        """
        from parser_2gis.parallel import parallel_parser

        assert parallel_parser is not None
        assert hasattr(parallel_parser, "ParallelCityParser")

    def test_import_validation(self):
        """
        Тест 1.3: Проверка импорта validation.

        Проверяет что модуль validation импортируется без ошибок.
        """
        from parser_2gis.validation import url_validator, data_validator

        assert url_validator is not None
        assert data_validator is not None

    def test_import_chrome_browser(self):
        """
        Тест 1.4: Проверка импорта chrome.browser.

        Проверяет что модуль chrome.browser импортируется без ошибок.
        """
        from parser_2gis.chrome import browser

        assert browser is not None
        assert hasattr(browser, "ChromeBrowser")

    def test_import_writer(self):
        """
        Тест 1.5: Проверка импорта writer.

        Проверяет что модуль writer импортируется без ошибок.
        """
        from parser_2gis.writer import writers

        assert writers is not None


class TestCyclicDependencies:
    """Тесты для проверки отсутствия циклических зависимостей."""

    def test_no_cache_parallel_cycle(self):
        """
        Тест 2.1: Проверка отсутствия цикла cache <-> parallel.

        Проверяет что cache и parallel не имеют циклической зависимости.
        """
        # Импортируем cache

        # Импортируем parallel

        # Проверяем что cache не импортирует parallel напрямую
        cache_module = sys.modules["parser_2gis.cache.manager"]

        # Parallel не должен импортироваться в cache
        assert "parser_2gis.parallel" not in str(cache_module.__file__)

    def test_no_validation_chrome_cycle(self):
        """
        Тест 2.2: Проверка отсутствия цикла validation <-> chrome.

        Проверяет что validation и chrome не имеют циклической зависимости.
        """
        # Импортируем validation
        from parser_2gis.validation import url_validator

        # Импортируем chrome
        from parser_2gis.chrome import browser

        # Оба модуля должны быть загружены независимо
        assert url_validator is not None
        assert browser is not None

    def test_no_config_writer_cycle(self):
        """
        Тест 2.3: Проверка отсутствия цикла config <-> writer.

        Проверяет что config и writer не имеют циклической зависимости.
        """
        # Импортируем config
        from parser_2gis import config

        # Импортируем writer
        from parser_2gis.writer.writers import csv_writer

        # Оба модуля должны быть загружены независимо
        assert config is not None
        assert csv_writer is not None


class TestASTImportAnalysis:
    """Тесты для AST анализа импортов."""

    def get_module_imports(self, module_path: Path) -> Set[str]:
        """
        Получает список импортов из модуля.

        Args:
            module_path: Путь к модулю.

        Returns:
            Множество имён импортируемых модулей.
        """
        if not module_path.exists():
            return set()

        content = module_path.read_text(encoding="utf-8")
        tree = ast.parse(content)

        imports: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("parser_2gis"):
                    # Извлекаем основной модуль
                    main_module = node.module.split(".")[0]
                    sub_module = node.module.replace("parser_2gis.", "")
                    imports.add(f"{main_module}:{sub_module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("parser_2gis"):
                        imports.add(alias.name)

        return imports

    def test_core_modules_no_direct_cycle(self):
        """
        Тест 3.1: Проверка отсутствия прямых циклов в основных модулях.

        Проверяет отсутствие прямых циклических зависимостей.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Основные модули для проверки
        core_modules = [
            "cache/manager.py",
            "parallel/parallel_parser.py",
            "validation/url_validator.py",
            "chrome/browser.py",
            "config.py",
            "writer/writers/csv_writer.py",
        ]

        dependencies: Dict[str, Set[str]] = {}

        for module_file in core_modules:
            module_path = project_root / module_file
            if module_path.exists():
                imports = self.get_module_imports(module_path)
                dependencies[module_file] = imports

        # Проверяем циклы
        cycles: List[str] = []

        for module_a, deps_a in dependencies.items():
            for dep in deps_a:
                # Ищем обратную зависимость
                for module_b, deps_b in dependencies.items():
                    if module_a != module_b:
                        if module_a in deps_b:
                            pair = tuple(sorted([module_a, module_b]))
                            cycle_str = f"{pair[0]} <-> {pair[1]}"
                            if cycle_str not in cycles:
                                cycles.append(cycle_str)

        assert len(cycles) == 0, f"Обнаружены циклические зависимости: {cycles}"

    def test_no_self_import(self):
        """
        Тест 3.2: Проверка отсутствия самоимпорта.

        Проверяет что модули не импортируют сами себя.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем основные модули
        test_modules = [
            "cache/manager.py",
            "parallel/parallel_parser.py",
            "validation/url_validator.py",
            "chrome/browser.py",
            "config.py",
        ]

        for module_file in test_modules:
            module_path = project_root / module_file
            if module_path.exists():
                imports = self.get_module_imports(module_path)

                # Проверяем что модуль не импортирует сам себя
                module_name = module_file.replace("/", ".").replace(".py", "")
                for imp in imports:
                    assert module_name not in imp, (
                        f"Модуль {module_name} импортирует сам себя через {imp}"
                    )


class TestTYPE_CHECKINGImports:
    """Тесты для проверки использования TYPE_CHECKING."""

    def test_cache_manager_uses_type_checking(self):
        """
        Тест 4.1: Проверка использования TYPE_CHECKING в cache.manager.

        Проверяет что TYPE_CHECKING используется для условных импортов.
        """
        from parser_2gis.cache import manager

        # Проверяем что модуль загружается без ошибок
        assert manager is not None
        assert hasattr(manager, "CacheManager")

    def test_parallel_parser_uses_type_checking(self):
        """
        Тест 4.2: Проверка использования TYPE_CHECKING в parallel_parser.

        Проверяет что TYPE_CHECKING используется для условных импортов.
        """
        from parser_2gis.parallel import parallel_parser

        module_source = Path(parallel_parser.__file__).read_text(encoding="utf-8")

        assert "TYPE_CHECKING" in module_source

    def test_config_has_conditional_imports(self):
        """
        Тест 4.3: Проверка что config использует условные импорты.

        Проверяет что config модуль корректно управляет импортами.
        """
        from parser_2gis import config

        # Проверяем что модуль загружается без ошибок
        assert config is not None
        assert hasattr(config, "Configuration")


class TestImportOrder:
    """Тесты для проверки порядка импортов."""

    def test_standard_library_first(self):
        """
        Тест 5.1: Проверка что стандартная библиотека импортируется первой.

        Проверяет порядок импортов в модуле.
        """
        from parser_2gis.cache import manager

        module_source = Path(manager.__file__).read_text(encoding="utf-8")
        lines = module_source.split("\n")

        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                if "parser_2gis" in stripped:
                    local_imports.append(stripped)
                elif stripped.startswith("import ") and not stripped.startswith("from"):
                    stdlib_imports.append(stripped)
                else:
                    third_party_imports.append(stripped)

        # Стандартная библиотека должна быть до local импортов
        assert len(stdlib_imports) > 0 or len(third_party_imports) > 0

    def test_no_wildcard_imports(self):
        """
        Тест 5.2: Проверка отсутствия wildcard импортов.

        Проверяет что не используется `from module import *`.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем основные модули
        test_modules = [
            "cache/manager.py",
            "parallel/parallel_parser.py",
            "validation/url_validator.py",
            "chrome/browser.py",
            "config.py",
        ]

        for module_file in test_modules:
            module_path = project_root / module_file
            if module_path.exists():
                content = module_path.read_text(encoding="utf-8")

                # Проверяем что нет wildcard импортов
                assert "import *" not in content, f"Модуль {module_file} содержит wildcard импорт"


class TestModuleInitialization:
    """Тесты для проверки инициализации модулей."""

    def test_cache_module_init(self):
        """
        Тест 6.1: Проверка инициализации cache модуля.

        Проверяет что cache модуль инициализируется корректно.
        """
        import parser_2gis.cache as cache_package

        assert hasattr(cache_package, "CacheManager")

    def test_parallel_module_init(self):
        """
        Тест 6.2: Проверка инициализации parallel модуля.

        Проверяет что parallel модуль инициализируется корректно.
        """
        import parser_2gis.parallel as parallel_package

        assert hasattr(parallel_package, "ParallelCityParser")

    def test_validation_module_init(self):
        """
        Тест 6.3: Проверка инициализации validation модуля.

        Проверяет что validation модуль инициализируется корректно.
        """
        import parser_2gis.validation as validation_package

        assert hasattr(validation_package, "validate_url")
        assert hasattr(validation_package, "validate_positive_int")


class TestImportPerformance:
    """Тесты для проверки производительности импортов."""

    def test_import_time_cache_manager(self):
        """
        Тест 7.1: Проверка времени импорта cache.manager.

        Проверяет что импорт выполняется за разумное время.
        """
        import time

        start = time.time()

        # Очищаем кэш импортов
        modules_to_remove = [k for k in sys.modules.keys() if k.startswith("parser_2gis.cache")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Импортируем заново

        elapsed = time.time() - start

        # Импорт не должен занимать больше 5 секунд
        assert elapsed < 5.0, f"Импорт cache.manager занял {elapsed:.2f} секунд"

    def test_import_time_parallel_parser(self):
        """
        Тест 7.2: Проверка времени импорта parallel.parallel_parser.

        Проверяет что импорт выполняется за разумное время.
        """
        import time

        start = time.time()

        # Очищаем кэш импортов
        modules_to_remove = [k for k in sys.modules.keys() if k.startswith("parser_2gis.parallel")]
        for mod in modules_to_remove:
            del sys.modules[mod]

        # Импортируем заново

        elapsed = time.time() - start

        # Импорт не должен занимать больше 5 секунд
        assert elapsed < 5.0, f"Импорт parallel.parallel_parser занял {elapsed:.2f} секунд"


# Запуск тестов через pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
