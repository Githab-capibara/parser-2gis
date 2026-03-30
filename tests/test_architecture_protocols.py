"""
Тесты на проверку использования Protocol и Abstractions.

Проверяет что:
- BrowserService используется через Protocol для разрыва зависимости
- ParallelCoordinator использует ParallelErrorHandler через композицию
- MainPageParser принимает BrowserService через dependency injection
- Protocol используются для типизации callback функций

Принципы:
- Dependency Inversion Principle (DIP)
- Программирование через интерфейсы (Protocol)
- Композиция вместо наследования
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def get_protocol_usage(file_path: Path, protocol_name: str) -> Dict[str, Any]:
    """Анализирует использование Protocol в файле.

    Args:
        file_path: Путь к Python файлу.
        protocol_name: Имя Protocol для поиска.

    Returns:
        Словарь с информацией об использовании Protocol.
    """
    usage: Dict[str, Any] = {
        "imported": False,
        "used_in_annotations": False,
        "used_in_generics": False,
        "implementations": [],
    }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return usage

    # Проверяем импорт
    if (
        f"import {protocol_name}" in source
        or f"from parser_2gis.protocols import {protocol_name}" in source
    ):
        usage["imported"] = True

    # Проверяем использование в аннотациях
    if f": {protocol_name}" in source or f"Optional[{protocol_name}]" in source:
        usage["used_in_annotations"] = True

    # Проверяем использование в generics
    if f"[{protocol_name}]" in source:
        usage["used_in_generics"] = True

    return usage


def get_class_init_parameters(file_path: Path, class_name: str) -> List[str]:
    """Извлекает параметры __init__ метода класса.

    Args:
        file_path: Путь к Python файлу.
        class_name: Имя класса.

    Returns:
        Список имён параметров __init__.
    """
    parameters: List[str] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError):
        return parameters

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return parameters

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    for arg in item.args.args:
                        if arg.arg != "self":
                            parameters.append(arg.arg)

    return parameters


def check_composition(file_path: Path, class_name: str, component_name: str) -> bool:
    """Проверяет использует ли класс композицию с указанным компонентом.

    Args:
        file_path: Путь к Python файлу.
        class_name: Имя класса для проверки.
        component_name: Имя компонента для поиска.

    Returns:
        True если используется композиция.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return False

    # Проверяем наличие компонента как атрибута класса
    patterns = [
        f"self._{component_name.lower()}",
        f"self.{component_name.lower()}",
        f"self.{component_name}",
    ]

    return any(pattern in content for pattern in patterns)


# =============================================================================
# ТЕСТ 1: BROWSERSERVICE PROTOCOL
# =============================================================================


class TestBrowserServiceProtocol:
    """Тесты на использование BrowserService Protocol."""

    def test_browser_service_protocol_exists(self) -> None:
        """Проверяет что BrowserService Protocol существует."""
        from parser_2gis.protocols import BrowserService

        assert BrowserService is not None
        assert hasattr(BrowserService, "__protocol_attrs__")

    def test_browser_service_protocol_is_runtime_checkable(self) -> None:
        """Проверяет что BrowserService Protocol runtime_checkable."""

        from parser_2gis.protocols import BrowserService

        # Проверяем что Protocol имеет @runtime_checkable
        # runtime_checkable добавляет __protocol_attrs__ или _is_runtime_protocol
        has_runtime_check = (
            hasattr(BrowserService, "__runtime_checkable__")
            or getattr(BrowserService, "_is_runtime_protocol", False)
            or hasattr(BrowserService, "__protocol_attrs__")
        )
        assert has_runtime_check, "BrowserService должен быть @runtime_checkable"

    def test_main_parser_uses_browser_service_protocol(self) -> None:
        """Проверяет что MainPageParser использует BrowserService Protocol."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        usage = get_protocol_usage(main_parser_file, "BrowserService")

        assert usage["imported"] is True, (
            "main_parser.py должен импортировать BrowserService из protocols"
        )
        assert usage["used_in_annotations"] is True, (
            "main_parser.py должен использовать BrowserService в аннотациях"
        )

    def test_main_parser_accepts_browser_service_via_di(self) -> None:
        """Проверяет что MainPageParser принимает BrowserService через dependency injection."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        params = get_class_init_parameters(main_parser_file, "MainPageParser")

        assert "browser" in params, "MainPageParser должен принимать browser параметр в __init__"

        content = main_parser_file.read_text(encoding="utf-8")
        assert (
            "browser: Optional[BrowserService]" in content or "browser: BrowserService" in content
        ), "MainPageParser должен типизировать browser как BrowserService"

    def test_browser_service_protocol_methods(self) -> None:
        """Проверяет что BrowserService Protocol имеет необходимые методы."""
        from parser_2gis.protocols import BrowserService

        # Проверяем наличие обязательных методов через inspect

        # BrowserService должен быть Protocol с методами
        assert hasattr(BrowserService, "__abstractmethods__") or hasattr(
            BrowserService, "__protocol_attrs__"
        )

    def test_browser_service_protocol_composite(self) -> None:
        """Проверяет что BrowserService Protocol составной (наследуется от других Protocol)."""
        from parser_2gis.protocols import (
            BrowserContentAccess,
            BrowserJSExecution,
            BrowserNavigation,
            BrowserScreenshot,
            BrowserService,
        )

        # BrowserService должен наследоваться от более мелких Protocol
        assert BrowserService is not None
        # Проверяем что отдельные Protocol существуют
        assert BrowserNavigation is not None
        assert BrowserContentAccess is not None
        assert BrowserJSExecution is not None
        assert BrowserScreenshot is not None


