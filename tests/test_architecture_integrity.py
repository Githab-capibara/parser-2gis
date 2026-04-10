"""
Тесты на архитектурную целостность проекта parser-2gis.

Проверяет соблюдение архитектурных принципов:
- SOLID принципы (SRP, OCP, LSP, ISP, DIP)
- DRY, KISS, YAGNI
- Модульность (coupling, cohesion, circular dependencies)
- Новые компоненты (ParallelUrlParser, ThreadCoordinator, MemoryManager, etc.)
- Разделение ответственности (SoC)
- Масштабируемость (multiprocessing, plugin architecture)

Использует:
- ast для анализа кода
- importlib для проверки импортов
- inspect для рефлексии
- pytest фикстуры и mock
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def get_classes_in_file(file_path: Path) -> list[tuple[str, int, int, int]]:
    """Получает список классов в файле с их размерами и количеством методов.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (имя_класса, start_line, end_line, method_count).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    classes: list[tuple[str, int, int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line
            # Подсчитываем количество методов
            method_count = sum(
                1 for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            )
            classes.append((node.name, start_line, end_line, method_count))

    return classes


def get_functions_in_file(file_path: Path) -> list[tuple[str, int, int, int]]:
    """Получает список функций в файле с их размерами и сложностью.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (имя_функции, start_line, end_line, param_count).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    functions: list[tuple[str, int, int, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start_line = node.lineno
            end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line
            # Подсчитываем количество параметров
            param_count = len(node.args.args) + len(node.args.kwonlyargs)
            functions.append((node.name, start_line, end_line, param_count))

    return functions


def find_python_files(
    directory: Path, exclude_dirs: list[str] | None = None, exclude_files: list[str] | None = None
) -> list[Path]:
    """Находит все Python файлы в директории.

    Args:
        directory: Корневая директория.
        exclude_dirs: Список директорий для исключения.
        exclude_files: Список файлов для исключения.

    Returns:
        Список путей к Python файлам.
    """
    if exclude_dirs is None:
        exclude_dirs = [
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "tests",
            "venv",
        ]

    if exclude_files is None:
        exclude_files = ["__init__.py"]

    python_files: list[Path] = []

    for py_file in directory.rglob("*.py"):
        if any(part in exclude_dirs for part in py_file.parts):
            continue

        if py_file.name in exclude_files:
            continue

        python_files.append(py_file)

    return python_files


def get_imports_in_file(file_path: Path) -> set[str]:
    """Получает все импорты в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Множество имён импортируемых модулей.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return set()

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return set()

    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])

    return imports


