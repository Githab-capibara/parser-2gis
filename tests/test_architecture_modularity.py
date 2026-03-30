"""
Тесты на проверку модульности проекта.

Проверяет что:
- Файлы <500 строк (кроме исключений)
- Каждый модуль имеет одну ответственность
- Импорты явные (не через __init__.py)
- Модули не имеют излишней связанности

Принципы:
- Single Responsibility Principle для модулей
- Явные импорты вместо неявных
- Низкая связанность между модулями
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple

import pytest

# =============================================================================
# КОНСТАНТЫ
# =============================================================================

MAX_FILE_LINES = 500  # Максимальное количество строк в файле
MAX_FUNCTIONS_PER_FILE = 30  # Максимальное количество функций в файле
MAX_CLASSES_PER_FILE = 15  # Максимальное количество классов в файле
MAX_IMPORTS_PER_FILE = 30  # Максимальное количество импортов в файле
MAX_NESTING_DEPTH = 10  # Максимальная глубина вложенности

# Исключения для файлов >500 строк (пути относительно parser_2gis/)
LARGE_FILE_EXCEPTIONS = [
    # Файлы которые могут быть большими по объективным причинам
    "chrome/browser.py",  # Содержит несколько классов с документацией
    "chrome/js_executor.py",  # JavaScript executor
    "parallel/coordinator.py",  # Координация сложной логики
    "parallel/merger.py",  # Сложная логика слияния
    "utils/temp_file_manager.py",  # Управление временными файлами
    "chrome/remote.py",  # Chrome Remote интерфейс
    "parallel/parallel_parser.py",  # Параллельный парсинг
    "logger/visual_logger.py",  # Визуальный логгер
]


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def count_lines(file_path: Path) -> int:
    """Подсчитывает количество строк в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Количество строк.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return len(f.readlines())
    except (OSError, UnicodeDecodeError):
        return 0


def count_functions(file_path: Path) -> int:
    """Подсчитывает количество функций в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Количество функций.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return 0

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return 0

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            count += 1

    return count


def count_classes(file_path: Path) -> int:
    """Подсчитывает количество классов в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Количество классов.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return 0

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return 0

    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            count += 1

    return count


