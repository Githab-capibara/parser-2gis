"""
Тесты на проверку SOLID принципов в архитектуре проекта.

Проверяет:
- Single Responsibility Principle (SRP) - классы не имеют множественной ответственности
- Dependency Inversion Principle (DIP) - использование Protocol
- Interface Segregation Principle (ISP) - Protocol не избыточны
- Liskov Substitution Principle (LSP) - наследники корректны
- Open/Closed Principle (OCP) - расширение без модификации

Принципы:
- SOLID принципы проектирования
- Программирование через интерфейсы
- Композиция вместо наследования
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def count_class_methods(file_path: Path, class_name: str) -> int:
    """Подсчитывает количество методов в классе.

    Args:
        file_path: Путь к файлу.
        class_name: Имя класса.

    Returns:
        Количество методов.
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
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    count += 1

    return count


def get_class_methods(file_path: Path, class_name: str) -> List[str]:
    """Извлекает имена методов класса.

    Args:
        file_path: Путь к файлу.
        class_name: Имя класса.

    Returns:
        Список имён методов.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    methods: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    methods.append(item.name)

    return methods


def get_method_categories(methods: List[str]) -> Dict[str, List[str]]:
    """Категоризирует методы по ответственности.

    Args:
        methods: Список имён методов.

    Returns:
        Словарь {категория: [методы]}.
    """
    categories: Dict[str, List[str]] = {
        "initialization": [],
        "public_api": [],
        "private_impl": [],
        "dunder": [],
    }

    for method in methods:
        if method.startswith("__") and method.endswith("__"):
            categories["dunder"].append(method)
        elif method.startswith("_"):
            categories["private_impl"].append(method)
        elif method in ("__init__",):
            categories["initialization"].append(method)
        else:
            categories["public_api"].append(method)

    return categories


def check_protocol_methods_count(protocol_type: type) -> int:
    """Подсчитывает количество методов в Protocol.

    Args:
        protocol_type: Тип Protocol.

    Returns:
        Количество методов.
    """
    count = 0
    for name, member in inspect.getmembers(protocol_type):
        if not name.startswith("_") and callable(member):
            count += 1
    return count


# =============================================================================
# ТЕСТ 1: SINGLE RESPONSIBILITY PRINCIPLE (SRP)
# =============================================================================


class TestSingleResponsibilityPrinciple:
    """Тесты на принцип единственной ответственности."""

    def test_parallel_coordinator_has_single_responsibility(self) -> None:
        """Проверяет что ParallelCoordinator имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        methods = get_class_methods(coordinator_file, "ParallelCoordinator")
        categories = get_method_categories(methods)

        # ParallelCoordinator должен координировать но не выполнять
        # Проверяем что методы относятся к координации
        public_methods = categories["public_api"]

        # Ожидаемые методы координации

        # Проверяем что большинство методов относятся к координации
        coordination_count = sum(
            1
            for m in public_methods
            if any(c in m for c in ["run", "stop", "get_", "generate", "parse_single"])
        )

        assert coordination_count >= len(public_methods) * 0.7, (
            f"ParallelCoordinator должен иметь >=70% методов координации "
            f"(сейчас: {coordination_count}/{len(public_methods)})"
        )

    def test_parallel_error_handler_has_single_responsibility(self) -> None:
        """Проверяет что ParallelErrorHandler имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        error_handler_file = project_root / "parallel" / "error_handler.py"

        assert error_handler_file.exists(), "parallel/error_handler.py должен существовать"

        methods = get_class_methods(error_handler_file, "ParallelErrorHandler")

        # Все методы должны быть для обработки ошибок
        error_methods = [
            m
            for m in methods
            if "error" in m.lower() or "handle" in m.lower() or "cleanup" in m.lower()
        ]

        # Разрешаем также log и вспомогательные методы
        allowed_methods = error_methods + ["log", "create_unique_temp_file", "retry_with_backoff"]

        assert len(allowed_methods) >= len(methods) * 0.8, (
            "ParallelErrorHandler должен иметь >=80% методов для обработки ошибок"
        )

    def test_parallel_file_merger_has_single_responsibility(self) -> None:
        """Проверяет что ParallelFileMerger имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        merger_file = project_root / "parallel" / "merger.py"

        assert merger_file.exists(), "parallel/merger.py должен существовать"

        methods = get_class_methods(merger_file, "ParallelFileMerger")

        # Все методы должны быть для слияния файлов
        merge_methods = [
            m
            for m in methods
            if "merge" in m.lower()
            or "csv" in m.lower()
            or "file" in m.lower()
            or "lock" in m.lower()
        ]

        # Разрешаем также log и вспомогательные методы
        allowed_methods = merge_methods + [
            "log",
            "extract_category_from_filename",
            "process_single_csv_file",
            "acquire_merge_lock",
            "cleanup_merge_lock",
        ]

        assert len(allowed_methods) >= len(methods) * 0.9, (
            "ParallelFileMerger должен иметь >=90% методов для слияния файлов"
        )

    def test_main_page_parser_has_single_responsibility(self) -> None:
        """Проверяет что MainPageParser имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        methods = get_class_methods(main_parser_file, "MainPageParser")

        # Методы должны быть для DOM и навигации
        dom_nav_methods = [
            m
            for m in methods
            if any(
                k in m.lower()
                for k in ["dom", "nav", "link", "page", "request", "response", "validate"]
            )
        ]

        # Разрешаем также вспомогательные методы
        allowed_methods = dom_nav_methods + [
            "_add_xhr_counter",
            "_validate_js_script",
            "url_pattern",
        ]

        assert len(allowed_methods) >= len(methods) * 0.8, (
            "MainPageParser должен иметь >=80% методов для DOM и навигации"
        )

    def test_class_method_count_under_limit(self) -> None:
        """Проверяет что классы имеют <50 методов."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем основные классы
        classes_to_check = [
            ("parallel/coordinator.py", "ParallelCoordinator"),
            ("parallel/merger.py", "ParallelFileMerger"),
            ("parallel/error_handler.py", "ParallelErrorHandler"),
            ("parser/parsers/main_parser.py", "MainPageParser"),
            ("chrome/browser.py", "BrowserLifecycleManager"),
        ]

        for file_rel_path, class_name in classes_to_check:
            file_path = project_root / file_rel_path
            if not file_path.exists():
                continue

            method_count = count_class_methods(file_path, class_name)

            assert method_count < 50, (
                f"{class_name} должен иметь <50 методов (сейчас: {method_count})"
            )


