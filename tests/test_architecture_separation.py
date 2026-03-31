"""
Тесты на проверку разделения ответственности (Separation of Concerns).

Проверяет что:
- parallel/coordinator.py не содержит логики слияния файлов
- parallel/merger.py не содержит логики парсинга
- parser/parsers/main_parser.py не содержит бизнес-логики
- Каждый модуль имеет одну чёткую ответственность

Принципы:
- Single Responsibility Principle (SRP)
- Модули не должны смешивать разные уровни абстракции
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Set

import pytest

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def get_class_names(file_path: Path) -> Set[str]:
    """Извлекает имена всех классов из Python файла.

    Args:
        file_path: Путь к Python файлу.

    Returns:
        Множество имён классов.
    """
    class_names: Set[str] = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return class_names

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return class_names

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            class_names.add(node.name)

    return class_names


def get_function_names(file_path: Path) -> Set[str]:
    """Извлекает имена всех функций из Python файла.

    Args:
        file_path: Путь к Python файлу.

    Returns:
        Множество имён функций.
    """
    function_names: Set[str] = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return function_names

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return function_names

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            function_names.add(node.name)

    return function_names


def get_method_calls_in_class(file_path: Path, class_name: str) -> Set[str]:
    """Извлекает имена методов вызываемых в классе.

    Args:
        file_path: Путь к Python файлу.
        class_name: Имя класса для анализа.

    Returns:
        Множество имён вызываемых методов.
    """
    method_calls: Set[str] = set()

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return method_calls

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return method_calls

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Attribute):
                        method_calls.add(child.func.attr)
                    elif isinstance(child.func, ast.Name):
                        method_calls.add(child.func.id)

    return method_calls


def contains_pattern(file_path: Path, patterns: List[str]) -> List[str]:
    """Проверяет содержит ли файл указанные паттерны.

    Args:
        file_path: Путь к Python файлу.
        patterns: Список паттернов для поиска.

    Returns:
        Список найденных паттернов.
    """
    found_patterns: List[str] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return found_patterns

    for pattern in patterns:
        if pattern in content:
            found_patterns.append(pattern)

    return found_patterns


# =============================================================================
# ТЕСТ 1: PARALLEL/COORDINATOR НЕ СОДЕРЖИТ ЛОГИКИ СЛИЯНИЯ
# =============================================================================


class TestCoordinatorNoMergeLogic:
    """Тесты на отсутствие логики слияния в coordinator.py."""

    def test_coordinator_no_csv_merge_code(self) -> None:
        """Проверяет что coordinator.py не содержит кода слияния CSV."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        # Паттерны которые указывают на логику слияния CSV
        merge_patterns = [
            "csv.DictReader",
            "csv.DictWriter",
            "MERGE_BUFFER_SIZE",
            "MERGE_BATCH_SIZE",
            "fieldnames_cache",
            "process_single_csv_file",
            "extract_category_from_filename",
        ]

        found_patterns = contains_pattern(coordinator_file, merge_patterns)

        assert len(found_patterns) == 0, (
            f"coordinator.py не должен содержать логики слияния CSV:\n"
            f"Найдены паттерны: {found_patterns}"
        )

    def test_coordinator_uses_merger_class(self) -> None:
        """Проверяет что coordinator использует ParallelFileMerger для слияния."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # coordinator должен импортировать и использовать ParallelFileMerger
        assert "ParallelFileMerger" in content, (
            "coordinator.py должен использовать ParallelFileMerger для слияния"
        )
        assert "self._file_merger" in content, (
            "coordinator.py должен иметь экземпляр ParallelFileMerger"
        )
        assert "self._file_merger.merge_csv_files" in content, (
            "coordinator.py должен вызывать merge_csv_files через ParallelFileMerger"
        )

    def test_coordinator_classes_no_merge_methods(self) -> None:
        """Проверяет что классы в coordinator.py не имеют методов слияния."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        class_names = get_class_names(coordinator_file)

        # Методы которые указывают на логику слияния
        merge_method_patterns = [
            "merge_csv",
            "merge_files",
            "process_csv",
            "extract_category",
            "get_csv_files",
        ]

        for class_name in class_names:
            get_method_calls_in_class(coordinator_file, class_name)

            for merge_pattern in merge_method_patterns:
                # Проверяем что нет методов с такими названиями (не вызовов)
                content = coordinator_file.read_text(encoding="utf-8")
                # Ищем определения методов а не вызовы
                method_def_pattern = f"def {merge_pattern}"
                assert method_def_pattern not in content, (
                    f"Класс {class_name} не должен содержать методов слияния: {merge_pattern}"
                )


# =============================================================================
# ТЕСТ 2: PARALLEL/MERGER НЕ СОДЕРЖИТ ЛОГИКИ ПАРСИНГА
# =============================================================================


