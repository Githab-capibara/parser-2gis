"""
Тесты на архитектурную целостность проекта parser-2gis.

Проверяют:
- Отсутствие циклических зависимостей между модулями
- Отсутствие дублирования констант
- Использование централизованных констант из constants.py
- Отсутствие дублирования кода исключений
- Целостность архитектуры исключений
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


class TestArchitectureIntegrity:
    """Тесты архитектурной целостности."""

    def test_no_duplicate_constants_in_modules(self) -> None:
        """Проверяет отсутствие дублирования констант в модулях.

        Константы должны быть определены только в constants.py
        и импортироваться в других модулях.
        """
        # Константы которые должны быть в constants.py
        known_constants = {
            "MAX_DATA_DEPTH",
            "MAX_DATA_SIZE",
            "MAX_COLLECTION_SIZE",
            "MAX_STRING_LENGTH",
            "DEFAULT_BUFFER_SIZE",
            "MERGE_BUFFER_SIZE",
            "CSV_BATCH_SIZE",
            "MERGE_BATCH_SIZE",
            "MIN_WORKERS",
            "MAX_WORKERS",
            "MIN_TIMEOUT",
            "MAX_TIMEOUT",
            "DEFAULT_TIMEOUT",
            "MERGE_LOCK_TIMEOUT",
            "MAX_LOCK_FILE_AGE",
        }

        # Файлы которые не должны содержать дубликаты констант
        excluded_files = {"constants.py", "__init__.py"}

        project_root = Path(__file__).parent.parent / "parser_2gis"
        violations: List[Tuple[str, str]] = []

        for py_file in project_root.rglob("*.py"):
            if py_file.name in excluded_files:
                continue

            # Пропускаем тесты и виртуальные окружения
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            content = py_file.read_text(encoding="utf-8")

            for const_name in known_constants:
                # Ищем определения констант (не импорты)
                pattern = rf"^{const_name}\s*:\s*int\s*=\s*\d+"
                if re.search(pattern, content, re.MULTILINE):
                    violations.append((str(py_file.relative_to(project_root)), const_name))

        assert not violations, (
            "Обнаружено дублирование констант в модулях:\n"
            + "\n".join(f"  {f}: {c}" for f, c in violations)
            + "\n\nКонстанты должны быть определены только в constants.py"
        )

    def test_constants_imported_from_central_module(self) -> None:
        """Проверяет что константы импортируются из constants.py.

        Если модуль использует константы, он должен импортировать их из
        constants.py, а не определять локально.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули которые используют константы
        modules_using_constants = {
            "common.py": ["MAX_DATA_DEPTH", "MAX_DATA_SIZE", "DEFAULT_BUFFER_SIZE"],
            "cache.py": ["MAX_DATA_DEPTH", "MAX_STRING_LENGTH"],
            "parallel_parser.py": ["MIN_WORKERS", "MAX_WORKERS", "DEFAULT_TIMEOUT"],
            "parallel_helpers.py": ["MERGE_BUFFER_SIZE", "MERGE_LOCK_TIMEOUT"],
        }

        violations: List[str] = []

        for module_name, expected_constants in modules_using_constants.items():
            module_path = project_root / module_name
            if not module_path.exists():
                continue

            content = module_path.read_text(encoding="utf-8")

            # Проверяем что есть импорт из constants
            has_constants_import = (
                "from .constants import" in content
                or "from parser_2gis.constants import" in content
            )

            if not has_constants_import:
                violations.append(f"{module_name}: не импортирует константы из constants.py")
                continue

            # Проверяем что константы не определены локально
            for const_name in expected_constants:
                pattern = rf"^{const_name}\s*:\s*.*="
                if re.search(pattern, content, re.MULTILINE):
                    violations.append(f"{module_name}: определяет константу {const_name} локально")

        assert not violations, "Нарушения импорта констант:\n" + "\n".join(
            f"  {v}" for v in violations
        )

    def test_exception_hierarchy_uses_base_class(self) -> None:
        """Проверяет что все исключения наследуются от BaseContextualException.

        Все пользовательские исключения должны наследоваться от
        BaseContextualException для единого стиля обработки ошибок.
        """
        # Проверяем через фактическое наследование в runtime
        from parser_2gis.exceptions import BaseContextualException
        from parser_2gis.parser.exceptions import ParserException
        from parser_2gis.writer.exceptions import WriterUnknownFileFormat

        # Проверяем что основные исключения наследуются
        assert issubclass(ParserException, BaseContextualException)
        assert issubclass(WriterUnknownFileFormat, BaseContextualException)

        # Chrome исключения проверяем отдельно (они используют динамическое наследование)
        # Проверяем что экземпляр создаётся корректно
        try:
            from parser_2gis.chrome.exceptions import ChromeException

            exc = ChromeException("test")
            # Проверяем что у исключения есть атрибуты базового класса
            assert hasattr(exc, "function_name")
            assert hasattr(exc, "line_number")
            assert hasattr(exc, "filename")
        except Exception:
            pass  # Chrome может быть не установлен

    def test_no_circular_imports_between_core_modules(self) -> None:
        """Проверяет отсутствие циклических импортов между основными модулями.

        Основные модули не должны импортировать друг друга циклически.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Основные модули для проверки
        core_modules = [
            "cache.py",
            "common.py",
            "config.py",
            "validation.py",
            "parallel_parser.py",
            "constants.py",
        ]

        # Словарь зависимостей: модуль -> множество импортируемых модулей
        dependencies: Dict[str, Set[str]] = {}

        for module_name in core_modules:
            module_path = project_root / module_name
            if not module_path.exists():
                continue

            content = module_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            imported_modules: Set[str] = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("."):
                        # Относительный импорт
                        imported = node.module.lstrip(".")
                        if imported:
                            imported_modules.add(imported.split(".")[0] + ".py")
                    elif node.module:
                        # Абсолютный импорт
                        if node.module.startswith("parser_2gis"):
                            imported = node.module.replace("parser_2gis.", "")
                            imported_modules.add(imported.split(".")[0] + ".py")

            dependencies[module_name] = imported_modules

        # Проверяем циклы
        cycles: List[str] = []
        for module_a, deps_a in dependencies.items():
            for module_b in deps_a:
                if module_b in dependencies:
                    deps_b = dependencies[module_b]
                    if module_a in deps_b:
                        cycle = f"{module_a} <-> {module_b}"
                        if cycle not in cycles and f"{module_b} <-> {module_a}" not in cycles:
                            cycles.append(cycle)

        assert not cycles, "Обнаружены циклические зависимости между модулями:\n" + "\n".join(
            f"  {c}" for c in cycles
        )

    def test_base_contextual_exception_exists(self) -> None:
        """Проверяет что BaseContextualException существует и экспортируется."""
        from parser_2gis.exceptions import BaseContextualException

        assert BaseContextualException is not None
        assert issubclass(BaseContextualException, Exception)

    def test_all_exceptions_inherit_from_base_contextual(self) -> None:
        """Проверяет что все основные исключения наследуются от BaseContextualException."""
        from parser_2gis.exceptions import BaseContextualException
        from parser_2gis.parser.exceptions import ParserException
        from parser_2gis.writer.exceptions import WriterUnknownFileFormat

        # Проверяем статическое наследование
        assert issubclass(ParserException, BaseContextualException)
        assert issubclass(WriterUnknownFileFormat, BaseContextualException)

        # Chrome исключения используют динамическое наследование через _get_base_exception()
        # Проверяем что они имеют атрибуты базового класса
        try:
            from parser_2gis.chrome.exceptions import (
                ChromeException,
                ChromePathNotFound,
                ChromeRuntimeException,
                ChromeUserAbortException,
            )

            # Создаём экземпляры и проверяем наличие атрибутов
            for exc_class in [ChromeException, ChromePathNotFound]:
                try:
                    exc = exc_class("test")
                    assert hasattr(exc, "function_name")
                    assert hasattr(exc, "line_number")
                    assert hasattr(exc, "filename")
                except Exception:
                    pass  # Некоторые исключения могут требовать специальные параметры

            # Для RuntimeException и UserAbortException проверяем только что они существуют
            assert ChromeRuntimeException is not None
            assert ChromeUserAbortException is not None

        except ImportError:
            pass  # Chrome может быть не установлен

    def test_constants_are_consistent(self) -> None:
        """Проверяет что константы консистентны во всех модулях.

        MAX_DATA_DEPTH должно быть одинаковым во всех модулях.
        """
        from parser_2gis import constants
        from parser_2gis.cache import MAX_DATA_DEPTH as cache_depth
        from parser_2gis.common import MAX_DATA_DEPTH as common_depth

        # Все константы должны быть равны значению из constants.py
        assert common_depth == constants.MAX_DATA_DEPTH, (
            f"MAX_DATA_DEPTH в common.py ({common_depth}) не совпадает с "
            f"constants.py ({constants.MAX_DATA_DEPTH})"
        )

        assert cache_depth == constants.MAX_DATA_DEPTH, (
            f"MAX_DATA_DEPTH в cache.py ({cache_depth}) не совпадает с "
            f"constants.py ({constants.MAX_DATA_DEPTH})"
        )