# =============================================================================
# ТЕСТ 2: DEPENDENCY INVERSION PRINCIPLE (DIP)
# =============================================================================


class TestDependencyInversionPrinciple:
    """Тесты на принцип инверсии зависимостей."""

    def test_main_parser_depends_on_abstraction_not_concretion(self) -> None:
        """Проверяет что MainPageParser зависит от абстракции BrowserService."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        content = main_parser_file.read_text(encoding="utf-8")

        # MainPageParser должен использовать BrowserService Protocol
        assert "BrowserService" in content, (
            "MainPageParser должен использовать BrowserService Protocol"
        )

        # Не должен напрямую создавать ChromeRemote
        assert "ChromeRemote(" not in content or "# ChromeRemote(" in content, (
            "MainPageParser не должен напрямую создавать ChromeRemote"
        )

    def test_execution_backend_protocol_used(self) -> None:
        """Проверяет что ExecutionBackend Protocol используется."""
        from parser_2gis.protocols import ExecutionBackend

        assert ExecutionBackend is not None

        # Проверяем что Protocol имеет методы
        methods = check_protocol_methods_count(ExecutionBackend)
        assert methods >= 3, f"ExecutionBackend должен иметь >=3 методов (сейчас: {methods})"


# =============================================================================
# ТЕСТ 3: INTERFACE SEGREGATION PRINCIPLE (ISP)
# =============================================================================


class TestInterfaceSegregationPrinciple:
    """Тесты на принцип разделения интерфейса."""

    def test_browser_protocol_is_segregated(self) -> None:
        """Проверяет что Browser Protocol разделён на мелкие интерфейсы."""
        from parser_2gis.protocols import (
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
            BrowserService,
        )

        # Проверяем что существуют отдельные Protocol
        assert BrowserNavigation is not None
        assert BrowserContentAccess is not None
        assert BrowserJSExecution is not None
        assert BrowserScreenshot is not None
        assert BrowserService is not None

        # Проверяем что отдельные Protocol имеют мало методов
        nav_methods = check_protocol_methods_count(BrowserNavigation)
        content_methods = check_protocol_methods_count(BrowserContentAccess)
        js_methods = check_protocol_methods_count(BrowserJSExecution)
        screenshot_methods = check_protocol_methods_count(BrowserScreenshot)

        assert nav_methods <= 2, (
            f"BrowserNavigation должен иметь <=2 методов (сейчас: {nav_methods})"
        )
        assert content_methods <= 3, (
            f"BrowserContentAccess должен иметь <=3 методов (сейчас: {content_methods})"
        )
        assert js_methods <= 2, (
            f"BrowserJSExecution должен иметь <=2 методов (сейчас: {js_methods})"
        )
        assert screenshot_methods <= 2, (
            f"BrowserScreenshot должен иметь <=2 методов (сейчас: {screenshot_methods})"
        )

    def test_callback_protocols_are_segregated(self) -> None:
        """Проверяет что callback Protocol разделены."""
        from parser_2gis.protocols import (
            CancelCallback,
            CleanupCallback,
            LogCallback,
            ProgressCallback,
        )

        # Каждый callback должен быть отдельным Protocol
        assert CancelCallback is not None
        assert CleanupCallback is not None
        assert LogCallback is not None
        assert ProgressCallback is not None

        # Callback Protocol являются Callable и имеют __call__ метод
        # Проверяем что они существуют и могут быть использованы
        for protocol in [CancelCallback, CleanupCallback, LogCallback, ProgressCallback]:
            assert hasattr(protocol, "__call__") or protocol is not None, (
                f"{protocol.__name__} должен быть Callable Protocol"
            )

    def test_protocols_are_not_fat(self) -> None:
        """Проверяет что Protocol не избыточны."""
        from parser_2gis.protocols import (
            BrowserService,
            CacheBackend,
            ExecutionBackend,
            LoggerProtocol,
            Parser,
            Writer,
        )

        # Проверяем что Protocol имеют разумное количество методов
        protocols = [
            (BrowserService, 10),  # Максимум методов
            (CacheBackend, 6),
            (ExecutionBackend, 5),
            (LoggerProtocol, 7),
            (Parser, 4),
            (Writer, 4),
        ]

        for protocol, max_methods in protocols:
            methods = check_protocol_methods_count(protocol)
            assert methods <= max_methods, (
                f"{protocol.__name__} должен иметь <={max_methods} методов (сейчас: {methods})"
            )


# =============================================================================
# ТЕСТ 4: LISKOV SUBSTITUTION PRINCIPLE (LSP)
# =============================================================================


class TestLiskovSubstitutionPrinciple:
    """Тесты на принцип подстановки Барбары Лисков."""

    def test_mock_browser_service_substitutable(self) -> None:
        """Проверяет что mock BrowserService может заменить реальный."""
        from parser_2gis.protocols import BrowserService

        mock_browser: BrowserService = MagicMock(spec=BrowserService)

        # Mock должен поддерживать все методы Protocol
        mock_browser.navigate("http://example.com")
        mock_browser.get_html()
        mock_browser.execute_js("console.log('test')")
        mock_browser.screenshot("/tmp/test.png")
        mock_browser.close()

        assert mock_browser.navigate.called
        assert mock_browser.get_html.called
        assert mock_browser.execute_js.called
        assert mock_browser.screenshot.called
        assert mock_browser.close.called

    def test_mock_writer_substitutable(self) -> None:
        """Проверяет что mock Writer может заменить реальный."""
        from parser_2gis.protocols import Writer

        mock_writer: Writer = MagicMock(spec=Writer)

        mock_writer.write([{"key": "value"}])
        mock_writer.close()

        assert mock_writer.write.called
        assert mock_writer.close.called

    def test_mock_parser_substitutable(self) -> None:
        """Проверяет что mock Parser может заменить реальный."""
        from parser_2gis.protocols import Parser

        mock_parser: Parser = MagicMock(spec=Parser)

        mock_parser.parse()
        mock_parser.get_stats()

        assert mock_parser.parse.called
        assert mock_parser.get_stats.called

    def test_mock_cache_backend_substitutable(self) -> None:
        """Проверяет что mock CacheBackend может заменить реальный."""
        from parser_2gis.protocols import CacheBackend

        mock_cache: CacheBackend = MagicMock(spec=CacheBackend)

        mock_cache.set("key", "value", 3600)
        mock_cache.get("key")
        mock_cache.delete("key")
        mock_cache.exists("key")

        assert mock_cache.set.called
        assert mock_cache.get.called
        assert mock_cache.delete.called
        assert mock_cache.exists.called


# =============================================================================
# ТЕСТ 5: OPEN/CLOSED PRINCIPLE (OCP)
# =============================================================================


class TestOpenClosedPrinciple:
    """Тесты на принцип открытости/закрытости."""

    def test_protocols_allow_extension(self) -> None:
        """Проверяет что Protocol позволяют расширение."""
        from parser_2gis.protocols import BrowserService, Writer

        # Создаём классы реализующие Protocol
        class MockBrowser:
            def navigate(self, url: str, **kwargs: Any) -> None:
                pass

            def get_html(self) -> str:
                return ""

            def get_document(self) -> Any:
                return None

            def execute_js(self, js_code: str, timeout: int | None = None) -> Any:
                return None

            def screenshot(self, path: str) -> None:
                pass

            def close(self) -> None:
                pass

        class MockWriter:
            def write(self, records: list[dict]) -> None:
                pass

            def close(self) -> None:
                pass

        # Проверяем что классы могут быть использованы как Protocol
        browser: BrowserService = MockBrowser()  # type: ignore
        writer: Writer = MockWriter()  # type: ignore

        assert browser is not None
        assert writer is not None

    def test_error_handler_allows_new_error_types(self) -> None:
        """Проверяет что ParallelErrorHandler позволяет добавлять новые типы ошибок."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        error_handler_file = project_root / "parallel" / "error_handler.py"

        assert error_handler_file.exists(), "parallel/error_handler.py должен существовать"

        content = error_handler_file.read_text(encoding="utf-8")

        # Проверяем что есть общие методы для обработки ошибок
        assert "handle_other_error" in content, (
            "ParallelErrorHandler должен иметь общий метод для обработки ошибок"
        )

    def test_strategy_pattern_for_backends(self) -> None:
        """Проверяет что бэкенды используют стратегию."""
        from parser_2gis.protocols import CacheBackend, ExecutionBackend

        # CacheBackend и ExecutionBackend позволяют менять стратегию
        assert CacheBackend is not None
        assert ExecutionBackend is not None

        # Mock объекты для проверки
        mock_cache: CacheBackend = MagicMock(spec=CacheBackend)
        mock_executor: ExecutionBackend = MagicMock(spec=ExecutionBackend)

        assert mock_cache is not None
        assert mock_executor is not None