class TestMergerNoParsingLogic:
    """Тесты на отсутствие логики парсинга в merger.py."""

    def test_merger_no_browser_code(self) -> None:
        """Проверяет что merger.py не содержит кода работы с браузером."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        merger_file = project_root / "parallel" / "merger.py"

        assert merger_file.exists(), "parallel/merger.py должен существовать"

        # Паттерны которые указывают на логику парсинга/браузера
        browser_patterns = [
            "ChromeRemote",
            "BrowserService",
            "execute_js",
            "get_document",
            "get_html",
            "navigate",
            "screenshot",
            "DOMNode",
            "parse_firm",
        ]

        found_patterns = contains_pattern(merger_file, browser_patterns)

        assert len(found_patterns) == 0, (
            f"merger.py не должен содержать логики работы с браузером:\n"
            f"Найдены паттерны: {found_patterns}"
        )

    def test_merger_no_parser_imports(self) -> None:
        """Проверяет что merger.py не импортирует модули парсера."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        merger_file = project_root / "parallel" / "merger.py"

        assert merger_file.exists(), "parallel/merger.py должен существовать"

        content = merger_file.read_text(encoding="utf-8")

        # merger не должен импортировать модули парсера
        parser_imports = [
            "from parser_2gis.parser",
            "from .parser",
            "import parser_2gis.parser",
            "MainPageParser",
            "MainDataExtractor",
            "FirmParser",
        ]

        found_imports = [imp for imp in parser_imports if imp in content]

        assert len(found_imports) == 0, (
            f"merger.py не должен импортировать модули парсера:\nНайдены импорты: {found_imports}"
        )

    def test_merger_only_csv_operations(self) -> None:
        """Проверяет что merger.py содержит только CSV операции."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        merger_file = project_root / "parallel" / "merger.py"

        assert merger_file.exists(), "parallel/merger.py должен существовать"

        class_names = get_class_names(merger_file)

        # Ожидаемые классы в merger.py (включая dataclass для конфигурации)
        expected_classes = {"ParallelFileMerger", "MergeConfig"}

        assert class_names == expected_classes, (
            f"merger.py должен содержать только классы для слияния файлов:\n"
            f"Ожидаемые: {expected_classes}, Найдены: {class_names}"
        )


# =============================================================================
# ТЕСТ 3: PARSER/MAIN_PARSER НЕ СОДЕРЖИТ БИЗНЕС-ЛОГИКИ
# =============================================================================


class TestMainParserNoBusinessLogic:
    """Тесты на отсутствие бизнес-логики в main_parser.py."""

    def test_main_parser_no_data_extraction_logic(self) -> None:
        """Проверяет что main_parser.py не содержит логики извлечения данных."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        # Паттерны которые указывают на логику извлечения данных
        extraction_patterns = [
            "extract_firm_data",
            "extract_name",
            "extract_address",
            "extract_phone",
            "extract_website",
            "extract_rating",
            "extract_reviews_count",
            "_parse_firm_entry",
            "_extract_field",
        ]

        found_patterns = contains_pattern(main_parser_file, extraction_patterns)

        # main_parser.py может содержать некоторые методы извлечения для DOM операций
        # но не должен содержать бизнес-логики обработки данных
        # Проверяем что нет сложных методов извлечения
        business_logic_patterns = ["extract_firm_data", "_parse_firm_entry"]

        found_business = [p for p in business_logic_patterns if p in found_patterns]

        assert len(found_business) == 0, (
            f"main_parser.py не должен содержать бизнес-логики извлечения:\n"
            f"Найдены паттерны: {found_business}"
        )

    def test_main_parser_responsibility_is_dom_and_navigation(self) -> None:
        """Проверяет что main_parser.py отвечает только за DOM и навигацию."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        content = main_parser_file.read_text(encoding="utf-8")

        # Ожидаемые методы для DOM и навигации
        expected_methods = [
            "_get_links",
            "_go_page",
            "_navigate_to_search",
            "_get_available_pages",
            "_validate_document_response",
        ]

        found_expected = [method for method in expected_methods if method in content]

        assert len(found_expected) >= 3, (
            f"main_parser.py должен содержать методы для DOM и навигации:\n"
            f"Ожидаемые: {expected_methods}, Найдены: {found_expected}"
        )

    def test_main_parser_uses_browser_service_protocol(self) -> None:
        """Проверяет что main_parser.py использует BrowserService Protocol."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        content = main_parser_file.read_text(encoding="utf-8")

        # main_parser.py должен использовать BrowserService Protocol
        assert "BrowserService" in content, (
            "main_parser.py должен использовать BrowserService Protocol"
        )
        assert (
            "browser: Optional[BrowserService]" in content or "browser: BrowserService" in content
        ), "main_parser.py должен принимать BrowserService через dependency injection"


# =============================================================================
# ТЕСТ 4: РАЗДЕЛЕНИЕ ОТВЕТСТВЕННОСТИ МЕЖДУ МОДУЛЯМИ
# =============================================================================


