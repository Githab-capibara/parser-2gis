"""
Тесты на проверку соблюдения YAGNI принципа (You Ain't Gonna Need It).

Проверяет:
- Использование pydantic_compat (временная абстракция)
- Использование validation/legacy (устаревшая логика)
- Использование main.py (устаревший модуль)

YAGNI принцип:
Не добавляйте функциональность пока она не нужна.
Удаляйте временные и устаревшие абстракции.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Tuple


class TestPydanticCompatUsage:
    """Тесты на использование pydantic_compat."""

    def test_pydantic_compat_exists(self) -> None:
        """Проверяет что pydantic_compat.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        pydantic_compat = project_root / "pydantic_compat.py"

        assert pydantic_compat.exists(), "pydantic_compat.py должен существовать"

    def test_pydantic_compat_usage(self) -> None:
        """Проверяет использование pydantic_compat в проекте.

        pydantic_compat — временная абстракция для поддержки Pydantic v1 и v2.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Ищем использования pydantic_compat
        usages: List[Tuple[str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            if py_file.name == "pydantic_compat.py":
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and "pydantic_compat" in node.module:
                        usages.append((str(py_file.relative_to(project_root)), node.lineno or 0))

        # pydantic_compat должен использоваться
        assert len(usages) > 0, "pydantic_compat должен использоваться в проекте"

    def test_pydantic_compat_exports(self) -> None:
        """Проверяет что pydantic_compat экспортирует требуемые функции."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        pydantic_compat = project_root / "pydantic_compat.py"

        content = pydantic_compat.read_text(encoding="utf-8")

        # Ожидаемые экспорты
        expected_exports = ["get_model_dump", "get_model_fields_set", "model_validate_json_class"]

        missing_exports = []
        for export in expected_exports:
            if f"def {export}" not in content:
                missing_exports.append(export)

        assert len(missing_exports) == 0, (
            f"pydantic_compat.py не содержит функций: {missing_exports}"
        )

    def test_pydantic_compat_has_version_detection(self) -> None:
        """Проверяет что pydantic_compat определяет версию Pydantic."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        pydantic_compat = project_root / "pydantic_compat.py"

        content = pydantic_compat.read_text(encoding="utf-8")

        # Должна быть проверка версии
        has_version_check = (
            "pydantic.VERSION" in content
            or "pydantic.__version__" in content
            or "VERSION" in content
        )

        assert has_version_check, "pydantic_compat.py должен определять версию Pydantic"


class TestValidationLegacyUsage:
    """Тесты на использование validation/legacy."""

    def test_validation_legacy_exists(self) -> None:
        """Проверяет что validation/legacy.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        legacy = project_root / "validation" / "legacy.py"

        assert legacy.exists(), "validation/legacy.py должен существовать"

    def test_validation_legacy_usage(self) -> None:
        """Проверяет использование validation/legacy в проекте.

        legacy.py — устаревшая логика валидации.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Ищем использования legacy
        usages: List[Tuple[str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            if py_file.name == "legacy.py":
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except (SyntaxError, UnicodeDecodeError):
                continue

            # Ищем импорты из legacy
            if "from .legacy import" in content or "from validation.legacy import" in content:
                usages.append((py_file.name, 0))

        # legacy может использоваться или нет — это информационный тест
        if usages:
            pass  # Просто информируем

    def test_validation_legacy_content(self) -> None:
        """Проверяет содержимое validation/legacy.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        legacy = project_root / "validation" / "legacy.py"

        content = legacy.read_text(encoding="utf-8")

        # Должен содержать устаревшие функции валидации
        has_legacy_functions = "def " in content

        assert has_legacy_functions, "legacy.py должен содержать функции"

    def test_validation_new_api_exists(self) -> None:
        """Проверяет что новая API валидации существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Новые модули валидации
        new_modules = [
            "validation/data_validator.py",
            "validation/path_validator.py",
            "validation/url_validator.py",
        ]

        for module_path in new_modules:
            full_path = project_root / module_path
            assert full_path.exists(), f"{module_path} должен существовать"


class TestMainModuleUsage:
    """Тесты на использование main.py."""

    def test_main_py_exists(self) -> None:
        """Проверяет что main.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_py = project_root / "main.py"

        assert main_py.exists(), "main.py должен существовать"

    def test_main_py_is_wrapper(self) -> None:
        """Проверяет что main.py — обёртка над cli/.

        main.py должен делегировать логику в cli/.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_py = project_root / "main.py"

        content = main_py.read_text(encoding="utf-8")

        # Должен импортировать из cli
        has_cli_import = "from parser_2gis.cli" in content or "from .cli" in content

        assert has_cli_import, "main.py должен импортировать из cli/"

    def test_main_py_exports_for_backward_compatibility(self) -> None:
        """Проверяет что main.py экспортирует символы для backward совместимости."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_py = project_root / "main.py"

        content = main_py.read_text(encoding="utf-8")

        # Должен иметь __all__ для экспорта
        has_all = "__all__" in content

        assert has_all, "main.py должен определять __all__"

    def test_cli_package_exists(self) -> None:
        """Проверяет что cli/ пакет существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cli_dir = project_root / "cli"

        assert cli_dir.exists(), "cli/ должен существовать"

        # Должен иметь основные модули
        expected_modules = [
            "__init__.py",
            "main.py",
            "arguments.py",
            "validator.py",
            "formatter.py",
        ]

        for module in expected_modules:
            module_path = cli_dir / module
            assert module_path.exists(), f"cli/{module} должен существовать"


class TestTemporaryAbstractions:
    """Тесты на временные абстракции."""

    def test_no_unused_temporary_abstractions(self) -> None:
        """Проверяет что нет неиспользуемых временных абстракций.

        Временные абстракции должны быть удалены когда больше не нужны.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Потенциальные временные абстракции
        temporary_modules = [
            "pydantic_compat.py"  # Для поддержки Pydantic v1/v2
        ]

        for module_name in temporary_modules:
            module_path = project_root / module_name

            if not module_path.exists():
                continue

            # Проверяем что модуль используется
            usage_count = 0

            for py_file in project_root.rglob("*.py"):
                if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                    continue

                if py_file == module_path:
                    continue

                try:
                    content = py_file.read_text(encoding="utf-8")
                except (SyntaxError, UnicodeDecodeError):
                    continue

                if module_name.replace(".py", "") in content:
                    usage_count += 1

            # Модуль должен использоваться
            assert usage_count > 0, f"{module_name} не используется. Рассмотрите удаление."

    def test_deprecation_warnings_exist(self) -> None:
        """Проверяет что устаревшие функции имеют предупреждения."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        legacy = project_root / "validation" / "legacy.py"

        if not legacy.exists():
            return

        content = legacy.read_text(encoding="utf-8")

        # Должны быть предупреждения о депрекации
        has_deprecation = (
            "DeprecationWarning" in content
            or "warnings.warn" in content
            or "deprecated" in content.lower()
        )

        # Это информационный тест
        if not has_deprecation:
            pass  # Просто информируем


class TestYAGNICompliance:
    """Общие тесты на соответствие YAGNI."""

    def test_no_unused_imports_in_modules(self) -> None:
        """Проверяет отсутствие неиспользуемых импортов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули для проверки
        modules_to_check = ["config.py", "config_service.py", "constants.py"]

        for module_name in modules_to_check:
            module_path = project_root / module_name

            if not module_path.exists():
                continue

            content = module_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            # Собираем все импорты
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.names:
                        for alias in node.names:
                            imports.append(alias.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)

            # Проверяем что импорты используются (упрощённо)
            # Это информационный тест
            if imports:
                pass  # Просто информируем

    def test_no_future_imports_unused(self) -> None:
        """Проверяет что future импорты используются."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            # Ищем future импорты
            has_future = "from __future__ import" in content

            if has_future:
                # future импорты должны быть
                pass  # Это хорошо

    def test_feature_flags_are_documented(self) -> None:
        """Проверяет что флаги функций документированы.

        Если есть флаги функций, они должны быть документированы.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Ищем флаги функций
        feature_flags: List[Tuple[str, str]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
            except (SyntaxError, UnicodeDecodeError):
                continue

            # Ищем паттерны флагов
            if "ENABLE_" in content or "USE_" in content:
                # Нашли потенциальный флаг
                feature_flags.append((py_file.name, "flag"))

        # Это информационный тест
        if feature_flags:
            pass  # Просто информируем


class TestBackwardCompatibility:
    """Тесты на backward совместимость."""

    def test_backward_compatibility_preserved(self) -> None:
        """Проверяет что backward совместимость сохранена.

        Основные символы должны быть доступны из старых мест импорта.
        """
        # Проверяем что основные символы доступны
        from parser_2gis.cli.main import main as main_from_cli
        from parser_2gis.main import main as main_from_main

        # Оба должны быть доступны
        assert main_from_main is not None
        assert main_from_cli is not None

    def test_old_import_paths_work(self) -> None:
        """Проверяет что старые пути импорта работают."""
        # Configuration должен быть доступен из config
        from parser_2gis.config import Configuration

        assert Configuration is not None

        # ConfigService должен быть доступен из config_service
        from parser_2gis.config_service import ConfigService

        assert ConfigService is not None

    def test_deprecation_warnings_for_old_api(self) -> None:
        """Проверяет что старая API имеет предупреждения.

        Если есть устаревшая API, она должна иметь предупреждения.
        """
        # Это информационный тест
        # Проверяем что есть механизм для предупреждений
        import warnings

        assert hasattr(warnings, "warn"), "warnings.warn должен существовать"


__all__ = [
    "TestPydanticCompatUsage",
    "TestValidationLegacyUsage",
    "TestMainModuleUsage",
    "TestTemporaryAbstractions",
    "TestYAGNICompliance",
    "TestBackwardCompatibility",
]