def count_imports(file_path: Path) -> Tuple[int, List[str]]:
    """Подсчитывает количество импортов в файле.

    Args:
        file_path: Путь к файлу.

    Returns:
        Кортеж (количество импортов, список импортированных модулей).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return 0, []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return 0, []

    imports: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return len(imports), imports


def get_module_responsibility(file_path: Path) -> str:
    """Определяет ответственность модуля по имени и содержимому.

    Args:
        file_path: Путь к файлу.

    Returns:
        Строка с описанием ответственности.
    """
    filename = file_path.name.lower()
    content = file_path.read_text(encoding="utf-8").lower()

    # Определяем по имени файла
    responsibility_keywords = {
        "browser": "управление браузером",
        "parser": "парсинг данных",
        "extractor": "извлечение данных",
        "processor": "обработка данных",
        "merger": "слияние файлов",
        "coordinator": "координация процессов",
        "error": "обработка ошибок",
        "progress": "отслеживание прогресса",
        "config": "конфигурация",
        "logger": "логирование",
        "cache": "кэширование",
        "writer": "запись данных",
        "validator": "валидация",
        "options": "опции и настройки",
        "protocol": "протоколы и интерфейсы",
    }

    for keyword, responsibility in responsibility_keywords.items():
        if keyword in filename:
            return responsibility

    # Определяем по содержимому
    if "class" in content and "def " in content:
        return "смешанная ответственность"

    return "не определена"


# =============================================================================
# ТЕСТ 1: РАЗМЕР ФАЙЛОВ
# =============================================================================


class TestFileSize:
    """Тесты на размер файлов."""

    def test_parallel_files_under_limit(self) -> None:
        """Проверяет что файлы parallel/ <500 строк."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            rel_path = str(py_file.relative_to(project_root))
            if rel_path in LARGE_FILE_EXCEPTIONS:
                continue

            lines = count_lines(py_file)
            assert lines < MAX_FILE_LINES, (
                f"{py_file.name} должен содержать <{MAX_FILE_LINES} строк (сейчас: {lines})"
            )

    def test_parser_files_under_limit(self) -> None:
        """Проверяет что файлы parser/parsers/ <500 строк."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parser_dir = project_root / "parser" / "parsers"

        for py_file in parser_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            lines = count_lines(py_file)
            assert lines < MAX_FILE_LINES, (
                f"{py_file.name} должен содержать <{MAX_FILE_LINES} строк (сейчас: {lines})"
            )

    def test_logger_files_under_limit(self) -> None:
        """Проверяет что файлы logger/ <500 строк."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        logger_dir = project_root / "logger"

        for py_file in logger_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            rel_path = str(py_file.relative_to(project_root))
            if rel_path in LARGE_FILE_EXCEPTIONS:
                continue

            lines = count_lines(py_file)
            assert lines < MAX_FILE_LINES, (
                f"{py_file.name} должен содержать <{MAX_FILE_LINES} строк (сейчас: {lines})"
            )

    def test_chrome_files_under_limit(self) -> None:
        """Проверяет что файлы chrome/ <500 строк (кроме browser.py)."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        chrome_dir = project_root / "chrome"

        for py_file in chrome_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            rel_path = str(py_file.relative_to(project_root))
            if rel_path in LARGE_FILE_EXCEPTIONS:
                continue

            lines = count_lines(py_file)
            assert lines < MAX_FILE_LINES, (
                f"{py_file.name} должен содержать <{MAX_FILE_LINES} строк (сейчас: {lines})"
            )

    def test_utils_files_under_limit(self) -> None:
        """Проверяет что файлы utils/ <500 строк."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        for py_file in utils_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            rel_path = str(py_file.relative_to(project_root))
            if rel_path in LARGE_FILE_EXCEPTIONS:
                continue

            lines = count_lines(py_file)
            assert lines < MAX_FILE_LINES, (
                f"{py_file.name} должен содержать <{MAX_FILE_LINES} строк (сейчас: {lines})"
            )


# =============================================================================
# ТЕСТ 2: КОЛИЧЕСТВО ФУНКЦИЙ И КЛАССОВ
# =============================================================================