class TestSeparationOfConcernsBetweenModules:
    """Тесты на разделение ответственности между модулями."""

    def test_error_handler_no_parsing_logic(self) -> None:
        """Проверяет что error_handler.py не содержит логики парсинга."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        error_handler_file = project_root / "parallel" / "error_handler.py"

        assert error_handler_file.exists(), "parallel/error_handler.py должен существовать"

        # Паттерны которые указывают на логику парсинга
        parsing_patterns = ["parse_firm", "extract_data", "get_document", "execute_js", "DOMNode"]

        found_patterns = contains_pattern(error_handler_file, parsing_patterns)

        assert len(found_patterns) == 0, (
            f"error_handler.py не должен содержать логики парсинга:\n"
            f"Найдены паттерны: {found_patterns}"
        )

    def test_progress_reporter_no_business_logic(self) -> None:
        """Проверяет что progress.py не содержит бизнес-логики."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        progress_file = project_root / "parallel" / "progress.py"

        assert progress_file.exists(), "parallel/progress.py должен существовать"

        # Паттерны которые указывают на бизнес-логику
        business_patterns = ["parse_firm", "extract_data", "merge_csv", "create_browser"]

        found_patterns = contains_pattern(progress_file, business_patterns)

        assert len(found_patterns) == 0, (
            f"progress.py не должен содержать бизнес-логики:\nНайдены паттерны: {found_patterns}"
        )

    def test_each_module_has_single_responsibility(self) -> None:
        """Проверяет что каждый модуль parallel/ имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        # Ожидаемые ответственности модулей
        module_responsibilities = {
            "coordinator.py": ["координация", "запуск", "управление"],
            "merger.py": ["слияние", "объединение", "CSV"],
            "error_handler.py": ["ошибки", "обработка", "retry"],
            "progress.py": ["прогресс", "отчёт", "статистика"],
        }

        for module_name, expected_keywords in module_responsibilities.items():
            module_file = parallel_dir / module_name

            if not module_file.exists():
                continue

            content = module_file.read_text(encoding="utf-8").lower()

            # Проверяем что модуль содержит ожидаемые ключевые слова
            found_keywords = [kw for kw in expected_keywords if kw in content]

            assert len(found_keywords) > 0, (
                f"{module_name} должен содержать код для {expected_keywords}"
            )


# =============================================================================
# ТЕСТ 5: КЛАССЫ ИМЕЮТ ЧЁТКУЮ ОТВЕТСТВЕННОСТЬ
# =============================================================================


class TestClassResponsibilityClarity:
    """Тесты на чёткую ответственность классов."""

    def test_parallel_coordinator_responsibility(self) -> None:
        """Проверяет ответственность ParallelCoordinator."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        class_names = get_class_names(coordinator_file)

        assert "ParallelCoordinator" in class_names, (
            "coordinator.py должен содержать класс ParallelCoordinator"
        )

        # ParallelCoordinator должен координировать но не выполнять
        content = coordinator_file.read_text(encoding="utf-8")

        # Должен использовать делегирование
        assert "self._error_handler" in content, (
            "ParallelCoordinator должен делегировать обработку ошибок"
        )
        assert "self._file_merger" in content, (
            "ParallelCoordinator должен делегировать слияние файлов"
        )
        assert "self._progress_reporter" in content, (
            "ParallelCoordinator должен делегировать отчёт о прогрессе"
        )

    def test_parallel_file_merger_responsibility(self) -> None:
        """Проверяет ответственность ParallelFileMerger."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        merger_file = project_root / "parallel" / "merger.py"

        assert merger_file.exists(), "parallel/merger.py должен существовать"

        class_names = get_class_names(merger_file)

        assert "ParallelFileMerger" in class_names, (
            "merger.py должен содержать класс ParallelFileMerger"
        )

        # ParallelFileMerger должен только сливать файлы
        content = merger_file.read_text(encoding="utf-8")

        # Должен содержать только методы для слияния
        expected_methods = [
            "merge_csv_files",
            "get_csv_files_list",
            "extract_category_from_filename",
            "process_single_csv_file",
        ]

        found_methods = [method for method in expected_methods if method in content]

        assert len(found_methods) >= 3, (
            f"ParallelFileMerger должен содержать методы для слияния:\n"
            f"Ожидаемые: {expected_methods}, Найдены: {found_methods}"
        )

    def test_parallel_error_handler_responsibility(self) -> None:
        """Проверяет ответственность ParallelErrorHandler."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        error_handler_file = project_root / "parallel" / "error_handler.py"

        assert error_handler_file.exists(), "parallel/error_handler.py должен существовать"

        class_names = get_class_names(error_handler_file)

        assert "ParallelErrorHandler" in class_names, (
            "error_handler.py должен содержать класс ParallelErrorHandler"
        )

        # ParallelErrorHandler должен только обрабатывать ошибки
        content = error_handler_file.read_text(encoding="utf-8")

        # Должен содержать методы для обработки различных ошибок
        expected_methods = [
            "handle_chrome_error",
            "handle_timeout_error",
            "handle_memory_error",
            "handle_init_error",
            "handle_other_error",
        ]

        found_methods = [method for method in expected_methods if method in content]

        assert len(found_methods) >= 3, (
            f"ParallelErrorHandler должен содержать методы для обработки ошибок:\n"
            f"Ожидаемые: {expected_methods}, Найдены: {found_methods}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