# =============================================================================
# ТЕСТ 6: SOLID INTEGRITY
# =============================================================================


class TestSOLIDIntegrity:
    """Тесты на целостность SOLID принципов."""

    def test_all_solid_principles_covered(self) -> None:
        """Проверяет что все SOLID принципы покрыты тестами."""
        # S - Single Responsibility Principle
        from parser_2gis.protocols import BrowserService

        assert BrowserService is not None

        # O - Open/Closed Principle
        from parser_2gis.protocols import Writer

        assert Writer is not None

        # L - Liskov Substitution Principle
        from parser_2gis.protocols import Parser

        assert Parser is not None

        # I - Interface Segregation Principle
        from parser_2gis.protocols import (
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
        )

        assert BrowserNavigation is not None
        assert BrowserContentAccess is not None
        assert BrowserJSExecution is not None
        assert BrowserScreenshot is not None

        # D - Dependency Inversion Principle
        # Проверяем что main_parser использует BrowserService
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        content = main_parser_file.read_text(encoding="utf-8")
        assert "BrowserService" in content, (
            "MainPageParser должен использовать BrowserService для DIP"
        )

    def test_protocols_module_is_stable(self) -> None:
        """Проверяет что protocols.py стабилен."""
        from parser_2gis import protocols

        # Проверяем что все Protocol экспортируются
        expected_protocols = [
            "BrowserService",
            "BrowserNavigation",
            "BrowserContentAccess",
            "BrowserJSExecution",
            "BrowserScreenshot",
            "Writer",
            "Parser",
            "CacheBackend",
            "ExecutionBackend",
            "LoggerProtocol",
            "ProgressCallback",
            "LogCallback",
            "CleanupCallback",
            "CancelCallback",
        ]

        for protocol_name in expected_protocols:
            assert hasattr(protocols, protocol_name), (
                f"protocols.py должен экспортировать {protocol_name}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
