"""
Дополнительные SOLID тесты для архитектуры проекта.

Проверяет:
- SRP для parallel модулей
- DIP используется
- ISP соблюдается
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

import pytest

# =============================================================================
# ТЕСТ 1: Single Responsibility Principle для parallel модулей
# =============================================================================


class TestSingleResponsibilityParallel:
    """Тесты на SRP для parallel модулей."""

    def _count_method_categories(self, file_path: Path, class_name: str) -> Dict[str, int]:
        """Подсчитывает методы по категориям ответственности.

        Args:
            file_path: Путь к файлу.
            class_name: Имя класса.

        Returns:
            Словарь {категория: количество методов}.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return {}

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return {}

        categories: Dict[str, int] = {
            "coordination": 0,
            "error_handling": 0,
            "file_operations": 0,
            "logging": 0,
            "data_processing": 0,
            "other": 0,
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_name = item.name.lower()

                        if any(k in method_name for k in ["run", "stop", "start", "generate"]):
                            categories["coordination"] += 1
                        elif any(k in method_name for k in ["error", "handle", "cleanup"]):
                            categories["error_handling"] += 1
                        elif any(k in method_name for k in ["file", "merge", "write", "read"]):
                            categories["file_operations"] += 1
                        elif method_name == "log":
                            categories["logging"] += 1
                        elif any(k in method_name for k in ["parse", "process", "validate"]):
                            categories["data_processing"] += 1
                        else:
                            categories["other"] += 1

        return categories

    def test_parallel_coordinator_has_single_responsibility(self) -> None:
        """Проверка что ParallelCoordinator имеет одну ответственность.

        ParallelCoordinator должен отвечать только за координацию,
        а не за обработку ошибок или слияние файлов.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        categories = self._count_method_categories(coordinator_file, "ParallelCoordinator")

        # Координация должна быть основной ответственностью
        total_methods = sum(categories.values())
        coordination_ratio = categories["coordination"] / max(total_methods, 1)

        assert coordination_ratio >= 0.25, (
            f"ParallelCoordinator должен иметь >=25% методов координации "
            f"(сейчас: {coordination_ratio:.1%})"
        )

        # Проверка что делегирует обработку ошибок
        content = coordinator_file.read_text(encoding="utf-8")
        assert "error_handler" in content, (
            "ParallelCoordinator должен использовать error_handler для обработки ошибок"
        )
        assert "file_merger" in content, (
            "ParallelCoordinator должен использовать file_merger для слияния файлов"
        )

    def test_parallel_error_handler_has_single_responsibility(self) -> None:
        """Проверка что ParallelErrorHandler имеет одну ответственность.

        ParallelErrorHandler должен отвечать только за обработку ошибок.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        error_handler_file = project_root / "parallel" / "error_handler.py"

        assert error_handler_file.exists(), "parallel/error_handler.py должен существовать"

        categories = self._count_method_categories(error_handler_file, "ParallelErrorHandler")

        # Обработка ошибок должна быть основной ответственностью
        total_methods = sum(categories.values())
        error_handling_ratio = categories["error_handling"] / max(total_methods, 1)

        assert error_handling_ratio >= 0.5, (
            f"ParallelErrorHandler должен иметь >=50% методов обработки ошибок "
            f"(сейчас: {error_handling_ratio:.1%})"
        )

    def test_parallel_file_merger_has_single_responsibility(self) -> None:
        """Проверка что ParallelFileMerger имеет одну ответственность.

        ParallelFileMerger должен отвечать только за слияние файлов.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        merger_file = project_root / "parallel" / "merger.py"

        assert merger_file.exists(), "parallel/merger.py должен существовать"

        categories = self._count_method_categories(merger_file, "ParallelFileMerger")

        # Слияние файлов должно быть основной ответственностью
        total_methods = sum(categories.values())
        file_ops_ratio = categories["file_operations"] / max(total_methods, 1)

        assert file_ops_ratio >= 0.4, (
            f"ParallelFileMerger должен иметь >=40% методов слияния файлов "
            f"(сейчас: {file_ops_ratio:.1%})"
        )


# =============================================================================
# ТЕСТ 2: Dependency Inversion Principle
# =============================================================================


class TestDependencyInversionUsage:
    """Тесты на использование DIP."""

    def test_parallel_coordinator_uses_di(self) -> None:
        """Проверка что ParallelCoordinator использует DI.

        ParallelCoordinator должен принимать зависимости через конструктор.
        """
        import inspect

        from parser_2gis.parallel.coordinator import ParallelCoordinator

        sig = inspect.signature(ParallelCoordinator.__init__)
        params = sig.parameters

        # Проверяем наличие параметров DI
        assert "error_handler" in params, (
            "ParallelCoordinator должен принимать error_handler через конструктор"
        )
        assert "file_merger" in params, (
            "ParallelCoordinator должен принимать file_merger через конструктор"
        )

        # Проверяем что параметры опциональны
        assert params["error_handler"].default is None, "error_handler должен быть опциональным"
        assert params["file_merger"].default is None, "file_merger должен быть опциональным"

    def test_parser_uses_browser_protocol(self) -> None:
        """Проверка что парсеры используют BrowserService Protocol.

        Парсеры должны зависеть от абстракции BrowserService, а не от реализации.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parser_dir = project_root / "parser" / "parsers"

        # Парсеры которые должны использовать BrowserService напрямую
        parser_files_requiring_browser = ["main_parser.py", "main.py", "base.py"]

        for parser_file_name in parser_files_requiring_browser:
            parser_file = parser_dir / parser_file_name
            if not parser_file.exists():
                continue

            content = parser_file.read_text(encoding="utf-8")

            # Проверяем что используется BrowserService
            if "class" in content and "Parser" in content:
                assert "BrowserService" in content, (
                    f"{parser_file_name} должен использовать BrowserService Protocol"
                )

        # Файлы которые могут не использовать BrowserService напрямую
        # (они используют другие парсеры которые уже используют BrowserService)
        indirect_browser_files = {
            "main_extractor.py": "MainPageParser",  # Использует MainPageParser
            "main_processor.py": "MainPageParser",  # Использует MainPageParser
            "firm.py": "MainParser",  # Наследуется от MainParser
        }

        for parser_file_name, parent_class in indirect_browser_files.items():
            parser_file = parser_dir / parser_file_name
            if not parser_file.exists():
                continue

            content = parser_file.read_text(encoding="utf-8")

            # Проверяем что файл либо использует BrowserService, либо наследуется/использует правильный класс
            has_browser_service = "BrowserService" in content
            has_parent_usage = parent_class in content

            assert has_browser_service or has_parent_usage, (
                f"{parser_file_name} должен использовать BrowserService или {parent_class}"
            )

    def test_protocols_are_used_for_abstractions(self) -> None:
        """Проверка что Protocol используются для абстракций.

        Protocol должны использоваться для определения интерфейсов.
        """
        from parser_2gis import protocols

        # Проверяем что основные Protocol существуют
        expected_protocols = [
            "BrowserService",
            "Writer",
            "Parser",
            "CacheBackend",
            "ExecutionBackend",
        ]

        for protocol_name in expected_protocols:
            assert hasattr(protocols, protocol_name), (
                f"protocols.py должен экспортировать {protocol_name}"
            )


# =============================================================================
# ТЕСТ 3: Interface Segregation Principle
# =============================================================================


class TestInterfaceSegregation:
    """Тесты на соблюдение ISP."""

    def test_browser_protocol_is_segregated(self) -> None:
        """Проверка что BrowserService разделён на мелкие интерфейсы.

        BrowserService должен состоять из отдельных Protocol для навигации,
        контента, JS и скриншотов.
        """
        from parser_2gis.protocols import (
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
            BrowserService,
        )

        # Проверяем что отдельные Protocol существуют
        assert BrowserNavigation is not None, "BrowserNavigation должен существовать"
        assert BrowserContentAccess is not None, "BrowserContentAccess должен существовать"
        assert BrowserJSExecution is not None, "BrowserJSExecution должен существовать"
        assert BrowserScreenshot is not None, "BrowserScreenshot должен существовать"
        assert BrowserService is not None, "BrowserService должен существовать"

    def test_callback_protocols_are_segregated(self) -> None:
        """Проверка что callback Protocol разделены.

        Каждый callback должен быть отдельным Protocol.
        """
        from parser_2gis.protocols import (
            CancelCallback,
            CleanupCallback,
            LogCallback,
            ProgressCallback,
        )

        assert CancelCallback is not None, "CancelCallback должен существовать"
        assert CleanupCallback is not None, "CleanupCallback должен существовать"
        assert LogCallback is not None, "LogCallback должен существовать"
        assert ProgressCallback is not None, "ProgressCallback должен существовать"

    def test_protocols_are_not_fat(self) -> None:
        """Проверка что Protocol не избыточны.

        Каждый Protocol должен иметь ограниченное количество методов.
        """

        def count_protocol_methods(protocol_type: type) -> int:
            """Подсчитывает количество методов в Protocol."""
            count = 0
            for name, member in protocol_type.__dict__.items():
                if not name.startswith("_") and callable(member):
                    count += 1
            return count

        from parser_2gis.protocols import (
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
        )

        # Проверяем что отдельные Protocol имеют мало методов
        nav_methods = count_protocol_methods(BrowserNavigation)
        content_methods = count_protocol_methods(BrowserContentAccess)
        js_methods = count_protocol_methods(BrowserJSExecution)
        screenshot_methods = count_protocol_methods(BrowserScreenshot)

        assert nav_methods <= 3, (
            f"BrowserNavigation должен иметь <=3 методов (сейчас: {nav_methods})"
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


# =============================================================================
# ТЕСТ 4: Интеграция SOLID
# =============================================================================


class TestSOLIDIntegration:
    """Тесты на интеграцию SOLID принципов."""

    def test_all_solid_principles_are_applied(self) -> None:
        """Проверка что все SOLID принципы применяются.

        S - Single Responsibility
        O - Open/Closed
        L - Liskov Substitution
        I - Interface Segregation
        D - Dependency Inversion
        """
        from parser_2gis import protocols
        from parser_2gis.application.layer import BrowserFacade, CacheFacade, ParserFacade

        # S: Фасады имеют одну ответственность
        assert ParserFacade is not None
        assert CacheFacade is not None
        assert BrowserFacade is not None

        # O: Protocol позволяют расширение без модификации
        assert protocols.BrowserService is not None
        assert protocols.Writer is not None

        # L: Mock объекты могут заменить реальные реализации
        mock_browser = MagicMock(spec=protocols.BrowserService)
        mock_writer = MagicMock(spec=protocols.Writer)
        assert mock_browser is not None
        assert mock_writer is not None

        # I: Protocol разделены
        assert protocols.BrowserNavigation is not None
        assert protocols.BrowserContentAccess is not None

        # D: DI используется
        import inspect

        from parser_2gis.parallel.coordinator import ParallelCoordinator

        sig = inspect.signature(ParallelCoordinator.__init__)
        assert "error_handler" in sig.parameters
        assert "file_merger" in sig.parameters

    def test_infrastructure_layer_is_isolated(self) -> None:
        """Проверка что infrastructure слой изолирован.

        Infrastructure должен инкапсулировать внешние зависимости.
        """
        from parser_2gis.infrastructure import MemoryMonitor, ResourceMonitor

        # Проверяем что мониторы работают
        monitor = MemoryMonitor()
        available = monitor.get_available_memory()
        assert isinstance(available, int)
        assert available > 0

        resource_monitor = ResourceMonitor()
        memory_monitor = resource_monitor.get_memory_monitor()
        assert isinstance(memory_monitor, MemoryMonitor)

    def test_application_layer_provides_facades(self) -> None:
        """Проверка что application слой предоставляет фасады.

        Application должен предоставлять фасады для бизнес-логики.
        """
        from parser_2gis.application import BrowserFacade, CacheFacade, ParserFacade

        # Проверяем что фасады доступны из application
        assert ParserFacade is not None
        assert CacheFacade is not None
        assert BrowserFacade is not None

        # Проверяем что фасады имеют ожидаемые методы
        assert hasattr(ParserFacade, "create_parser")
        assert hasattr(CacheFacade, "get")
        assert hasattr(CacheFacade, "set")
        assert hasattr(BrowserFacade, "create_browser")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