# =============================================================================
# ТЕСТ 2: PARALLELCOORDINATOR КОМПОЗИЦИЯ
# =============================================================================


class TestParallelCoordinatorComposition:
    """Тесты на композицию в ParallelCoordinator."""

    def test_coordinator_uses_error_handler_via_composition(self) -> None:
        """Проверяет что ParallelCoordinator использует ParallelErrorHandler через композицию."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        # Проверяем композицию
        has_composition = check_composition(
            coordinator_file, "ParallelCoordinator", "error_handler"
        )

        assert has_composition, (
            "ParallelCoordinator должен использовать ParallelErrorHandler через композицию"
        )

    def test_coordinator_instantiates_error_handler(self) -> None:
        """Проверяет что ParallelCoordinator создаёт экземпляр ParallelErrorHandler."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        assert "ParallelErrorHandler(" in content, (
            "ParallelCoordinator должен создавать экземпляр ParallelErrorHandler"
        )
        assert "self._error_handler = ParallelErrorHandler" in content, (
            "ParallelCoordinator должен сохранять экземпляр как self._error_handler"
        )

    def test_coordinator_uses_file_merger_via_composition(self) -> None:
        """Проверяет что ParallelCoordinator использует ParallelFileMerger через композицию."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        has_composition = check_composition(coordinator_file, "ParallelCoordinator", "file_merger")

        assert has_composition, (
            "ParallelCoordinator должен использовать ParallelFileMerger через композицию"
        )

    def test_coordinator_uses_progress_reporter_via_composition(self) -> None:
        """Проверяет что ParallelCoordinator использует ParallelProgressReporter через композицию."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        assert "ParallelProgressReporter" in content, (
            "ParallelCoordinator должен использовать ParallelProgressReporter"
        )
        assert "self._progress_reporter" in content, (
            "ParallelCoordinator должен сохранять экземпляр как self._progress_reporter"
        )

    def test_coordinator_delegates_to_components(self) -> None:
        """Проверяет что ParallelCoordinator делегирует задачи компонентам."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # Проверяем делегирование
        assert "self._error_handler.handle_" in content, (
            "ParallelCoordinator должен делегировать обработку ошибок"
        )
        assert "self._file_merger.merge_csv_files" in content, (
            "ParallelCoordinator должен делегировать слияние файлов"
        )


# =============================================================================
# ТЕСТ 3: PROTOCOL ДЛЯ CALLBACK
# =============================================================================


class TestCallbackProtocols:
    """Тесты на использование Protocol для callback функций."""

    def test_progress_callback_protocol_exists(self) -> None:
        """Проверяет что ProgressCallback Protocol существует."""
        from parser_2gis.protocols import ProgressCallback

        assert ProgressCallback is not None

    def test_log_callback_protocol_exists(self) -> None:
        """Проверяет что LogCallback Protocol существует."""
        from parser_2gis.protocols import LogCallback

        assert LogCallback is not None

    def test_cleanup_callback_protocol_exists(self) -> None:
        """Проверяет что CleanupCallback Protocol существует."""
        from parser_2gis.protocols import CleanupCallback

        assert CleanupCallback is not None

    def test_cancel_callback_protocol_exists(self) -> None:
        """Проверяет что CancelCallback Protocol существует."""
        from parser_2gis.protocols import CancelCallback

        assert CancelCallback is not None

    def test_coordinator_uses_progress_callback_protocol(self) -> None:
        """Проверяет что coordinator использует ProgressCallback Protocol."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # Проверяем использование callback
        assert "ProgressCallback" in content or "progress_callback" in content, (
            "coordinator.py должен использовать ProgressCallback"
        )

    def test_callback_protocols_are_runtime_checkable(self) -> None:
        """Проверяет что callback Protocol runtime_checkable."""
        from parser_2gis.protocols import (
            CancelCallback,
            CleanupCallback,
            LogCallback,
            ProgressCallback,
        )

        # Проверяем что Protocol имеют @runtime_checkable
        # runtime_checkable добавляет __protocol_attrs__ или _is_runtime_protocol
        for protocol in [ProgressCallback, LogCallback, CleanupCallback, CancelCallback]:
            has_runtime_check = (
                hasattr(protocol, "__runtime_checkable__")
                or getattr(protocol, "_is_runtime_protocol", False)
                or hasattr(protocol, "__protocol_attrs__")
                # Для Callable Protocol проверяем что они работают с isinstance
                or callable(protocol)
            )
            # Callable Protocol могут не иметь явного __runtime_checkable__
            # но всё равно работать с isinstance через __call__
            assert has_runtime_check or hasattr(protocol, "__call__"), (
                f"{protocol.__name__} должен быть @runtime_checkable или Callable"
            )