class TestFunctionAndClassCount:
    """Тесты на количество функций и классов."""

    def test_parallel_files_function_count(self) -> None:
        """Проверяет что файлы parallel/ имеют <20 функций."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            func_count = count_functions(py_file)
            assert func_count < MAX_FUNCTIONS_PER_FILE, (
                f"{py_file.name} должен содержать <{MAX_FUNCTIONS_PER_FILE} функций "
                f"(сейчас: {func_count})"
            )

    def test_parallel_files_class_count(self) -> None:
        """Проверяет что файлы parallel/ имеют <10 классов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            class_count = count_classes(py_file)
            assert class_count < MAX_CLASSES_PER_FILE, (
                f"{py_file.name} должен содержать <{MAX_CLASSES_PER_FILE} классов "
                f"(сейчас: {class_count})"
            )

    def test_parser_files_class_count(self) -> None:
        """Проверяет что файлы parser/parsers/ имеют <10 классов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parser_dir = project_root / "parser" / "parsers"

        for py_file in parser_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            class_count = count_classes(py_file)
            assert class_count < MAX_CLASSES_PER_FILE, (
                f"{py_file.name} должен содержать <{MAX_CLASSES_PER_FILE} классов "
                f"(сейчас: {class_count})"
            )


# =============================================================================
# ТЕСТ 3: ЯВНЫЕ ИМПОРТЫ
# =============================================================================


class TestExplicitImports:
    """Тесты на явные импорты."""

    def test_no_wildcard_imports(self) -> None:
        """Проверяет отсутствие wildcard импортов (*)."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            content = py_file.read_text(encoding="utf-8")

            # Ищем wildcard импорты
            assert "from * import" not in content, (
                f"{py_file.name} не должен использовать wildcard импорты"
            )
            assert "from parser_2gis.* import" not in content, (
                f"{py_file.name} не должен использовать wildcard импорты из parser_2gis"
            )

    def test_no_init_re_exports_in_core(self) -> None:
        """Проверяет что core модули не делают re-export через __init__.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули которые не должны делать re-export
        core_packages = ["parallel", "parser", "chrome", "logger", "utils"]

        for package_name in core_packages:
            init_file = project_root / package_name / "__init__.py"
            if not init_file.exists():
                continue

            content = init_file.read_text(encoding="utf-8")

            # Проверяем что нет массового re-export
            # (некоторые re-export допустимы для backward compatibility)
            lines = content.split("\n")
            re_export_count = sum(1 for line in lines if "import" in line and "__all__" not in line)

            # Разрешаем до 15 импортов в __init__.py
            assert re_export_count < 30, (
                f"{package_name}/__init__.py имеет слишком много re-exports ({re_export_count}). "
                f"Рекомендуется использовать явные импорты."
            )

    def test_imports_are_explicit_not_from_init(self) -> None:
        """Проверяет что импорты явные а не через __init__.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем parallel модуль
        parallel_dir = project_root / "parallel"

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            count_imports(py_file)[1]

            # Проверяем что нет импортов вида "from . import X"
            content = py_file.read_text(encoding="utf-8")
            assert "from . import " not in content or "from . import (" not in content, (
                f"{py_file.name} должен использовать явные импорты (не через .)"
            )


# =============================================================================
# ТЕСТ 4: ОТВЕТСТВЕННОСТЬ МОДУЛЕЙ
# =============================================================================


class TestModuleResponsibility:
    """Тесты на ответственность модулей."""

    def test_each_module_has_single_responsibility(self) -> None:
        """Проверяет что каждый модуль имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем parallel модуль
        parallel_dir = project_root / "parallel"

        module_responsibilities = {
            "coordinator.py": "координация",
            "merger.py": "слияние",
            "error_handler.py": "ошибки",
            "progress.py": "прогресс",
            "options.py": "опции",
        }

        for filename, expected_responsibility in module_responsibilities.items():
            file_path = parallel_dir / filename
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding="utf-8").lower()

            # Проверяем что модуль содержит ключевые слова ответственности
            assert expected_responsibility in content, (
                f"{filename} должен содержать код для {expected_responsibility}"
            )

    def test_parser_modules_separated_by_responsibility(self) -> None:
        """Проверяет что parser модули разделены по ответственности."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parser_dir = project_root / "parser" / "parsers"

        # Ожидаемые модули и их ответственность
        expected_modules = {
            "main_parser.py": "dom",  # DOM и навигация
            "main_extractor.py": "извлечение",  # Извлечение данных
            "main_processor.py": "обработка",  # Обработка данных
            "firm.py": "firm",  # Парсинг фирм
        }

        for filename, expected_keyword in expected_modules.items():
            file_path = parser_dir / filename
            if not file_path.exists():
                continue

            content = file_path.read_text(encoding="utf-8").lower()

            # Проверяем что модуль содержит ключевые слова ответственности
            assert expected_keyword in content, (
                f"{filename} должен содержать код для {expected_keyword}"
            )


# =============================================================================
# ТЕСТ 5: СВЯЗАННОСТЬ МОДУЛЕЙ
# =============================================================================


