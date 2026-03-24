"""
Тесты на архитектурную целостность проекта parser-2gis.

Проверяют:
- Отсутствие циклических зависимостей между модулями
- Соблюдение границ модулей
- Размер модулей (предотвращение God Object)
- Использование централизованных констант
- Иерархию исключений
- Зависимости между слоями архитектуры
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


class TestModuleSizeLimits:
    """Тесты на размер модулей для предотвращения God Object."""

    def test_main_module_size_limit(self) -> None:
        """Проверяет что main.py не превышает разумный размер."""
        main_path = Path(__file__).parent.parent / "parser_2gis" / "main.py"
        content = main_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # main.py не должен превышать 2000 строк
        # При превышении рекомендуется декомпозировать на специализированные модули
        assert len(lines) < 2000, (
            f"main.py слишком большой: {len(lines)} строк (максимум: 2000). "
            "Рекомендуется декомпозировать на специализированные модули."
        )

    def test_common_module_size_limit(self) -> None:
        """Проверяет что common.py не превышает разумный размер."""
        common_path = Path(__file__).parent.parent / "parser_2gis" / "common.py"
        content = common_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # common.py не должен превышать 1500 строк
        # При превышении рекомендуется разделить на decorators.py, sanitizers.py, url_utils.py
        assert len(lines) < 1500, (
            f"common.py слишком большой: {len(lines)} строк (максимум: 1500). "
            "Рекомендуется разделить на decorators.py, sanitizers.py, url_utils.py."
        )

    def test_parallel_parser_module_size_limit(self) -> None:
        """Проверяет что parallel/parallel_parser.py не превышает разумный размер."""
        parallel_path = (
            Path(__file__).parent.parent / "parser_2gis" / "parallel" / "parallel_parser.py"
        )
        content = parallel_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        # parallel/parallel_parser.py не должен превышать 1500 строк
        # После разделения на подмодули
        assert len(lines) < 1500, (
            f"parallel/parallel_parser.py слишком большой: {len(lines)} строк (максимум: 1500). "
            "Рекомендуется дальнейшее разделение."
        )


class TestCircularDependencies:
    """Тесты на отсутствие циклических зависимостей."""

    def test_no_circular_imports_common_logger(self) -> None:
        """Проверяет отсутствие цикла common.py ↔ logger.py."""
        common_path = Path(__file__).parent.parent / "parser_2gis" / "common.py"
        logger_path = Path(__file__).parent.parent / "parser_2gis" / "logger" / "logger.py"

        common_content = common_path.read_text(encoding="utf-8")
        logger_content = logger_path.read_text(encoding="utf-8")

        # Проверяем что common.py не импортирует logger напрямую в глобальной области
        common_imports_logger = (
            "from .logger import" in common_content
            or "from parser_2gis.logger import" in common_content
        )

        # Проверяем что logger.py не импортирует common напрямую в глобальной области
        logger_imports_common = (
            "from .common import" in logger_content
            or "from parser_2gis.common import" in logger_content
        )

        # Цикл возникает если оба модуля импортируют друг друга
        assert not (common_imports_logger and logger_imports_common), (
            "Обнаружена циклическая зависимость: common.py ↔ logger.py. "
            "Используйте interfaces.py с Protocol для разрыва цикла."
        )

    def test_no_circular_imports_main_config(self) -> None:
        """Проверяет отсутствие цикла main.py ↔ config.py."""
        config_path = Path(__file__).parent.parent / "parser_2gis" / "config.py"

        config_content = config_path.read_text(encoding="utf-8")

        # config.py не должен импортировать main.py
        config_imports_main = (
            "from .main import" in config_content
            or "from parser_2gis.main import" in config_content
        )

        assert not config_imports_main, (
            "Обнаружена циклическая зависимость: main.py ↔ config.py. "
            "config.py не должен импортировать main.py."
        )


class TestModuleBoundaries:
    """Тесты на соблюдение границ модулей."""

    def test_logger_does_not_import_business_logic(self) -> None:
        """Проверяет что logger не импортирует бизнес-логику."""
        logger_dir = Path(__file__).parent.parent / "parser_2gis" / "logger"

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

    def test_constants_does_not_import_business_logic(self) -> None:
        """Проверяет что constants.py не импортирует бизнес-логику."""
        constants_path = Path(__file__).parent.parent / "parser_2gis" / "constants.py"
        content = constants_path.read_text(encoding="utf-8")

        forbidden_imports = ["parser", "writer", "chrome", "tui_textual", "cli"]

        for forbidden in forbidden_imports:
            pattern = rf"from \.{forbidden}|from parser_2gis\.{forbidden}"
            if re.search(pattern, content):
                pytest.fail(
                    f"constants.py не должен импортировать {forbidden}. "
                    "Константы должны быть независимы."
                )


class TestCentralizedConstants:
    """Тесты на использование централизованных констант."""

    def test_no_duplicate_max_data_depth(self) -> None:
        """Проверяет что MAX_DATA_DEPTH определена только в constants.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        duplicates = []

        for py_file in project_root.rglob("*.py"):
            if py_file.name == "constants.py":
                continue

            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            content = py_file.read_text(encoding="utf-8")

            # Ищем определение константы (не импорт)
            pattern = r"^MAX_DATA_DEPTH\s*:\s*int\s*=\s*\d+"
            if re.search(pattern, content, re.MULTILINE):
                duplicates.append(str(py_file.relative_to(project_root)))

        assert not duplicates, (
            f"MAX_DATA_DEPTH должна быть определена только в constants.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )

    def test_no_duplicate_buffer_constants(self) -> None:
        """Проверяет что буферные константы определены только в constants.py."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        buffer_constants = [
            "DEFAULT_BUFFER_SIZE",
            "MERGE_BUFFER_SIZE",
            "CSV_BATCH_SIZE",
            "MERGE_BATCH_SIZE",
        ]

        duplicates = []

        for py_file in project_root.rglob("*.py"):
            if py_file.name in ("constants.py", "common.py"):
                continue

            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            content = py_file.read_text(encoding="utf-8")

            for const_name in buffer_constants:
                pattern = rf"^{const_name}\s*:\s*int\s*=\s*\d+"
                if re.search(pattern, content, re.MULTILINE):
                    duplicates.append(f"{py_file.relative_to(project_root)}:{const_name}")

        assert not duplicates, (
            f"Буферные константы должны быть определены только в constants.py. "
            f"Найдены дубликаты в: {', '.join(duplicates)}"
        )


class TestExceptionHierarchy:
    """Тесты на иерархию исключений."""

    def test_base_contextual_exception_exists(self) -> None:
        """Проверяет что BaseContextualException существует."""
        from parser_2gis.exceptions import BaseContextualException

        assert BaseContextualException is not None
        assert issubclass(BaseContextualException, Exception)

    def test_parser_exception_inherits_base(self) -> None:
        """Проверяет что ParserException наследуется от BaseContextualException."""
        from parser_2gis.exceptions import BaseContextualException
        from parser_2gis.parser.exceptions import ParserException

        assert issubclass(ParserException, BaseContextualException)

    def test_writer_exception_inherits_base(self) -> None:
        """Проверяет что WriterUnknownFileFormat наследуется от BaseContextualException."""
        from parser_2gis.exceptions import BaseContextualException
        from parser_2gis.writer.exceptions import WriterUnknownFileFormat

        assert issubclass(WriterUnknownFileFormat, BaseContextualException)

    def test_chrome_exception_has_context_attributes(self) -> None:
        """Проверяет что ChromeException имеет атрибуты контекста."""
        try:
            from parser_2gis.chrome.exceptions import ChromeException

            exc = ChromeException("test message")

            # Проверяем наличие атрибутов базового класса
            assert hasattr(exc, "function_name"), "ChromeException должна иметь function_name"
            assert hasattr(exc, "line_number"), "ChromeException должна иметь line_number"
            assert hasattr(exc, "filename"), "ChromeException должна иметь filename"

        except ImportError:
            pytest.skip("Chrome модуль недоступен")


class TestDependencyInjection:
    """Тесты на использование Dependency Injection."""

    def test_protocols_module_exists(self) -> None:
        """Проверяет что protocols.py существует и экспортирует Protocol."""
        from parser_2gis import protocols

        assert hasattr(protocols, "ProgressCallback")
        assert hasattr(protocols, "LogCallback")
        assert hasattr(protocols, "Writer")
        assert hasattr(protocols, "Parser")

    def test_logger_protocol_in_protocols(self) -> None:
        """Проверяет что LoggerProtocol находится в protocols.py."""
        from parser_2gis import protocols

        assert hasattr(protocols, "LoggerProtocol")

    def test_validation_package_exists(self) -> None:
        """Проверяет что validation/ пакет существует."""
        from parser_2gis import validation

        assert hasattr(validation, "PathValidator")
        assert hasattr(validation, "validate_path")
        assert hasattr(validation, "validate_url")


class TestCodeQuality:
    """Тесты на качество кода."""

    def test_no_todo_fixme_in_code(self) -> None:
        """Проверяет отсутствие TODO/FIXME комментариев в коде."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        files_with_todos = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            content = py_file.read_text(encoding="utf-8")

            if re.search(r"#\s*(TODO|FIXME|XXX|HACK)\b", content, re.IGNORECASE):
                files_with_todos.append(str(py_file.relative_to(project_root)))

        # Это предупреждение, а не ошибка
        if files_with_todos:
            pytest.fail(
                f"Найдены TODO/FIXME комментарии в {len(files_with_todos)} файлах:\n"
                + "\n".join(f"  - {f}" for f in files_with_todos[:10])
                + ("\n  ..." if len(files_with_todos) > 10 else "")
            )

    def test_no_debug_imports_in_production(self) -> None:
        """Проверяет отсутствие отладочных импортов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        debug_modules = ["pdb", "ipdb", "debugpy"]

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "venv" in py_file.parts:
                continue

            content = py_file.read_text(encoding="utf-8")

            for debug_module in debug_modules:
                pattern = rf"import\s+{debug_module}|from\s+{debug_module}\s+import"
                if re.search(pattern, content):
                    pytest.fail(
                        f"{py_file.relative_to(project_root)} содержит отладочный импорт: {debug_module}"
                    )


class TestArchitecturalLayers:
    """Тесты на соблюдение слоёв архитектуры."""

    def test_domain_layer_does_not_import_ui(self) -> None:
        """Проверяет что domain слой не импортирует UI."""
        domain_modules = ["parser", "writer", "cache", "common", "config"]

        project_root = Path(__file__).parent.parent / "parser_2gis"

        for domain_module in domain_modules:
            module_dir = project_root / domain_module
            if not module_dir.exists():
                continue

            for py_file in module_dir.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                content = py_file.read_text(encoding="utf-8")

                # Проверяем что domain не импортирует UI
                ui_imports = ["tui_textual", "cli.app"]
                for ui_import in ui_imports:
                    pattern = rf"from \.{ui_import}|from parser_2gis\.{ui_import}"
                    if re.search(pattern, content):
                        pytest.fail(
                            f"Domain модуль {py_file.relative_to(project_root)} "
                            f"не должен импортировать UI ({ui_import})"
                        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