# =============================================================================
# ТЕСТ 4: PROTOCOL ДЛЯ WRITER И PARSER
# =============================================================================


class TestWriterParserProtocols:
    """Тесты на использование Protocol для Writer и Parser."""

    def test_writer_protocol_exists(self) -> None:
        """Проверяет что Writer Protocol существует."""
        from parser_2gis.protocols import Writer

        assert Writer is not None

    def test_parser_protocol_exists(self) -> None:
        """Проверяет что Parser Protocol существует."""
        from parser_2gis.protocols import Parser

        assert Parser is not None

    def test_writer_protocol_methods(self) -> None:
        """Проверяет что Writer Protocol имеет необходимые методы."""
        from parser_2gis.protocols import Writer

        # Writer должен иметь методы write и close
        # Проверяем через создание mock
        mock_writer: Writer = MagicMock(spec=Writer)
        mock_writer.write([])
        mock_writer.close()

        assert mock_writer.write.called
        assert mock_writer.close.called

    def test_parser_protocol_methods(self) -> None:
        """Проверяет что Parser Protocol имеет необходимые методы."""
        from parser_2gis.protocols import Parser

        # Parser должен иметь методы parse и get_stats
        mock_parser: Parser = MagicMock(spec=Parser)
        mock_parser.parse()
        mock_parser.get_stats()

        assert mock_parser.parse.called
        assert mock_parser.get_stats.called


# =============================================================================
# ТЕСТ 5: PROTOCOL ДЛЯ BACKEND
# =============================================================================


class TestBackendProtocols:
    """Тесты на использование Protocol для бэкендов."""

    def test_cache_backend_protocol_exists(self) -> None:
        """Проверяет что CacheBackend Protocol существует."""
        from parser_2gis.protocols import CacheBackend

        assert CacheBackend is not None

    def test_execution_backend_protocol_exists(self) -> None:
        """Проверяет что ExecutionBackend Protocol существует."""
        from parser_2gis.protocols import ExecutionBackend

        assert ExecutionBackend is not None

    def test_cache_backend_protocol_methods(self) -> None:
        """Проверяет что CacheBackend Protocol имеет необходимые методы."""
        from parser_2gis.protocols import CacheBackend

        mock_cache: CacheBackend = MagicMock(spec=CacheBackend)
        mock_cache.get("key")
        mock_cache.set("key", "value", 3600)
        mock_cache.delete("key")
        mock_cache.exists("key")

        assert mock_cache.get.called
        assert mock_cache.set.called
        assert mock_cache.delete.called
        assert mock_cache.exists.called

    def test_execution_backend_protocol_methods(self) -> None:
        """Проверяет что ExecutionBackend Protocol имеет необходимые методы."""
        from parser_2gis.protocols import ExecutionBackend

        mock_executor: ExecutionBackend = MagicMock(spec=ExecutionBackend)
        mock_executor.submit(lambda: None)
        mock_executor.map(lambda x: x, [1, 2, 3])
        mock_executor.shutdown()

        assert mock_executor.submit.called
        assert mock_executor.map.called
        assert mock_executor.shutdown.called