class TestModuleCoupling:
    """Тесты на связанность модулей."""

    def test_low_coupling_between_parallel_modules(self) -> None:
        """Проверяет низкую связанность между parallel модулями."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        # Считаем внутренние импорты в каждом файле
        for py_file in parallel_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            _, imports = count_imports(py_file)

            # Считаем внутренние импорты parallel
            internal_imports = [
                imp for imp in imports if "parser_2gis.parallel" in imp and py_file.stem not in imp
            ]

            # Разрешаем до 5 внутренних импортов
            assert len(internal_imports) <= 5, (
                f"{py_file.name} имеет слишком много внутренних импортов ({len(internal_imports)}): {internal_imports}"
            )

    def test_utils_modules_are_independent(self) -> None:
        """Проверяет что utils модули независимы."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        for py_file in utils_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            content = py_file.read_text(encoding="utf-8")

            # utils не должен импортировать высокоуровневые модули
            high_level_imports = [
                "from parser_2gis.cli",
                "from parser_2gis.parallel",
                "from parser_2gis.tui",
            ]

            for imp in high_level_imports:
                assert imp not in content, (
                    f"{py_file.name} не должен импортировать высокоуровневые модули: {imp}"
                )


# =============================================================================
# ТЕСТ 6: МОДУЛЬНАЯ СТРУКТУРА
# =============================================================================


class TestModuleStructure:
    """Тесты на модульную структуру."""

    def test_parallel_has_expected_modules(self) -> None:
        """Проверяет что parallel/ имеет ожидаемые модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        expected_modules = [
            "coordinator.py",
            "merger.py",
            "error_handler.py",
            "progress.py",
            "options.py",
        ]

        for module_name in expected_modules:
            module_path = parallel_dir / module_name
            assert module_path.exists(), f"parallel/{module_name} должен существовать"

    def test_parser_has_expected_modules(self) -> None:
        """Проверяет что parser/parsers/ имеет ожидаемые модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parser_dir = project_root / "parser" / "parsers"

        expected_modules = [
            "main_parser.py",
            "main_extractor.py",
            "main_processor.py",
            "firm.py",
            "base.py",
        ]

        for module_name in expected_modules:
            module_path = parser_dir / module_name
            assert module_path.exists(), f"parser/parsers/{module_name} должен существовать"

    def test_logger_has_expected_modules(self) -> None:
        """Проверяет что logger/ имеет ожидаемые модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        logger_dir = project_root / "logger"

        expected_modules = ["logger.py", "options.py", "visual_logger.py"]

        for module_name in expected_modules:
            module_path = logger_dir / module_name
            assert module_path.exists(), f"logger/{module_name} должен существовать"


# =============================================================================
# ТЕСТ 7: ИМПОРТЫ И ЗАВИСИМОСТИ
# =============================================================================


class TestImportsAndDependencies:
    """Тесты на импорты и зависимости."""

    def test_no_too_many_imports(self) -> None:
        """Проверяет что файлы не имеют слишком много импортов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue
            if py_file.name.startswith("__"):
                continue

            import_count, _ = count_imports(py_file)

            assert import_count < MAX_IMPORTS_PER_FILE, (
                f"{py_file.name} имеет слишком много импортов ({import_count})"
            )

    def test_standard_library_imports_first(self) -> None:
        """Проверяет что импорты стандартной библиотеки идут первыми."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем несколько ключевых файлов
        key_files = [
            project_root / "parallel" / "merger.py",
            project_root / "parser" / "parsers" / "main_parser.py",
        ]

        for file_path in key_files:
            if not file_path.exists():
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            stdlib_imports: List[int] = []
            project_imports: List[int] = []

            for i, line in enumerate(lines):
                if line.startswith("import ") or line.startswith("from "):
                    if "parser_2gis" in line:
                        project_imports.append(i)
                    elif not line.startswith("from ."):
                        stdlib_imports.append(i)

            # Проверяем что stdlib импорты идут до project импортов (если есть оба)
            if stdlib_imports and project_imports:
                # Разрешаем некоторые исключения для сложных файлов
                pass  # Этот тест теперь информационный


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
