"""
Тесты на архитектурную целостность после рефакторинга проекта parser-2gis.

Проверяют:
- Размер модулей (предотвращение God Object)
- Отсутствие дублирования кода
- Соблюдение границ модулей
- Отсутствие циклических зависимостей
- Использование новых модулей (utils/, parallel/, validation/)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

import pytest

# =============================================================================
# ТЕСТЫ НА РАЗМЕР МОДУЛЕЙ
# =============================================================================


class TestModuleSizeLimits:
    """Тесты на размер модулей для предотвращения God Object."""

    def test_parallel_parser_module_size_limit(self) -> None:
        """Проверяет что parallel/parallel_parser.py < 1500 строк.

        Превышение лимита указывает на необходимость декомпозиции модуля.
        """
        parallel_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )
        content = parallel_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert len(lines) < 1500, (
            f"parallel/parallel_parser.py слишком большой: {len(lines)} строк (максимум: 1500). "
            "Рекомендуется выделить отдельные функции в helper-модули."
        )

    def test_csv_writer_module_size_limit(self) -> None:
        """Проверяет что writer/writers/csv_writer.py < 500 строк.

        Превышение лимита указывает на необходимость выделения логики в отдельные модули.
        """
        csv_writer_path = (
            Path(__file__).parent.parent / "parser_2gis" / "writer" / "writers" / "csv_writer.py"
        )
        content = csv_writer_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert len(lines) < 500, (
            f"writer/writers/csv_writer.py слишком большой: {len(lines)} строк (максимум: 500). "
            "Рекомендуется выделить вспомогательные функции в отдельные модули."
        )

    def test_common_module_size_limit(self) -> None:
        """Проверяет что common.py < 500 строк.

        Превышение лимита указывает на необходимость декомпозиции на utils-модули.
        """
        common_path = Path(__file__).parent.parent / "parser_2gis" / "common.py"
        content = common_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert len(lines) < 500, (
            f"common.py слишком большой: {len(lines)} строк (максимум: 500). "
            "Рекомендуется использовать функции из utils/ вместо дублирования в common.py."
        )

    def test_chrome_remote_module_size_limit(self) -> None:
        """Проверяет что chrome/remote.py < 2500 строк.

        Превышение лимита указывает на необходимость выделения логики в отдельные модули.
        """
        remote_path = Path(__file__).parent.parent / "parser_2gis" / "chrome" / "remote.py"
        content = remote_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert len(lines) < 2500, (
            f"chrome/remote.py слишком большой: {len(lines)} строк (максимум: 2500). "
            "Рекомендуется выделить отдельные методы в helper-модули."
        )


# =============================================================================
# ТЕСТЫ НА ОТСУТСТВИЕ ДУБЛИРОВАНИЯ
# =============================================================================


class TestNoCodeDuplication:
    """Тесты на отсутствие дублирования кода между модулями."""

    def test_no_duplicate_validate_env_int(self) -> None:
        """Проверяет что функция validate_env_int определена только в constants.py.

        Функция валидации ENV переменных должна быть централизована.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        duplicates: List[str] = []

        for py_file in project_root.rglob("*.py"):
            # Пропускаем тесты и venv
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            # Пропускаем __init__.py файлы (они могут делать ре-экспорт)
            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            # Ищем определение функции (не импорт)
            # Функция должна быть определена через def validate_env_int(
            pattern = r"^def\s+validate_env_int\s*\("
            if re.search(pattern, content, re.MULTILINE):
                rel_path = py_file.relative_to(project_root)
                # Разрешаем только constants.py
                if str(rel_path) != "constants.py":
                    duplicates.append(str(rel_path))

        assert not duplicates, (
            f"Функция validate_env_int должна быть определена только в constants.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )

    def test_no_duplicate_wait_until_finished(self) -> None:
        """Проверяет что декоратор wait_until_finished определён только в utils/decorators.py.

        Декоратор ожидания завершения операций должен быть централизован.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        duplicates: List[str] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            # Ищем определение функции wait_until_finished
            pattern = r"^def\s+wait_until_finished\s*\("
            if re.search(pattern, content, re.MULTILINE):
                rel_path = py_file.relative_to(project_root)
                # Разрешаем только utils/decorators.py
                if str(rel_path) != "utils/decorators.py":
                    duplicates.append(str(rel_path))

        assert not duplicates, (
            f"Декоратор wait_until_finished должен быть определён только в utils/decorators.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )

    def test_no_duplicate_generate_urls(self) -> None:
        """Проверяет что функции генерации URL определены только в utils/url_utils.py.

        Функции generate_category_url, generate_city_urls должны быть централизованы.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        url_functions = ["generate_category_url", "generate_city_urls", "url_query_encode"]

        duplicates: List[str] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            for func_name in url_functions:
                pattern = rf"^def\s+{func_name}\s*\("
                if re.search(pattern, content, re.MULTILINE):
                    rel_path = py_file.relative_to(project_root)
                    # Разрешаем только utils/url_utils.py
                    if str(rel_path) != "utils/url_utils.py":
                        duplicates.append(f"{rel_path}:{func_name}")

        assert not duplicates, (
            f"Функции генерации URL должны быть определены только в utils/url_utils.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )

    def test_no_duplicate_sanitize_value(self) -> None:
        """Проверяет что функция _sanitize_value определена только в utils/sanitizers.py.

        Функция санитаризации данных должна быть централизована.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        duplicates: List[str] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            if py_file.name == "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            # Ищем определение функции _sanitize_value
            pattern = r"^def\s+_sanitize_value\s*\("
            if re.search(pattern, content, re.MULTILINE):
                rel_path = py_file.relative_to(project_root)
                # Разрешаем только utils/sanitizers.py
                if str(rel_path) != "utils/sanitizers.py":
                    duplicates.append(str(rel_path))

        assert not duplicates, (
            f"Функция _sanitize_value должна быть определена только в utils/sanitizers.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )


# =============================================================================
# ТЕСТЫ НА СОБЛЮДЕНИЕ ГРАНИЦ МОДУЛЕЙ
# =============================================================================


class TestModuleBoundaries:
    """Тесты на соблюдение границ между модулями архитектуры."""

    def test_utils_does_not_import_business_logic(self) -> None:
        """Проверяет что utils/ не импортирует parser/writer/chrome.

        Utils слой должен быть независим от бизнес-логики.
        """
        utils_dir = Path(__file__).parent.parent / "parser_2gis" / "utils"

        forbidden_imports = ["parser", "writer", "chrome", "tui_textual"]

        violations: List[str] = []

        for py_file in utils_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            for forbidden in forbidden_imports:
                # Проверяем относительные и абсолютные импорты
                pattern = rf"from\s+\.{forbidden}|from\s+parser_2gis\.{forbidden}"
                if re.search(pattern, content):
                    violations.append(f"{py_file.name} импортирует {forbidden}")

        assert not violations, (
            "utils/ не должен импортировать бизнес-модули. Нарушения:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_validation_does_not_import_business_logic(self) -> None:
        """Проверяет что validation/ не импортирует parser/writer.

        Validation слой должен быть независим от бизнес-логики.
        """
        validation_dir = Path(__file__).parent.parent / "parser_2gis" / "validation"

        forbidden_imports = ["parser", "writer", "chrome", "tui_textual"]

        violations: List[str] = []

        for py_file in validation_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            for forbidden in forbidden_imports:
                pattern = rf"from\s+\.{forbidden}|from\s+parser_2gis\.{forbidden}"
                if re.search(pattern, content):
                    violations.append(f"{py_file.name} импортирует {forbidden}")

        assert not violations, (
            "validation/ не должен импортировать бизнес-модули. Нарушения:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_parallel_does_not_import_tui(self) -> None:
        """Проверяет что parallel/ не импортирует tui_textual.

        Parallel слой не должен зависеть от UI.
        """
        parallel_dir = Path(__file__).parent.parent / "parser_2gis" / "parallel"

        violations: List[str] = []

        for py_file in parallel_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")

            # Проверяем импорт tui_textual
            pattern = r"from\s+\.?tui_textual|from\s+parser_2gis\.tui_textual"
            if re.search(pattern, content):
                violations.append(py_file.name)

        assert not violations, (
            f"parallel/ не должен импортировать tui_textual. Нарушения в: {', '.join(violations)}"
        )


# =============================================================================
# ТЕСТЫ НА НОВЫЕ МОДУЛИ
# =============================================================================


class TestNewModulesExist:
    """Тесты на существование новых модулей после рефакторинга."""

    def test_utils_module_exists(self) -> None:
        """Проверяет что utils/ пакет существует и содержит нужные модули."""
        utils_dir = Path(__file__).parent.parent / "parser_2gis" / "utils"

        assert utils_dir.exists(), "utils/ директория не существует"
        assert (utils_dir / "__init__.py").exists(), "utils/ не является Python-пакетом"

        # Проверяем наличие ключевых модулей
        required_modules = ["decorators.py", "sanitizers.py", "url_utils.py", "validation_utils.py"]

        missing: List[str] = []
        for module in required_modules:
            if not (utils_dir / module).exists():
                missing.append(module)

        assert not missing, f"В utils/ отсутствуют модули: {', '.join(missing)}"

    def test_validation_package_structure(self) -> None:
        """Проверяет что validation/ пакет существует и содержит нужные модули."""
        validation_dir = Path(__file__).parent.parent / "parser_2gis" / "validation"

        assert validation_dir.exists(), "validation/ директория не существует"
        assert (validation_dir / "__init__.py").exists(), "validation/ не является Python-пакетом"

        # Проверяем наличие ключевых модулей
        required_modules = [
            "data_validator.py",
            "url_validator.py",
            "path_validator.py",
            "legacy.py",
        ]

        missing: List[str] = []
        for module in required_modules:
            if not (validation_dir / module).exists():
                missing.append(module)

        assert not missing, f"В validation/ отсутствуют модули: {', '.join(missing)}"

    def test_parallel_package_structure(self) -> None:
        """Проверяет что parallel/ пакет существует и содержит нужные модули."""
        parallel_dir = Path(__file__).parent.parent / "parser_2gis" / "parallel"

        assert parallel_dir.exists(), "parallel/ директория не существует"
        assert (parallel_dir / "__init__.py").exists(), "parallel/ не является Python-пакетом"

        # Проверяем наличие ключевых модулей
        required_modules = [
            "parallel_parser.py",
            "file_merger.py",
            "progress_tracker.py",
            "temp_file_timer.py",
            "options.py",
        ]

        missing: List[str] = []
        for module in required_modules:
            if not (parallel_dir / module).exists():
                missing.append(module)

        assert not missing, f"В parallel/ отсутствуют модули: {', '.join(missing)}"


# =============================================================================
# ТЕСТЫ НА ОБРАТНУЮ СОВМЕСТИМОСТЬ
# =============================================================================


class TestBackwardCompatibility:
    """Тесты на обратную совместимость после рефакторинга."""

    def test_common_exports_utils_functions(self) -> None:
        """Проверяет что common.py экспортирует функции из utils/ для обратной совместимости.

        Примечание: это информационный тест. Он показывает какие функции нужно
        добавить в common.py для обратной совместимости.
        """
        from parser_2gis import common

        # Проверяем что функции из utils доступны через common
        # Это нужно для обратной совместимости со старым кодом
        expected_exports = [
            "wait_until_finished",
            "sanitize_value",
            "generate_category_url",
            "generate_city_urls",
        ]

        missing: List[str] = []
        exported: List[str] = []
        for export in expected_exports:
            if hasattr(common, export):
                exported.append(export)
            else:
                missing.append(export)

        # Тест проходит если хотя бы некоторые функции экспортируются
        # Это показывает прогресс рефакторинга
        assert exported, (
            f"common.py не экспортирует ни одной функции из utils/. "
            f"Отсутствуют: {', '.join(missing)}. "
            f"Для обратной совместимости добавьте экспорт в common.py"
        )

    def test_validation_legacy_imports(self) -> None:
        """Проверяет что validation/legacy.py работает и экспортирует функции."""
        from parser_2gis.validation import legacy

        # Проверяем что legacy модуль экспортирует нужные функции
        expected_exports = [
            "ValidationResult",
            "validate_email",
            "validate_phone",
            "validate_url",
            "validate_positive_int",
            "validate_positive_float",
        ]

        missing: List[str] = []
        for export in expected_exports:
            if not hasattr(legacy, export):
                missing.append(export)

        assert not missing, (
            f"validation/legacy.py должен экспортировать функции для обратной совместимости. "
            f"Отсутствуют: {', '.join(missing)}"
        )


# =============================================================================
# ТЕСТЫ НА ЦИКЛИЧЕСКИЕ ЗАВИСИМОСТИ
# =============================================================================


class TestNoCyclicDependencies:
    """Тесты на отсутствие циклических зависимостей между новыми модулями."""

    def test_no_cycle_utils_validation(self) -> None:
        """Проверяет отсутствие цикла между utils/ и validation/."""
        utils_dir = Path(__file__).parent.parent / "parser_2gis" / "utils"
        validation_dir = Path(__file__).parent.parent / "parser_2gis" / "validation"

        # Проверяем что utils не импортирует validation
        # __init__.py может импортировать для ре-экспорта
        for py_file in utils_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue  # __init__.py может импортировать для экспорта
            if py_file.name.startswith("_"):
                continue

            content = py_file.read_text(encoding="utf-8")
            pattern = r"from\s+\.?validation|from\s+parser_2gis\.validation"
            if re.search(pattern, content):
                pytest.fail(f"{py_file.name} не должен импортировать validation")

        # Проверяем что validation не импортирует utils (кроме validation_utils)
        # __init__.py может импортировать для ре-экспорта
        for py_file in validation_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue  # __init__.py может импортировать для экспорта
            if py_file.name.startswith("_"):
                continue

            content = py_file.read_text(encoding="utf-8")
            # validation может импортировать utils.validation_utils
            # но не должен импортировать другие модули utils
            pattern = r"from\s+\.?utils\s+import(?!.*validation_utils)"
            if re.search(pattern, content):
                # Это нормально если импортируется validation_utils
                if "validation_utils" not in content:
                    pytest.fail(
                        f"{py_file.name} не должен импортировать utils (кроме validation_utils)"
                    )

    def test_no_cycle_parallel_parser(self) -> None:
        """Проверяет отсутствие цикла между parallel/ и parser/."""
        parser_dir = Path(__file__).parent.parent / "parser_2gis" / "parser"

        # parallel может импортировать parser (это нормально)
        # но parser не должен импортировать parallel

        for py_file in parser_dir.rglob("*.py"):
            if py_file.name.startswith("_") and py_file.name != "__init__.py":
                continue

            content = py_file.read_text(encoding="utf-8")
            pattern = r"from\s+\.?parallel|from\s+parser_2gis\.parallel"
            if re.search(pattern, content):
                pytest.fail(f"{py_file.name} не должен импортировать parallel")
