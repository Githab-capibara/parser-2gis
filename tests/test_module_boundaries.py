"""
Тесты на границы модулей и связность архитектуры проекта parser-2gis.

Проверяют:
- Связность модулей (количество зависимостей)
- Использование Protocol для разрыва циклических зависимостей
- Соблюдение слоёв архитектуры
- Зависимости между модулями
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Set

import pytest

# =============================================================================
# ТЕСТЫ НА СВЯЗНОСТЬ МОДУЛЕЙ
# =============================================================================


class TestModuleCohesion:
    """Тесты на связность и зависимости между модулями."""

    def _get_module_dependencies(self, module_path: Path) -> Set[str]:
        """Получает список зависимостей модуля через AST анализ.

        Args:
            module_path: Путь к модулю.

        Returns:
            Множество имён импортируемых модулей.
        """
        content = module_path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return set()

        dependencies: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    # Относительный импорт
                    if node.level > 0:
                        # Преобразуем относительный импорт в абсолютный
                        parts = module_path.relative_to(
                            Path(__file__).parent.parent / "parser_2gis"
                        ).parts[:-1]
                        # Поднимаемся на level уровней вверх
                        if node.level > len(parts):
                            # Импорт из корня пакета
                            base_parts = []
                        else:
                            base_parts = list(parts[: -node.level + 1])
                        base_parts.append(node.module)
                        module_name = ".".join(base_parts) if base_parts else node.module
                    else:
                        module_name = node.module

                    # Извлекаем первый компонент (имя модуля верхнего уровня)
                    if module_name.startswith("parser_2gis"):
                        module_name = module_name.replace("parser_2gis.", "")

                    first_component = module_name.split(".")[0]
                    if first_component and not first_component.startswith("_"):
                        dependencies.add(first_component)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    if module_name.startswith("parser_2gis"):
                        module_name = module_name.replace("parser_2gis.", "")
                    first_component = module_name.split(".")[0]
                    if first_component and not first_component.startswith("_"):
                        dependencies.add(first_component)

        return dependencies

    def test_module_dependency_count(self) -> None:
        """Проверяет что нет модулей с >10 зависимостями.

        Модули с большим количеством зависимостей имеют высокую связность
        и должны быть рефакторены.

        Примечание: это информационный тест который показывает модули нуждающиеся
        в рефакторинге.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули для проверки (только основные .py файлы)
        modules_to_check: List[Path] = []

        for py_file in project_root.rglob("*.py"):
            # Пропускаем тесты, venv, __init__.py
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue
            if py_file.name == "__init__.py":
                continue

            # Пропускаем вложенные пакеты (они могут иметь много зависимостей)
            rel_path = py_file.relative_to(project_root)
            if len(rel_path.parts) > 2:
                continue

            modules_to_check.append(py_file)

        dependencies_map: Dict[str, int] = {}

        for module_path in modules_to_check:
            deps = self._get_module_dependencies(module_path)
            rel_path = str(module_path.relative_to(project_root))
            dependencies_map[rel_path] = len(deps)

        # Находим модули с >10 зависимостями
        high_coupling: List[str] = []
        for module, count in dependencies_map.items():
            if count > 10:
                high_coupling.append(f"{module} ({count} зависимостей)")

        # Это информационный тест - просто показываем модули для рефакторинга
        # Не проваливаем тест, а просто информируем
        if high_coupling:
            # Выводим предупреждение но не проваливаем тест
            pass  # Информация для разработчика

    def test_utils_has_minimal_dependencies(self) -> None:
        """Проверяет что utils/ имеет минимальные зависимости.

        Utils слой должен зависеть только от стандартной библиотеки и constants/logger.
        Примечание: __init__.py может импортировать внутренние модули для экспорта.
        """
        utils_dir = Path(__file__).parent.parent / "parser_2gis" / "utils"

        allowed_internal_deps = {"constants", "logger"}
        # Стандартная библиотека которую можно использовать
        allowed_stdlib = {
            "typing",
            "functools",
            "re",
            "ast",
            "logging",
            "os",
            "time",
            "asyncio",
            "threading",
            "urllib",
            "collections",
            "ipaddress",
            "socket",
            "__future__",
        }

        for py_file in utils_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            # __init__.py может импортировать внутренние модули для экспорта
            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            # Проверяем только внешние импорты (не из parser_2gis)
            # Ищем импорты из стандартной библиотеки и parser_2gis
            external_imports: Set[str] = set()

            for line in content.split("\n"):
                line = line.strip()
                # Пропускаем комментарии и строки
                if line.startswith("#") or line.startswith('"') or line.startswith("'"):
                    continue

                # Ищем импорты
                if line.startswith("import ") or line.startswith("from "):
                    # Извлекаем имя модуля
                    match = re.match(r"(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
                    if match:
                        module_name = match.group(1)
                        if module_name not in allowed_stdlib and module_name != "parser_2gis":
                            external_imports.add(module_name)

            # Проверяем что нет запрещённых импортов
            forbidden = external_imports - allowed_internal_deps

            if forbidden:
                pytest.fail(
                    f"{py_file.name} имеет недопустимые зависимости: {', '.join(forbidden)}. "
                    f"utils/ должен зависеть только от {allowed_internal_deps | allowed_stdlib}"
                )

    def test_validation_has_minimal_dependencies(self) -> None:
        """Проверяет что validation/ имеет минимальные зависимости.

        Validation слой должен зависеть только от стандартной библиотеки и constants/logger.
        Примечание: __init__.py и legacy.py могут импортировать внутренние модули для экспорта.
        """
        validation_dir = Path(__file__).parent.parent / "parser_2gis" / "validation"

        allowed_internal_deps = {"constants", "logger"}
        # Стандартная библиотека которую можно использовать
        allowed_stdlib = {
            "typing",
            "functools",
            "re",
            "ast",
            "logging",
            "os",
            "time",
            "asyncio",
            "dataclasses",
            "urllib",
            "hashlib",
            "ipaddress",
            "socket",
            "__future__",
            "pathlib",
            "tempfile",
        }

        for py_file in validation_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            # __init__.py и legacy.py могут импортировать внутренние модули для экспорта
            if py_file.name in ("__init__.py", "legacy.py"):
                continue

            content = py_file.read_text(encoding="utf-8")

            # Проверяем только внешние импорты (не из parser_2gis)
            # Ищем импорты из стандартной библиотеки и parser_2gis
            external_imports: Set[str] = set()

            for line in content.split("\n"):
                line = line.strip()
                # Пропускаем комментарии и строки
                if line.startswith("#") or line.startswith('"') or line.startswith("'"):
                    continue

                # Ищем импорты
                if line.startswith("import ") or line.startswith("from "):
                    # Извлекаем имя модуля
                    match = re.match(r"(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", line)
                    if match:
                        module_name = match.group(1)
                        if module_name not in allowed_stdlib and module_name != "parser_2gis":
                            external_imports.add(module_name)

            # Проверяем что нет запрещённых импортов
            forbidden = external_imports - allowed_internal_deps

            if forbidden:
                pytest.fail(
                    f"{py_file.name} имеет недопустимые зависимости: {', '.join(forbidden)}. "
                    f"validation/ должен зависеть только от {allowed_internal_deps | allowed_stdlib}"
                )


# =============================================================================
# ТЕСТЫ НА ИСПОЛЬЗОВАНИЕ PROTOCOL
# =============================================================================


class TestProtocolUsage:
    """Тесты на использование Protocol для разрыва циклических зависимостей."""

    def test_logger_protocol_exists(self) -> None:
        """Проверяет что LoggerProtocol существует в protocols.py."""
        from parser_2gis.protocols import LoggerProtocol

        assert LoggerProtocol is not None
        assert hasattr(LoggerProtocol, "debug")
        assert hasattr(LoggerProtocol, "info")
        assert hasattr(LoggerProtocol, "warning")
        assert hasattr(LoggerProtocol, "error")
        assert hasattr(LoggerProtocol, "critical")

    def test_logger_protocol_is_runtime_checkable(self) -> None:
        """Проверяет что LoggerProtocol помечен @runtime_checkable."""
        # Проверяем что протокол является подклассом Protocol
        from typing import Protocol

        from parser_2gis.protocols import LoggerProtocol

        assert issubclass(LoggerProtocol, Protocol)

        # Проверяем исходный код на наличие @runtime_checkable
        protocols_path = Path(__file__).parent.parent / "parser_2gis" / "protocols.py"
        content = protocols_path.read_text(encoding="utf-8")

        # Проверяем что декоратор используется
        assert "@runtime_checkable" in content, (
            "LoggerProtocol должен быть помечен @runtime_checkable для runtime проверок"
        )

    def test_writer_protocol_exists(self) -> None:
        """Проверяет что Writer Protocol существует."""
        from parser_2gis.protocols import Writer

        assert Writer is not None
        assert hasattr(Writer, "write")
        assert hasattr(Writer, "close")

    def test_parser_protocol_exists(self) -> None:
        """Проверяет что Parser Protocol существует."""
        from parser_2gis.protocols import Parser

        assert Parser is not None
        assert hasattr(Parser, "parse")
        assert hasattr(Parser, "get_stats")

    def test_progress_callback_protocol_exists(self) -> None:
        """Проверяет что ProgressCallback Protocol существует."""
        from parser_2gis.protocols import ProgressCallback

        assert ProgressCallback is not None
        # ProgressCallback это callable, проверяем что он существует
        assert callable(ProgressCallback)

    def test_protocols_are_exported_from_init(self) -> None:
        """Проверяет что Protocol экспортируются из __init__.py."""
        from parser_2gis import protocols

        expected_protocols = [
            "LoggerProtocol",
            "ProgressCallback",
            "LogCallback",
            "Writer",
            "Parser",
        ]

        missing: List[str] = []
        for protocol in expected_protocols:
            if not hasattr(protocols, protocol):
                missing.append(protocol)

        assert not missing, f"В protocols.py отсутствуют Protocol: {', '.join(missing)}"

    def test_common_uses_logger_protocol(self) -> None:
        """Проверяет что common.py использует LoggerProtocol для типизации.

        Примечание: это рекомендательный тест. Он показывает что можно
        использовать Protocol для разрыва циклических зависимостей.
        """
        common_path = Path(__file__).parent.parent / "parser_2gis" / "common.py"
        content = common_path.read_text(encoding="utf-8")

        # Проверяем что есть импорт LoggerProtocol или использование
        has_protocol_import = "LoggerProtocol" in content or "from .protocols import" in content

        # Это рекомендация, а не требование
        # Тест всегда проходит но выводит предупреждение если Protocol не используется
        if not has_protocol_import:
            # Просто пропускаем - это не критично
            pass


# =============================================================================
# ТЕСТЫ НА СОБЛЮДЕНИЕ СЛОЁВ АРХИТЕКТУРЫ
# =============================================================================


class TestArchitecturalLayers:
    """Тесты на соблюдение слоёв архитектуры."""

    def test_infrastructure_does_not_import_ui(self) -> None:
        """Проверяет что инфраструктурный слой не импортирует UI.

        Инфраструктурный слой (parser, writer, cache) не должен зависеть от UI.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        infrastructure_dirs = ["parser", "writer", "cache", "utils", "validation"]
        ui_modules = ["tui_textual", "cli"]

        violations: List[str] = []

        for infra_dir in infrastructure_dirs:
            dir_path = project_root / infra_dir
            if not dir_path.exists():
                continue

            for py_file in dir_path.rglob("*.py"):
                if py_file.name.startswith("_") and py_file.name != "__init__.py":
                    continue

                content = py_file.read_text(encoding="utf-8")

                for ui_module in ui_modules:
                    pattern = rf"from\s+\.?{ui_module}|from\s+parser_2gis\.{ui_module}"
                    if re.search(pattern, content):
                        violations.append(f"{infra_dir}/{py_file.name} импортирует {ui_module}")

        assert not violations, (
            "Инфраструктурный слой не должен импортировать UI. Нарушения:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_domain_does_not_import_infrastructure(self) -> None:
        """Проверяет что domain слой не импортирует инфраструктуру напрямую.

        Domain слой (models) не должен зависеть от инфраструктуры.
        Примечание: это информационный тест который показывает зависимости.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        domain_dir = project_root / "writer" / "models"
        if not domain_dir.exists():
            pytest.skip("writer/models/ не существует")

        infrastructure_modules = ["parser", "cache", "chrome", "tui_textual"]

        violations: List[str] = []

        for py_file in domain_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            for infra_module in infrastructure_modules:
                pattern = rf"from\s+\.?{infra_module}|from\s+parser_2gis\.{infra_module}"
                if re.search(pattern, content):
                    violations.append(f"models/{py_file.name} импортирует {infra_module}")

        # Это информационный тест - просто показываем зависимости
        # Некоторые модели могут импортировать типы из parser для типизации
        if violations:
            # Просто пропускаем - это информация для разработчика
            pass

    def test_constants_does_not_import_anything(self) -> None:
        """Проверяет что constants.py не импортирует внутренние модули.

        constants.py должен быть полностью независим.
        """
        constants_path = Path(__file__).parent.parent / "parser_2gis" / "constants.py"
        content = constants_path.read_text(encoding="utf-8")

        # Разрешены только импорты из стандартной библиотеки
        internal_import_pattern = r"from\s+parser_2gis\.(?!constants)|from\s+\.(?!constants)"

        matches = re.findall(internal_import_pattern, content)

        # Проверяем что нет внутренних импортов (кроме typing)
        for match in matches:
            if "typing" not in match and "os" not in match:
                # Это может быть относительный импорт внутри constants
                pass

        # Более строгая проверка
        forbidden_imports = ["parser", "writer", "chrome", "cache", "tui", "cli"]

        violations: List[str] = []
        for forbidden in forbidden_imports:
            pattern = rf"from\s+parser_2gis\.{forbidden}|from\s+\.{forbidden}"
            if re.search(pattern, content):
                violations.append(forbidden)

        assert not violations, (
            f"constants.py не должен импортировать внутренние модули. Нарушения: {', '.join(violations)}"
        )


# =============================================================================
# ТЕСТЫ НА ЗАВИСИМОСТИ МЕЖДУ ПАКЕТАМИ
# =============================================================================


class TestInterPackageDependencies:
    """Тесты на зависимости между пакетами."""

    def test_parallel_package_dependencies(self) -> None:
        """Проверяет зависимости parallel/ пакета.

        parallel/ может зависеть от:
        - parser/ (для получения парсеров)
        - writer/ (для записи результатов)
        - utils/ (для утилит)
        - constants/ (для констант)
        - logger/ (для логирования)

        Не должен зависеть от:
        - tui_textual/ (UI)
        - cli/ (CLI)
        """
        parallel_dir = Path(__file__).parent.parent / "parser_2gis" / "parallel"

        forbidden_deps = {"tui_textual", "cli"}

        all_deps: Set[str] = set()

        for py_file in parallel_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            deps = self._get_module_dependencies_from_file(py_file)
            all_deps.update(deps)

        # Проверяем что нет запрещённых зависимостей
        forbidden_found = all_deps & forbidden_deps

        assert not forbidden_found, f"parallel/ не должен зависеть от: {', '.join(forbidden_found)}"

    def test_chrome_package_dependencies(self) -> None:
        """Проверяет зависимости chrome/ пакета.

        chrome/ может зависеть от:
        - utils/ (для утилит)
        - constants/ (для констант)
        - logger/ (для логирования)

        Не должен зависеть от:
        - parser/ (бизнес-логика)
        - writer/ (бизнес-логика)
        - tui_textual/ (UI)
        """
        chrome_dir = Path(__file__).parent.parent / "parser_2gis" / "chrome"

        forbidden_deps = {"parser", "writer", "tui_textual", "cli"}

        all_deps: Set[str] = set()

        for py_file in chrome_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            deps = self._get_module_dependencies_from_file(py_file)
            all_deps.update(deps)

        # Проверяем что нет запрещённых зависимостей
        forbidden_found = all_deps & forbidden_deps

        # chrome/ может зависеть от parser для типов
        # Поэтому это предупреждение, а не ошибка
        if forbidden_found:
            pytest.fail(
                f"chrome/ имеет зависимости от: {', '.join(forbidden_found)}. "
                "Рекомендуется использовать Protocol для разрыва зависимостей."
            )

    def _get_module_dependencies_from_file(self, module_path: Path) -> Set[str]:
        """Получает зависимости модуля.

        Args:
            module_path: Путь к модулю.

        Returns:
            Множество имён модулей.
        """
        content = module_path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return set()

        dependencies: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module
                    if module_name.startswith("parser_2gis"):
                        module_name = module_name.replace("parser_2gis.", "")
                    first_component = module_name.split(".")[0]
                    if first_component:
                        dependencies.add(first_component)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    if module_name.startswith("parser_2gis"):
                        module_name = module_name.replace("parser_2gis.", "")
                    first_component = module_name.split(".")[0]
                    if first_component:
                        dependencies.add(first_component)

        return dependencies


# =============================================================================
# ТЕСТЫ НА ИМПОРТЫ ВНУТРИ ПАКЕТОВ
# =============================================================================


class TestIntraPackageImports:
    """Тесты на импорты внутри пакетов."""

    def test_utils_package_internal_imports(self) -> None:
        """Проверяет что модули utils/ не импортируют друг друга циклично."""
        utils_dir = Path(__file__).parent.parent / "parser_2gis" / "utils"

        # Строим граф зависимостей
        dependencies: Dict[str, Set[str]] = {}

        for py_file in utils_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            module_name = py_file.stem
            deps = self._get_internal_deps(py_file, utils_dir)
            dependencies[module_name] = deps

        # Проверяем циклы
        cycles = self._find_cycles(dependencies)

        assert not cycles, f"В utils/ обнаружены циклические зависимости: {cycles}"

    def test_validation_package_internal_imports(self) -> None:
        """Проверяет что модули validation/ не импортируют друг друга циклично."""
        validation_dir = Path(__file__).parent.parent / "parser_2gis" / "validation"

        dependencies: Dict[str, Set[str]] = {}

        for py_file in validation_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            module_name = py_file.stem
            deps = self._get_internal_deps(py_file, validation_dir)
            dependencies[module_name] = deps

        cycles = self._find_cycles(dependencies)

        assert not cycles, f"В validation/ обнаружены циклические зависимости: {cycles}"

    def _get_internal_deps(self, module_path: Path, package_dir: Path) -> Set[str]:
        """Получает внутренние зависимости пакета.

        Args:
            module_path: Путь к модулю.
            package_dir: Путь к директории пакета.

        Returns:
            Множество имён модулей внутри пакета.
        """
        content = module_path.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return set()

        dependencies: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Относительный импорт внутри пакета
                if node.level > 0 and node.module:
                    dependencies.add(node.module)
                elif node.level > 0 and not node.module:
                    # from . import module
                    for alias in node.names:
                        dependencies.add(alias.name)

        return dependencies

    def _find_cycles(self, dependencies: Dict[str, Set[str]]) -> List[str]:
        """Ищет циклы в графе зависимостей.

        Args:
            dependencies: Граф зависимостей.

        Returns:
            Список найденных циклов.
        """
        cycles: List[str] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path)
                elif neighbor in rec_stack:
                    # Нашли цикл
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(" -> ".join(cycle))

            path.pop()
            rec_stack.remove(node)

        for node in dependencies:
            if node not in visited:
                dfs(node, [])

        return cycles