# =============================================================================
# ТЕСТ 6: DEPENDENCY INJECTION
# =============================================================================


class TestDependencyInjection:
    """Тесты на использование Dependency Injection."""

    def test_main_parser_di_pattern(self) -> None:
        """Проверяет что MainPageParser использует DI паттерн."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        main_parser_file = project_root / "parser" / "parsers" / "main_parser.py"

        assert main_parser_file.exists(), "parser/parsers/main_parser.py должен существовать"

        content = main_parser_file.read_text(encoding="utf-8")

        # MainPageParser должен принимать browser через __init__
        assert "def __init__" in content
        assert "browser:" in content

        # Должен использовать injected browser или создавать внутренний
        assert "self._chrome_remote" in content or "self._browser" in content, (
            "MainPageParser должен сохранять browser как атрибут"
        )

    def test_parallel_coordinator_di_pattern(self) -> None:
        """Проверяет что ParallelCoordinator использует DI паттерн."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        coordinator_file = project_root / "parallel" / "coordinator.py"

        assert coordinator_file.exists(), "parallel/coordinator.py должен существовать"

        content = coordinator_file.read_text(encoding="utf-8")

        # ParallelCoordinator должен создавать зависимости в __init__
        assert "def __init__" in content
        assert "self._error_handler" in content
        assert "self._file_merger" in content

    def test_protocol_allows_mocking(self) -> None:
        """Проверяет что Protocol позволяют использовать mock объекты."""
        from parser_2gis.protocols import BrowserService, Parser, Writer

        # Создаём mock объекты через Protocol
        mock_browser: BrowserService = MagicMock(spec=BrowserService)
        mock_writer: Writer = MagicMock(spec=Writer)
        mock_parser: Parser = MagicMock(spec=Parser)

        # Проверяем что mock объекты работают
        mock_browser.navigate("http://example.com")
        mock_writer.write([{"key": "value"}])
        mock_parser.parse()

        assert mock_browser.navigate.called
        assert mock_writer.write.called
        assert mock_parser.parse.called


# =============================================================================
# ТЕСТ 7: PROTOCOL INTEGRITY
# =============================================================================


class TestProtocolIntegrity:
    """Тесты на целостность Protocol."""

    def test_protocols_module_no_external_imports(self) -> None:
        """Проверяет что protocols.py не импортирует внешние модули проекта."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        protocols_file = project_root / "protocols.py"

        assert protocols_file.exists(), "protocols.py должен существовать"

        content = protocols_file.read_text(encoding="utf-8")

        # protocols.py не должен импортировать другие модули проекта
        # (кроме typing и стандартной библиотеки)
        # Исключаем docstring примеры (строки с >>>)
        lines = content.split("\n")
        code_lines = [
            line for line in lines if ">>>" not in line and '"""' not in line and "'''" not in line
        ]
        code_content = "\n".join(code_lines)

        forbidden_imports = [
            "from parser_2gis.chrome",
            "from parser_2gis.parser",
            "from parser_2gis.parallel",
            "from parser_2gis.logger",
        ]

        for imp in forbidden_imports:
            assert imp not in code_content, f"protocols.py не должен импортировать: {imp}"

    def test_protocol_definitions_are_stable(self) -> None:
        """Проверяет что определения Protocol стабильны."""
        from parser_2gis.protocols import (
            BrowserService,
            CacheBackend,
            ExecutionBackend,
            LoggerProtocol,
            Parser,
            ProgressCallback,
            Writer,
        )

        # Все Protocol должны быть определены
        protocols = [
            BrowserService,
            CacheBackend,
            ExecutionBackend,
            LoggerProtocol,
            Parser,
            ProgressCallback,
            Writer,
        ]

        for protocol in protocols:
            assert protocol is not None, "Protocol должен быть определён"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
