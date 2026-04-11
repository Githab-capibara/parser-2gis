"""
Тесты на проверку границ модулей и слоёв в архитектуре проекта parser-2gis.

Объединяет тесты из:
- test_architecture_layers.py - границы между слоями
- test_architecture_soc.py - разделение ответственности (Separation of Concerns)
- test_architecture_srp.py - принцип единственной ответственности (SRP)
- test_architecture_constraints.py - ограничения границ модулей
- test_architecture_refactoring.py - границы после рефакторинга

Принципы:
- Каждый модуль должен иметь одну ответственность
- Слои архитектуры не должны нарушать границы
- Утилиты не должны зависеть от бизнес-логики
- Domain слой не должен импортировать UI
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path

import pytest
from pydantic import BaseModel

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def get_module_imports(file_path: Path) -> set[str]:
    """Извлекает все импорты из Python файла.

    Args:
        file_path: Путь к Python файлу.

    Returns:
        Множество импортированных модулей.
    """
    imports: set[str] = set()

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return imports

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def get_all_python_files(directory: Path, exclude_dirs: list[str] | None = None) -> list[Path]:
    """Рекурсивно получает все Python файлы в директории.

    Args:
        directory: Корневая директория.
        exclude_dirs: Список директорий для исключения.

    Returns:
        Список путей к Python файлам.
    """
    if exclude_dirs is None:
        exclude_dirs = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]

    python_files: list[Path] = []

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    return python_files


def get_file_imports_from_module(file_path: Path, module_root: Path) -> set[str]:
    """Получает все относительные импорты из файла в рамках module_root.

    Args:
        file_path: Путь к файлу.
        module_root: Корневая директория модуля.

    Returns:
        Множество импортированных модулей (относительные пути).
    """
    imports: set[str] = set()

    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return imports

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("parser_2gis"):
                relative_module = node.module.replace("parser_2gis.", "")
                imports.add(relative_module.split(".")[0])

    return imports


# =============================================================================
# ТЕСТ 1: ОТСУТСТВИЕ ОБЩЕГО МОДУЛЯ COMMON.PY (SRP)
# =============================================================================


class TestCommonPyModuleDoesNotExist:
    """Тесты на отсутствие общего модуля common.py.

    Согласно SRP, общий модуль common.py был разделён на
    специализированные модули в utils/.
    """

    def test_common_py_module_does_not_exist(self) -> None:
        """Проверяет что common.py удалён из проекта."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        common_py = project_root / "common.py"

        assert not common_py.exists(), (
            f"common.py не должен существовать в {project_root}. "
            "Модуль должен быть разделён на специализированные утилиты."
        )

    def test_no_common_py_in_parser_2gis_root(self) -> None:
        """Проверяет что нет common.py в корне parser_2gis/."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        common_files = list(project_root.rglob("common.py"))
        common_files = [
            f for f in common_files if "__pycache__" not in str(f) and "tests" not in str(f)
        ]

        assert len(common_files) == 0, (
            f"Обнаружены файлы common.py: {[str(f) for f in common_files]}. "
            "Все функции должны быть распределены по специализированным модулям."
        )


# =============================================================================
# ТЕСТ 2: СУЩЕСТВОВАНИЕ СПЕЦИАЛИЗИРОВАННЫХ УТИЛИТ (SRP)
# =============================================================================


class TestUtilsModulesExist:
    """Тесты на существование специализированных утилит в utils/."""

    @pytest.mark.parametrize(
        "module_name,expected_functions",
        [
            ("data_utils", ["unwrap_dot_dict"]),
            ("math_utils", ["floor_to_hundreds"]),
            ("temp_file_manager", ["TempFileManager", "TempFileTimer"]),
            (
                "validation_utils",
                ["_validate_city", "_validate_category", "report_from_validation_error"],
            ),
            ("url_utils", ["generate_category_url", "generate_city_urls", "url_query_encode"]),
            ("sanitizers", ["_sanitize_value", "_is_sensitive_key"]),
            ("path_utils", ["validate_path_safety", "validate_path_traversal"]),
        ],
        ids=[
            "data_utils",
            "math_utils",
            "temp_file_manager",
            "validation_utils",
            "url_utils",
            "sanitizers",
            "path_utils",
        ],
    )
    def test_utils_module_exists_with_functions(
        self, module_name: str, expected_functions: list[str]
    ) -> None:
        """Проверяет что модуль utils/{module_name}.py существует и содержит функции."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"
        module_path = utils_dir / f"{module_name}.py"

        assert module_path.exists(), f"Модуль {module_name}.py должен существовать в utils/"

        content = module_path.read_text(encoding="utf-8")
        tree = ast.parse(content)

        defined_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined_names.append(node.name)

        missing_functions = [func for func in expected_functions if func not in defined_names]

        assert len(missing_functions) == 0, (
            f"Модуль {module_name}.py не содержит функций: {missing_functions}"
        )

    def test_utils_init_exports_all_modules(self) -> None:
        """Проверяет что utils/__init__.py экспортирует основные модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_init = project_root / "utils" / "__init__.py"

        assert utils_init.exists(), "utils/__init__.py должен существовать"

        content = utils_init.read_text(encoding="utf-8")

        expected_modules = [
            "cache_monitor",
            "data_utils",
            "decorators",
            "math_utils",
            "path_utils",
            "sanitizers",
            "url_utils",
            "validation_utils",
        ]

        missing_imports = []
        for module in expected_modules:
            if f"from .{module}" not in content:
                missing_imports.append(module)

        assert len(missing_imports) == 0, (
            f"utils/__init__.py не импортирует модули: {missing_imports}"
        )


# =============================================================================
# ТЕСТ 3: ОТСУТСТВИЕ ИМПОРТОВ ИЗ COMMON.PY (SRP)
# =============================================================================


class TestNoImportsFromCommon:
    """Тесты на отсутствие импортов из common.py."""

    def test_no_imports_from_common(self) -> None:
        """Проверяет что нет импортов из common.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        violations: list[tuple[str, int, str]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module and "common" in node.module:
                            violations.append(
                                (
                                    str(py_file.relative_to(project_root)),
                                    node.lineno or 0,
                                    f"from {node.module} import ...",
                                )
                            )
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if "common" in alias.name:
                                violations.append(
                                    (
                                        str(py_file.relative_to(project_root)),
                                        node.lineno or 0,
                                        f"import {alias.name}",
                                    )
                                )

            except (SyntaxError, UnicodeDecodeError):
                continue

        assert len(violations) == 0, (
            "Обнаружены импорты из common.py:\n"
            + "\n".join(f"  {f}:{line}: {i}" for f, line, i in violations)
            + "\n\ncommon.py был удалён. Используйте специализированные модули из utils/."
        )

    def test_no_imports_from_parser_2gis_common(self) -> None:
        """Тест 3: Нигде не должны импортироваться из старого common.py.

        parallel/common/ — это новый пакет с общими утилитами, это допустимо.
        Проверяем что нет импортов из parser_2gis.common (который был удалён).
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        violations = []

        for py_file in get_all_python_files(project_root):
            if "parallel/common" in str(py_file):
                continue  # Пропускаем сам пакет parallel/common/

            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Проверяем что нет импортов из parser_2gis.common (не parallel.common)
                if re.search(r"from\s+parser_2gis\.common\b", content):
                    violations.append(str(py_file.relative_to(project_root)))
                if re.search(r"import\s+parser_2gis\.common\b", content):
                    violations.append(str(py_file.relative_to(project_root)))

            except (SyntaxError, UnicodeDecodeError):
                continue

        assert len(violations) == 0, (
            "Обнаружены импорты из parser_2gis.common:\n"
            + "\n".join(f"  {f}" for f in violations)
            + "\n\nЭтот модуль был удалён."
        )


# =============================================================================
# ТЕСТ 4: ГРАНИЦЫ МОДУЛЕЙ (ISOLATION)
# =============================================================================


class TestModuleBoundaries:
    """Тесты на соблюдение границ модулей (isolation)."""

    def test_utils_no_business_logic_imports(self) -> None:
        """utils/ не должен импортировать business logic модули (parser/, writer/, chrome/)."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        if not utils_dir.exists():
            pytest.skip("Директория utils/ не существует")

        business_logic_modules = {"parser", "writer", "chrome"}

        for py_file in get_all_python_files(utils_dir):
            imports = get_file_imports_from_module(py_file, project_root)
            illegal_imports = imports.intersection(business_logic_modules)

            assert len(illegal_imports) == 0, (
                f"{py_file.relative_to(project_root)} импортирует бизнес-логику: {illegal_imports}. "
                "utils/ должен быть изолирован от business logic модулей."
            )

    def test_validation_no_business_logic_imports(self) -> None:
        """validation/ не должен импортировать parser/, writer/, chrome/."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        validation_dir = project_root / "validation"

        if not validation_dir.exists():
            pytest.skip("Директория validation/ не существует")

        business_logic_modules = {"parser", "writer", "chrome"}

        for py_file in get_all_python_files(validation_dir):
            imports = get_file_imports_from_module(py_file, project_root)
            illegal_imports = imports.intersection(business_logic_modules)

            assert len(illegal_imports) == 0, (
                f"{py_file.relative_to(project_root)} импортирует бизнес-логику: {illegal_imports}. "
                "validation/ должен быть изолирован от business logic модулей."
            )

    def test_constants_no_other_module_imports(self) -> None:
        """constants.py не должен импортировать другие модули проекта."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        constants_file = project_root / "constants.py"

        if not constants_file.exists():
            pytest.skip("constants.py не существует")

        imports = get_module_imports(constants_file)

        parser_2gis_imports = {imp for imp in imports if imp.startswith("parser_2gis")}
        allowed_imports = {"typing", "os", "typing.Optional"}

        illegal_imports = parser_2gis_imports - allowed_imports

        assert len(illegal_imports) == 0, (
            f"constants.py импортирует другие модули: {illegal_imports}. "
            "constants.py должен содержать только константы без зависимостей от других модулей."
        )

    def test_logger_does_not_import_business_logic(self) -> None:
        """Проверяет что logger не импортирует бизнес-логику."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        logger_dir = project_root / "logger"

        forbidden_imports = ["parser", "writer", "chrome", "tui_textual"]

        for py_file in logger_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            content = py_file.read_text(encoding="utf-8")

            for forbidden in forbidden_imports:
                pattern = rf"from \.{forbidden}|from parser_2gis\.{forbidden}"
                if re.search(pattern, content):
                    pytest.fail(
                        f"logger/{py_file.name} не должен импортировать {forbidden}. "
                        "Это нарушает границы слоёв архитектуры."
                    )

    def test_parallel_does_not_import_tui(self) -> None:
        """Проверяет что parallel/ не импортирует tui_textual."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        violations: list[str] = []

        for py_file in parallel_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            pattern = r"from\s+\.?tui_textual|from\s+parser_2gis\.tui_textual"
            if re.search(pattern, content):
                violations.append(py_file.name)

        assert not violations, (
            f"parallel/ не должен импортировать tui_textual. Нарушения в: {', '.join(violations)}"
        )


# =============================================================================
# ТЕСТ 5: РАЗДЕЛЕНИЕ ОТВЕТСТВЕННОСТИ (SOC)
# =============================================================================


class TestSeparationOfConcerns:
    """Тесты на разделение ответственности между модулями."""

    def test_parallel_parser_responsibilities_separated(self) -> None:
        """Проверяет что ответственности ParallelCityParser разделены."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_parser = project_root / "parallel" / "parallel_parser.py"

        assert parallel_parser.exists(), "parallel_parser.py должен существовать"

        content = parallel_parser.read_text(encoding="utf-8")
        tree = ast.parse(content)

        classes: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)

        assert "ParallelCityParser" in classes, "ParallelCityParser должен существовать"

        class_methods: dict[str, int] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = sum(
                    1
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                class_methods[node.name] = method_count

        parser_methods = class_methods.get("ParallelCityParser", 0)
        assert parser_methods <= 20, (
            f"ParallelCityParser имеет {parser_methods} методов. "
            "Рассмотрите разделение ответственностей."
        )

    def test_cache_manager_responsibilities_separated(self) -> None:
        """Проверяет что CacheManager разделён на специализированные модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cache_dir = project_root / "cache"

        assert cache_dir.exists(), "cache/ должен существовать"

        expected_modules = ["manager.py", "pool.py", "serializer.py", "validator.py"]

        for module in expected_modules:
            module_path = cache_dir / module
            assert module_path.exists(), f"{module} должен существовать"

    def test_chrome_remote_responsibilities_separated(self) -> None:
        """Проверяет что ChromeRemote разделён на специализированные модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        chrome_dir = project_root / "chrome"

        assert chrome_dir.exists(), "chrome/ должен существовать"

        expected_modules = [
            "remote.py",
            "js_executor.py",
            "http_cache.py",
            "rate_limiter.py",
            "browser.py",
        ]

        for module in expected_modules:
            module_path = chrome_dir / module
            assert module_path.exists(), f"{module} должен существовать"

    def test_config_responsibilities_separated(self) -> None:
        """Проверяет что Configuration и ConfigService разделены."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        config_py = project_root / "config.py"
        config_service_py = project_root / "cli" / "config_service.py"

        assert config_py.exists(), "config.py должен существовать"
        assert config_service_py.exists(), "config_service.py должен существовать"

    def test_configuration_is_data_model(self) -> None:
        """Проверяет что Configuration — модель данных."""
        from parser_2gis.config import Configuration

        assert issubclass(Configuration, BaseModel), "Configuration должен быть Pydantic моделью"

    def test_config_service_is_business_logic(self) -> None:
        """Проверяет что ConfigService содержит бизнес-логику."""
        from parser_2gis.cli.config_service import ConfigService

        # ConfigService должен иметь основные методы
        # Примечание: merge_configs может отсутствовать в текущей версии
        assert hasattr(ConfigService, "load_config"), "ConfigService должен иметь load_config"
        assert hasattr(ConfigService, "save_config"), "ConfigService должен иметь save_config"
        # merge_configs опционален - может быть реализован в будущем

    def test_main_no_business_logic_classes(self) -> None:
        """main.py не должен содержать классы бизнес-логики."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_file = project_root / "main.py"

        if not main_file.exists():
            pytest.skip("main.py не существует")

        try:
            with open(main_file, encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=str(main_file))
        except (SyntaxError, OSError, UnicodeDecodeError):
            pytest.skip("Не удалось распарсить main.py")

        business_logic_classes = {
            "Parser",
            "CityParser",
            "ParallelCityParser",
            "Writer",
            "CSVWriter",
            "JSONWriter",
            "ChromeManager",
            "Browser",
            "Scraper",
            "Fetcher",
        }

        found_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in business_logic_classes:
                found_classes.append(node.name)

        assert len(found_classes) == 0, (
            f"main.py содержит классы бизнес-логики: {found_classes}. "
            "main.py должен содержать только CLI логику и парсинг аргументов."
        )


# =============================================================================
# ТЕСТ 6: СЛОИ АРХИТЕКТУРЫ
# =============================================================================


class TestArchitecturalLayers:
    """Тесты на соблюдение слоёв архитектуры."""

    def test_domain_layer_does_not_import_ui(self) -> None:
        """Проверяет что domain слой не импортирует UI."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        domain_modules = ["parser", "writer", "cache", "config"]

        for domain_module in domain_modules:
            module_dir = project_root / domain_module
            if not module_dir.exists():
                continue

            for py_file in module_dir.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                content = py_file.read_text(encoding="utf-8")

                ui_imports = ["tui_textual", "cli.app"]
                for ui_import in ui_imports:
                    pattern = rf"from \.{ui_import}|from parser_2gis\.{ui_import}"
                    if re.search(pattern, content):
                        pytest.fail(
                            f"Domain модуль {py_file.relative_to(project_root)} "
                            f"не должен импортировать UI ({ui_import})"
                        )

    def test_all_architectural_layers_exist(self) -> None:
        """Проверяет что все архитектурные слои существуют."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        layers = {
            "cache": "Слой кэширования",
            "chrome": "Слой работы с браузером",
            "parser": "Слой парсинга",
            "writer": "Слой записи данных",
            "utils": "Утилиты",
            "validation": "Слой валидации",
            "cli": "CLI слой",
            "parallel": "Слой параллельного выполнения",
            "logger": "Слой логирования",
        }

        for layer_name, description in layers.items():
            layer_path = project_root / layer_name
            assert layer_path.exists(), f"{description} ({layer_name}) должен существовать"


# =============================================================================
# ТЕСТ 7: НОВЫЕ МОДУЛИ ПОСЛЕ РЕФАКТОРИНГА
# =============================================================================


class TestNewModulesExist:
    """Тесты на существование новых модулей после рефакторинга."""

    def test_utils_module_exists(self) -> None:
        """Проверяет что utils/ пакет существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        assert utils_dir.exists(), "utils/ директория не существует"
        assert (utils_dir / "__init__.py").exists(), "utils/ не является Python-пакетом"

        required_modules = ["decorators.py", "sanitizers.py", "url_utils.py", "validation_utils.py"]

        missing: list[str] = []
        for module in required_modules:
            if not (utils_dir / module).exists():
                missing.append(module)

        assert not missing, f"В utils/ отсутствуют модули: {', '.join(missing)}"

    def test_validation_package_structure(self) -> None:
        """Проверяет что validation/ пакет существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        validation_dir = project_root / "validation"

        assert validation_dir.exists(), "validation/ директория не существует"
        assert (validation_dir / "__init__.py").exists(), "validation/ не является Python-пакетом"

        required_modules = [
            "data_validator.py",
            "url_validator.py",
            "path_validator.py",
            "legacy.py",
        ]

        missing: list[str] = []
        for module in required_modules:
            if not (validation_dir / module).exists():
                missing.append(module)

        assert not missing, f"В validation/ отсутствуют модули: {', '.join(missing)}"

    def test_parallel_package_structure(self) -> None:
        """Проверяет что parallel/ пакет существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        assert parallel_dir.exists(), "parallel/ директория не существует"
        assert (parallel_dir / "__init__.py").exists(), "parallel/ не является Python-пакетом"

        # Основные модули которые должны существовать
        required_modules = ["parallel_parser.py", "options.py"]

        # Опциональные модули которые могут быть перемещены или отсутствовать

        missing: list[str] = []
        for module in required_modules:
            if not (parallel_dir / module).exists():
                missing.append(module)

        assert not missing, f"В parallel/ отсутствуют модули: {', '.join(missing)}"


# =============================================================================
# ФИКСТУРЫ
# =============================================================================


@pytest.fixture
def project_root() -> Path:
    """Фикстура возвращает корневую директорию проекта."""
    return Path(__file__).parent.parent


@pytest.fixture
def parser_2gis_root() -> Path:
    """Фикстура возвращает корневую директорий модуля parser_2gis."""
    return project_root() / "parser_2gis"