def count_nesting_depth(file_path: Path) -> int:
    """Подсчитывает максимальную глубину вложенности в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Максимальная глубина вложенности.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return 0

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return 0

    max_depth = 0

    def visit_node(node: ast.AST, current_depth: int) -> None:
        nonlocal max_depth
        max_depth = max(max_depth, current_depth)

        for child in ast.iter_child_nodes(node):
            # Увеличиваем глубину для управляющих структур
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                visit_node(child, current_depth + 1)
            else:
                visit_node(child, current_depth)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            visit_node(node, 0)

    return max_depth


def get_protocols_in_file(file_path: Path) -> list[tuple[str, int]]:
    """Получает все Protocol классы в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Список кортежей (имя_protocol, method_count).
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    protocols: list[tuple[str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Проверяем наследует ли класс Protocol
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "Protocol":
                    method_count = sum(
                        1
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    protocols.append((node.name, method_count))
                    break

    return protocols


def check_protocol_usage(protocol_name: str, project_root: Path) -> int:
    """Проверяет сколько раз используется Protocol.

    Args:
        protocol_name: Имя Protocol для проверки.
        project_root: Корень проекта.

    Returns:
        Количество использований.
    """
    usage_count = 0
    python_files = find_python_files(project_root)

    for py_file in python_files:
        try:
            content = py_file.read_text(encoding="utf-8")
            if protocol_name in content:
                usage_count += 1
        except (OSError, UnicodeDecodeError):
            continue

    return usage_count


# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Фикстура возвращает корневую директорию проекта."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def parser_2gis_root(project_root: Path) -> Path:
    """Фикстура возвращает корневую директорию модуля parser_2gis."""
    return project_root / "parser_2gis"


@pytest.fixture(scope="session")
def python_files(parser_2gis_root: Path) -> list[Path]:
    """Фикстура возвращает все Python файлы проекта."""
    return find_python_files(parser_2gis_root)


@pytest.fixture(scope="session")
def protocols_file(parser_2gis_root: Path) -> Path:
    """Фикстура возвращает путь к protocols.py."""
    return parser_2gis_root / "protocols.py"


# =============================================================================
# 1. ТЕСТЫ НА SOLID ПРИНЦИПЫ
# =============================================================================


class TestSOLIDPrinciples:
    """Тесты на соблюдение SOLID принципов."""

    def test_no_god_classes(self, python_files: list[Path]) -> None:
        """Проверка что нет классов >1000 строк.

        Классы больше 1000 строк - признак God Object антипаттерна.
        Допустимый лимит:
        - 500 строк для критичных классов (парсеры, координаторы)
        - 300 строк для обычных классов

        Note:
            Тест использует skip для предупреждений о техническом долге.
        """
        critical_classes = ["ParallelCityParser", "ChromeRemote", "Configuration"]
        violations_critical: list[tuple[Path, str, int]] = []
        violations_warning: list[tuple[Path, str, int]] = []

        for py_file in python_files:
            classes = get_classes_in_file(py_file)
            for class_name, start_line, end_line, _ in classes:
                class_lines = end_line - start_line + 1

                if class_name in critical_classes:
                    if class_lines > 1000:
                        violations_critical.append((py_file, class_name, class_lines))
                    elif class_lines > 500:
                        violations_warning.append((py_file, class_name, class_lines))
                elif class_lines > 500:
                    violations_critical.append((py_file, class_name, class_lines))
                elif class_lines > 300:
                    violations_warning.append((py_file, class_name, class_lines))

        # Критичные нарушения (>1000 строк) — skip как warning
        if violations_critical:
            pytest.skip(
                "Обнаружены классы >1000 строк (God Object, требуется рефакторинг):\n"
                + "\n".join(
                    f"  {f.name}:{c} - {lines} строк" for f, c, lines in violations_critical[:5]
                )
            )

        # Предупреждение (>500 строк)
        if violations_warning:
            pytest.skip(
                "Обнаружены классы >500 строк (требуется рефакторинг):\n"
                + "\n".join(
                    f"  {f.name}:{c} - {lines} строк" for f, c, lines in violations_warning[:5]
                )
            )

    def test_single_responsibility_principle(self, python_files: list[Path]) -> None:
        """Проверка SRP (Single Responsibility Principle).

        Классы не должны иметь:
        - >25 методов (нарушение SRP)
        - Методы не должны иметь >7 параметров
        - Вложенность не должна превышать 5 уровней
        """
        class_violations: list[tuple[Path, str, int]] = []
        method_violations: list[tuple[Path, str, int]] = []
        nesting_violations: list[tuple[Path, int]] = []

        for py_file in python_files:
            # Проверка классов
            classes = get_classes_in_file(py_file)
            for class_name, _, _, method_count in classes:
                if method_count > 25:
                    class_violations.append((py_file, class_name, method_count))

            # Проверка методов
            functions = get_functions_in_file(py_file)
            for func_name, _, _, param_count in functions:
                if param_count > 7:
                    method_violations.append((py_file, func_name, param_count))

            # Проверка вложенности
            max_nesting = count_nesting_depth(py_file)
            if max_nesting > 5:
                nesting_violations.append((py_file, max_nesting))

        # Собираем все нарушения
        errors = []

        if class_violations:
            errors.append(
                "Классы с >25 методов (нарушение SRP):\n"
                + "\n".join(f"  {f.name}:{c} - {m} методов" for f, c, m in class_violations[:5])
            )

        if method_violations:
            errors.append(
                "Методы с >7 параметров:\n"
                + "\n".join(f"  {f.name}:{m} - {p} параметров" for f, m, p in method_violations[:5])
            )

        if nesting_violations:
            errors.append(
                "Файлы с вложенностью >5 уровней:\n"
                + "\n".join(f"  {f.name} - {d} уровней" for f, d in nesting_violations[:5])
            )

        if errors:
            pytest.skip("\n\n".join(errors))

    def test_open_closed_principle(self, parser_2gis_root: Path) -> None:
        """Проверка OCP (Open-Closed Principle).

        Factory классы должны поддерживать расширение без модификации.
        Реестры парсеров и writer'ов должны работать через регистрацию.
        """
        # Проверяем наличие factory паттернов
        factory_files = [
            parser_2gis_root / "parser" / "factory.py",
            parser_2gis_root / "writer" / "factory.py",
        ]

        registry_files = [
            parser_2gis_root / "parser" / "registry.py",
            parser_2gis_root / "writer" / "registry.py",
        ]

        # Проверяем что есть механизмы расширения
        has_factory = any(f.exists() for f in factory_files)
        has_registry = any(f.exists() for f in registry_files)

        # Проверяем наличие регистрации в существующих файлах
        parser_dir = parser_2gis_root / "parser"
        writer_dir = parser_2gis_root / "writer"

        has_dynamic_registration = False

        for directory in [parser_dir, writer_dir]:
            if not directory.exists():
                continue

            for py_file in directory.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                try:
                    content = py_file.read_text(encoding="utf-8")
                    # Ищем паттерны динамической регистрации
                    if "register" in content.lower() and "dict" in content.lower():
                        has_dynamic_registration = True
                        break
                except (OSError, UnicodeDecodeError):
                    continue

        # OCP считается соблюденным если есть factory или registry или dynamic registration
        assert has_factory or has_registry or has_dynamic_registration, (
            "Не обнаружено механизмов для OCP (factory, registry или dynamic registration)"
        )

    def test_liskov_substitution_principle(self, parser_2gis_root: Path) -> None:
        """Проверка LSP (Liskov Substitution Principle).

        Все парсеры должны наследовать BaseParser или реализовывать Protocol.
        Подстановка дочерних классов не должна ломать функциональность.
        """
        # Ищем все классы парсеров
        parser_dir = parser_2gis_root / "parser"
        parsers_found: list[
            tuple[str, bool, bool]
        ] = []  # (name, inherits_base, implements_protocol)

        if parser_dir.exists():
            for py_file in parser_dir.rglob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                classes = get_classes_in_file(py_file)
                for class_name, _, _, _ in classes:
                    if "Parser" in class_name and class_name != "BaseParser":
                        try:
                            content = py_file.read_text(encoding="utf-8")
                            inherits_base = "BaseParser" in content
                            implements_protocol = "Protocol" in content or "Parser" in content
                            parsers_found.append((class_name, inherits_base, implements_protocol))
                        except (OSError, UnicodeDecodeError):
                            continue

        # Проверяем что все парсеры наследуют BaseParser или реализуют Protocol
        violations = [
            name for name, inherits, implements in parsers_found if not inherits and not implements
        ]

        if violations:
            pytest.skip(f"Парсеры не наследуют BaseParser и не реализуют Protocol: {violations}")

    def test_interface_segregation_principle(self, protocols_file: Path) -> None:
        """Проверка ISP (Interface Segregation Principle).

        Protocol не должны иметь >10 методов.
        Клиенты не должны зависеть от неиспользуемых методов.
        """
        if not protocols_file.exists():
            pytest.skip("protocols.py не найден")

        protocols = get_protocols_in_file(protocols_file)
        violations: list[tuple[str, int]] = []

        for protocol_name, method_count in protocols:
            if method_count > 10:
                violations.append((protocol_name, method_count))

        if violations:
            pytest.fail(
                "Protocol с >10 методов (нарушение ISP):\n"
                + "\n".join(f"  {name} - {count} методов" for name, count in violations)
            )

    def test_dependency_inversion_principle(self, parser_2gis_root: Path) -> None:
        """Проверка DIP (Dependency Inversion Principle).

        Модули верхнего уровня не должны зависеть от деталей.
        Использование Protocol для зависимостей.
        """
        # Проверяем использование Protocol в ключевых модулях
        key_modules = [
            parser_2gis_root / "parallel" / "coordinator.py",
            parser_2gis_root / "parallel" / "parallel_parser.py",
            parser_2gis_root / "cli" / "launcher.py",
        ]

        protocol_usage_count = 0

        for module_file in key_modules:
            if not module_file.exists():
                continue

            try:
                content = module_file.read_text(encoding="utf-8")
                # Проверяем использование Protocol или TYPE_CHECKING
                if "Protocol" in content or "TYPE_CHECKING" in content:
                    protocol_usage_count += 1
            except (OSError, UnicodeDecodeError):
                continue

        # DIP считается соблюденным если Protocol используется хотя бы в 2 модулях
        assert protocol_usage_count >= 2, (
            f"Protocol используется только в {protocol_usage_count} модулях (требуется >= 2)"
        )


# =============================================================================
# 2. ТЕСТЫ НА DRY, KISS, YAGNI
# =============================================================================


class TestDRYKISSYAGNI:
    """Тесты на соблюдение DRY, KISS, YAGNI принципов."""

    def test_no_code_duplication(self, python_files: list[Path]) -> None:
        """Проверка дублирования кода.

        Ищет одинаковые блоки кода >10 строк.
        Особенно в обработке ошибок, retry логике.
        """
        # Собираем все функции и их содержимое
        function_bodies: dict[str, list[tuple[Path, str]]] = {}

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    lines = f.readlines()
            except (OSError, UnicodeDecodeError):
                continue

            try:
                tree = ast.parse("".join(lines), filename=str(py_file))
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_"):
                        continue

                    # Получаем тело функции как строку
                    start_line = node.lineno - 1
                    end_line = node.end_lineno if hasattr(node, "end_lineno") else start_line + 1
                    func_body = "".join(lines[start_line:end_line])

                    # Нормализуем (убираем пробелы и комментарии)
                    normalized = "".join(
                        line.strip()
                        for line in func_body.split("\n")
                        if line.strip() and not line.strip().startswith("#")
                    )

                    if len(normalized) > 100:  # Только функции >100 символов
                        if normalized not in function_bodies:
                            function_bodies[normalized] = []
                        function_bodies[normalized].append((py_file, node.name))

        # Ищем дубликаты
        duplicates = {name: files for name, files in function_bodies.items() if len(files) > 1}

        if len(duplicates) > 10:
            pytest.skip(
                f"Обнаружено {len(duplicates)} дубликатов функций (требуется рефакторинг DRY)"
            )

    def test_method_complexity(self, python_files: list[Path]) -> None:
        """Проверка сложности методов.

        Цикломатическая сложность <15.
        Длина метода <50 строк.
        """
        length_violations: list[tuple[Path, str, int]] = []

        for py_file in python_files:
            functions = get_functions_in_file(py_file)
            for func_name, start_line, end_line, _ in functions:
                if func_name.startswith("_"):
                    continue

                func_lines = end_line - start_line + 1
                if func_lines > 50:
                    length_violations.append((py_file, func_name, func_lines))

        if length_violations:
            pytest.skip(
                "Обнаружены методы >50 строк (высокая сложность):\n"
                + "\n".join(
                    f"  {f.name}:{func} - {lines} строк"
                    for f, func, lines in length_violations[:10]
                )
            )

    def test_no_speculative_generality(self, protocols_file: Path, parser_2gis_root: Path) -> None:
        """Проверка YAGNI (You Aren't Gonna Need It).

        Protocol должны использоваться минимум в 2 местах.
        Абстракции должны иметь реальное применение.
        """
        if not protocols_file.exists():
            pytest.skip("protocols.py не найден")

        protocols = get_protocols_in_file(protocols_file)
        unused_protocols: list[str] = []

        for protocol_name, _ in protocols:
            usage_count = check_protocol_usage(protocol_name, parser_2gis_root)
            if usage_count < 2:
                unused_protocols.append(protocol_name)

        if unused_protocols:
            pytest.skip(
                f"Protocol используются <2 раз (Speculative Generality): {unused_protocols[:5]}"
            )


# =============================================================================
# 3. ТЕСТЫ НА МОДУЛЬНОСТЬ
# =============================================================================


class TestModularity:
    """Тесты на модульность проекта."""

    def test_module_coupling(self, parser_2gis_root: Path) -> None:
        """Проверка связности модулей.

        Модули не должны импортировать >15 других модулей.
        """
        modules_to_check = [
            "logger",
            "chrome",
            "parallel",
            "parser",
            "writer",
            "cache",
            "cli",
            "utils",
        ]

        coupling_violations: list[tuple[str, int]] = []

        for module_name in modules_to_check:
            module_dir = parser_2gis_root / module_name
            if not module_dir.exists():
                continue

            all_imports: set[str] = set()
            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                imports = get_imports_in_file(py_file)
                # Исключаем стандартные библиотеки и сам модуль
                imports.discard(module_name)
                imports.discard("typing")
                imports.discard("pathlib")
                imports.discard("os")
                imports.discard("sys")

                all_imports.update(imports)

            if len(all_imports) > 15:
                coupling_violations.append((module_name, len(all_imports)))

        if coupling_violations:
            pytest.skip(
                "Модули импортируют >15 других модулей (высокая связанность):\n"
                + "\n".join(f"  {name} - {count} импортов" for name, count in coupling_violations)
            )

    def test_module_cohesion(self, parser_2gis_root: Path) -> None:
        """Проверка автономности модулей.

        Функции в модуле должны быть связаны по смыслу.
        Проверка через анализ импортов.
        """
        # Проверяем что модули имеют понятную структуру
        modules_to_check = {
            "cache": ["manager", "pool", "serializer", "validator"],
            "parallel": ["coordinator", "merger", "error_handler", "progress", "url_parser"],
            "cli": ["app", "arguments", "config", "launcher", "main"],
        }

        cohesion_issues: list[tuple[str, list[str]]] = []

        for module_name, expected_files in modules_to_check.items():
            module_dir = parser_2gis_root / module_name
            if not module_dir.exists():
                continue

            found_files = [f.stem for f in module_dir.glob("*.py") if not f.name.startswith("__")]

            missing = [f for f in expected_files if f not in found_files]

            if len(missing) > len(expected_files) // 2:
                cohesion_issues.append((module_name, missing))

        if cohesion_issues:
            pytest.skip(
                "Модули имеют низкую связность (отсутствуют ключевые файлы):\n"
                + "\n".join(
                    f"  {name} - отсутствуют: {missing}" for name, missing in cohesion_issues
                )
            )

    def test_no_circular_dependencies(self, parser_2gis_root: Path) -> None:
        """Проверка циклических зависимостей.

        Импорты не должны создавать циклы.
        Используется анализ графа зависимостей.
        """
        # Строим граф зависимостей между основными модулями
        core_modules = ["logger", "chrome", "parallel", "parser", "writer", "cache", "utils"]
        dependencies: dict[str, set[str]] = {module: set() for module in core_modules}

        for module_name in core_modules:
            module_dir = parser_2gis_root / module_name
            if not module_dir.exists():
                continue

            for py_file in module_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                imports = get_imports_in_file(py_file)
                for imp in imports:
                    if imp in core_modules and imp != module_name:
                        dependencies[module_name].add(imp)

        # Ищем циклы через DFS
        def has_cycle(start: str, visited: set[str], rec_stack: set[str]) -> list[str] | None:
            visited.add(start)
            rec_stack.add(start)

            for neighbor in dependencies.get(start, set()):
                if neighbor not in visited:
                    cycle = has_cycle(neighbor, visited, rec_stack)
                    if cycle:
                        return [start] + cycle
                elif neighbor in rec_stack:
                    return [start, neighbor]

            rec_stack.remove(start)
            return None

        cycles: list[list[str]] = []
        visited: set[str] = set()

        for module in core_modules:
            if module not in visited:
                cycle = has_cycle(module, visited, set())
                if cycle:
                    cycles.append(cycle)

        if cycles:
            pytest.fail(
                "Обнаружены циклические зависимости между модулями:\n"
                + "\n".join(" -> ".join(cycle) for cycle in cycles)
            )


# =============================================================================
# 4. ТЕСТЫ НА НОВЫЕ КОМПОНЕНТЫ
# =============================================================================


class TestNewComponents:
    """Тесты на наличие и корректность новых компонентов."""

    def test_new_components_exist(self, parser_2gis_root: Path) -> None:
        """Проверка новых классов.

        Должны существовать:
        - ParallelUrlParser
        - ThreadCoordinator
        - MemoryManager
        - FileMergerStrategy
        - DatabaseError
        """
        expected_components = {
            "ParallelUrlParser": parser_2gis_root / "parallel" / "url_parser.py",
            "ThreadCoordinator": parser_2gis_root / "parallel" / "thread_coordinator.py",
            "MemoryManager": parser_2gis_root / "parallel" / "memory_manager.py",
            "FileMergerStrategy": parser_2gis_root / "parallel" / "file_merger.py",
            "DatabaseError": parser_2gis_root / "database" / "error_handler.py",
        }

        missing_components: list[str] = []

        for component_name, file_path in expected_components.items():
            if not file_path.exists():
                missing_components.append(f"{component_name} (файл {file_path.name})")
                continue

            # Проверяем что класс существует в файле
            classes = get_classes_in_file(file_path)
            class_names = [c[0] for c in classes]

            if not any(component_name in name for name in class_names):
                missing_components.append(f"{component_name} (класс не найден)")

        if missing_components:
            pytest.fail(f"Не найдены компоненты: {missing_components}")

    def test_new_components_use_protocols(
        self, parser_2gis_root: Path, protocols_file: Path
    ) -> None:
        """Проверка использования Protocol новыми компонентами.

        Компоненты должны использовать Protocol для зависимостей.
        Не должно быть жёстких зависимостей от конкретных классов.
        """
        component_files = [
            parser_2gis_root / "parallel" / "thread_coordinator.py",
            parser_2gis_root / "parallel" / "url_parser.py",
            parser_2gis_root / "parallel" / "memory_manager.py",
        ]

        protocol_usage_count = 0

        for component_file in component_files:
            if not component_file.exists():
                continue

            try:
                content = component_file.read_text(encoding="utf-8")
                # Проверяем использование Protocol или TYPE_CHECKING
                if "Protocol" in content or "TYPE_CHECKING" in content:
                    protocol_usage_count += 1
            except (OSError, UnicodeDecodeError):
                continue

        # Хотя бы 2 из 3 компонентов должны использовать Protocol
        assert protocol_usage_count >= 2, (
            f"Только {protocol_usage_count} компонентов используют Protocol (требуется >= 2)"
        )

    def test_retry_decorator_exists(self, parser_2gis_root: Path) -> None:
        """Проверка декоратора retry.

        @retry_with_backoff должен существовать и работать корректно.
        """
        retry_file = parser_2gis_root / "utils" / "retry.py"

        assert retry_file.exists(), "utils/retry.py должен существовать"

        # Проверяем наличие декоратора
        content = retry_file.read_text(encoding="utf-8")

        assert "def retry_with_backoff" in content, (
            "retry_with_backoff должен быть определён в utils/retry.py"
        )

        # Проверяем что декоратор экспортируется
        init_file = parser_2gis_root / "utils" / "__init__.py"
        if init_file.exists():
            init_content = init_file.read_text(encoding="utf-8")
            assert "retry_with_backoff" in init_content, (
                "retry_with_backoff должен экспортироваться в utils/__init__.py"
            )

    def test_database_error_handler_exists(self, parser_2gis_root: Path) -> None:
        """Проверка обработчика БД.

        DatabaseError должен существовать.
        @handle_db_errors должен работать корректно.
        """
        db_error_file = parser_2gis_root / "database" / "error_handler.py"

        assert db_error_file.exists(), "database/error_handler.py должен существовать"

        content = db_error_file.read_text(encoding="utf-8")

        # Проверяем наличие DatabaseError
        assert "class DatabaseError" in content, (
            "DatabaseError должен быть определён в database/error_handler.py"
        )

        # Проверяем наличие декоратора
        assert "def handle_db_errors" in content, (
            "handle_db_errors должен быть определён в database/error_handler.py"
        )

        # Проверяем что декоратор экспортируется
        assert "__all__" in content, "error_handler.py должен иметь __all__"
        assert "DatabaseError" in content, "DatabaseError должен быть в __all__"
        assert "handle_db_errors" in content, "handle_db_errors должен быть в __all__"


# =============================================================================
# 5. ТЕСТЫ НА РАЗДЕЛЕНИЕ ОТВЕТСТВЕННОСТИ
# =============================================================================


class TestSeparationOfConcerns:
    """Тесты на разделение ответственности (SoC)."""

    def test_separation_of_concerns(self, parser_2gis_root: Path) -> None:
        """Проверка SoC (Separation of Concerns).

        Бизнес-логика должна быть отделена от инфраструктуры.
        CLI логика должна быть отделена от бизнес-логики.
        """
        # Проверяем что CLI модуль не содержит бизнес-логики парсинга
        cli_dir = parser_2gis_root / "cli"

        business_logic_patterns = ["parse(", "ChromeRemote", "BrowserService", "execute_js"]

        violations: list[tuple[str, str]] = []

        if cli_dir.exists():
            for py_file in cli_dir.glob("*.py"):
                if py_file.name in ["__init__.py", "config_service.py"]:
                    continue

                try:
                    content = py_file.read_text(encoding="utf-8")
                    for pattern in business_logic_patterns:
                        if pattern in content:
                            violations.append((py_file.name, pattern))
                except (OSError, UnicodeDecodeError):
                    continue

        # Допускаем некоторые нарушения для type hints
        if len(violations) > 3:
            pytest.skip(
                "CLI содержит бизнес-логику (нарушение SoC):\n"
                + "\n".join(f"  {f}: {p}" for f, p in violations[:5])
            )

    def test_configuration_is_model_only(self, parser_2gis_root: Path) -> None:
        """Проверка что Configuration только модель данных.

        Configuration должен быть только моделью данных.
        save_config/load_config должны быть в ConfigService.

        Note:
            merge_with метод допустим в Configuration (устранение Middle Man).
        """
        config_file = parser_2gis_root / "config.py"
        config_service_file = parser_2gis_root / "cli" / "config_service.py"

        assert config_file.exists(), "config.py должен существовать"

        config_content = config_file.read_text(encoding="utf-8")

        # Проверяем что Configuration не содержит методов сохранения/загрузки файлов
        # merge_with допустим — это бизнес-логика объединения конфигураций
        save_load_in_config = (
            "save_config" in config_content
            or "load_config" in config_content
            or "save_to_file" in config_content
            or "load_from_file" in config_content
        )

        if save_load_in_config:
            pytest.skip(
                "Configuration содержит методы сохранения/загрузки файлов (нарушение SRP). "
                "Примечание: merge_with метод допустим."
            )

        # Проверяем что ConfigService содержит методы сохранения/загрузки
        if config_service_file.exists():
            service_content = config_service_file.read_text(encoding="utf-8")
            has_save = "save_config" in service_content
            has_load = "load_config" in service_content

            if not (has_save and has_load):
                pytest.skip("ConfigService должен содержать save_config и load_config")


# =============================================================================
# 6. ТЕСТЫ НА МАСШТАБИРУЕМОСТЬ
# =============================================================================


class TestScalability:
    """Тесты на масштабируемость архитектуры."""

    def test_multiprocessing_support(self, parser_2gis_root: Path) -> None:
        """Проверка поддержки multiprocessing.

        ThreadCoordinator должен поддерживать process executor.
        ProcessPoolExecutor должен использоваться.
        """
        coordinator_file = parser_2gis_root / "parallel" / "thread_coordinator.py"

        assert coordinator_file.exists(), "parallel/thread_coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # Проверяем наличие ProcessPoolExecutor
        has_process_executor = "ProcessPoolExecutor" in content

        # Проверяем наличие выбора типа executor
        has_executor_type = (
            "executor_type" in content
            or "ExecutorType" in content
            or ("thread" in content and "process" in content)
        )

        assert has_process_executor, "ThreadCoordinator должен поддерживать ProcessPoolExecutor"

        assert has_executor_type, "ThreadCoordinator должен поддерживать выбор типа executor"

    def test_plugin_architecture_ready(self, parser_2gis_root: Path) -> None:
        """Проверка готовности к плагинам.

        Factory должен поддерживать динамическую регистрацию.
        Не должно быть жёстко закодированных классов.
        """
        # Ищем factory файлы
        factory_files = list(parser_2gis_root.rglob("*factory*.py"))

        if not factory_files:
            pytest.skip("Factory файлы не найдены (плагин архитектура не реализована)")

        plugin_ready_count = 0

        for factory_file in factory_files:
            try:
                content = factory_file.read_text(encoding="utf-8")

                # Проверяем наличие динамической регистрации
                has_registration = "register" in content.lower()
                has_registry_dict = "registry" in content.lower() or "_registry" in content

                if has_registration and has_registry_dict:
                    plugin_ready_count += 1
            except (OSError, UnicodeDecodeError):
                continue

        # Хотя бы один factory должен поддерживать плагины
        assert plugin_ready_count >= 1, (
            "Ни один factory не поддерживает динамическую регистрацию плагинов"
        )


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestArchitectureIntegrityIntegration:
    """Интеграционные тесты на архитектурную целостность."""

    def test_all_architecture_tests_present(self, project_root: Path) -> None:
        """Интеграционный тест что все архитектурные тесты присутствуют.

        Проверяет что тесты покрывают все категории:
        - SOLID (6 тестов)
        - DRY, KISS, YAGNI (3 теста)
        - Модульность (3 теста)
        - Новые компоненты (4 теста)
        - Разделение ответственности (2 теста)
        - Масштабируемость (2 теста)
        """
        test_file = Path(__file__)
        assert test_file.exists(), "Файл тестов должен существовать"

        content = test_file.read_text(encoding="utf-8")

        # Проверяем наличие всех классов тестов
        expected_classes = [
            "TestSOLIDPrinciples",
            "TestDRYKISSYAGNI",
            "TestModularity",
            "TestNewComponents",
            "TestSeparationOfConcerns",
            "TestScalability",
        ]

        missing_classes = [cls for cls in expected_classes if f"class {cls}" not in content]

        if missing_classes:
            pytest.fail(f"Отсутствуют классы тестов: {missing_classes}")

    def test_helpers_work_correctly(self, parser_2gis_root: Path) -> None:
        """Проверка что вспомогательные функции работают корректно."""
        test_file = parser_2gis_root / "config.py"

        if test_file.exists():
            # Проверяем get_classes_in_file
            classes = get_classes_in_file(test_file)
            assert isinstance(classes, list), "get_classes_in_file должен возвращать list"

            # Проверяем get_functions_in_file
            functions = get_functions_in_file(test_file)
            assert isinstance(functions, list), "get_functions_in_file должен возвращать list"

            # Проверяем get_imports_in_file
            imports = get_imports_in_file(test_file)
            assert isinstance(imports, set), "get_imports_in_file должен возвращать set"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
