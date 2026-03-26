"""
Тесты на проверку Protocol абстракций (OCP, DIP).

Проверяет:
- Существование Protocol для кэширования, выполнения, фабрик
- Правильность определения методов в Protocol
- Реализацию Protocol в конкретных классах
- Экспорт всех Protocol из protocols.py

OCP (Open-Closed Principle):
Protocol позволяют расширять функциональность без изменения кода.

DIP (Dependency Inversion Principle):
Protocol позволяют зависеть от абстракций, а не от конкретных реализаций.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pytest


class TestCacheBackendProtocol:
    """Тесты на проверку CacheBackend Protocol."""

    def test_cache_backend_protocol_exists(self) -> None:
        """Проверяет что CacheBackend Protocol существует."""
        from parser_2gis.protocols import CacheBackend

        assert CacheBackend is not None, "CacheBackend Protocol должен существовать"

    def test_cache_backend_is_runtime_checkable(self) -> None:
        """Проверяет что CacheBackend декорирован @runtime_checkable."""
        from parser_2gis.protocols import CacheBackend

        assert hasattr(CacheBackend, "_is_runtime_protocol"), (
            "CacheBackend должен быть @runtime_checkable"
        )

    def test_cache_backend_has_required_methods(self) -> None:
        """Проверяет что CacheBackend определяет требуемые методы."""
        from parser_2gis.protocols import CacheBackend

        required_methods = ["get", "set", "delete", "exists"]

        for method_name in required_methods:
            assert hasattr(CacheBackend, method_name), (
                f"CacheBackend должен иметь метод '{method_name}'"
            )

    def test_cache_backend_method_signatures(self) -> None:
        """Проверяет сигнатуры методов CacheBackend."""
        from parser_2gis.protocols import CacheBackend

        # Проверяем что методы существуют и являются вызываемыми
        assert callable(getattr(CacheBackend, "get", None)), "get должен быть вызываемым"
        assert callable(getattr(CacheBackend, "set", None)), "set должен быть вызываемым"
        assert callable(getattr(CacheBackend, "delete", None)), "delete должен быть вызываемым"
        assert callable(getattr(CacheBackend, "exists", None)), "exists должен быть вызываемым"

    def test_cache_manager_implements_cache_backend(self) -> None:
        """Проверяет что CacheManager реализует CacheBackend Protocol."""
        from parser_2gis.cache import CacheManager

        # Проверяем наличие всех методов
        for method_name in ["get", "set", "delete", "exists"]:
            assert hasattr(CacheManager, method_name), (
                f"CacheManager должен иметь метод '{method_name}'"
            )


class TestExecutionBackendProtocol:
    """Тесты на проверку ExecutionBackend Protocol."""

    def test_execution_backend_protocol_exists(self) -> None:
        """Проверяет что ExecutionBackend Protocol существует."""
        from parser_2gis.protocols import ExecutionBackend

        assert ExecutionBackend is not None, "ExecutionBackend Protocol должен существовать"

    def test_execution_backend_is_runtime_checkable(self) -> None:
        """Проверяет что ExecutionBackend декорирован @runtime_checkable."""
        from parser_2gis.protocols import ExecutionBackend

        assert hasattr(ExecutionBackend, "_is_runtime_protocol"), (
            "ExecutionBackend должен быть @runtime_checkable"
        )

    def test_execution_backend_has_required_methods(self) -> None:
        """Проверяет что ExecutionBackend определяет требуемые методы."""
        from parser_2gis.protocols import ExecutionBackend

        required_methods = ["submit", "map", "shutdown"]

        for method_name in required_methods:
            assert hasattr(ExecutionBackend, method_name), (
                f"ExecutionBackend должен иметь метод '{method_name}'"
            )

    def test_thread_pool_executor_implements_execution_backend(self) -> None:
        """Проверяет что ThreadPoolExecutor реализует ExecutionBackend."""
        from concurrent.futures import ThreadPoolExecutor

        # Проверяем наличие всех методов
        for method_name in ["submit", "map", "shutdown"]:
            assert hasattr(ThreadPoolExecutor, method_name), (
                f"ThreadPoolExecutor должен иметь метод '{method_name}'"
            )


class TestParserFactoryProtocol:
    """Тесты на проверку ParserFactory Protocol."""

    def test_parser_factory_protocol_exists(self) -> None:
        """Проверяет что ParserFactory Protocol существует."""
        from parser_2gis.protocols import ParserFactory

        assert ParserFactory is not None, "ParserFactory Protocol должен существовать"

    def test_parser_factory_is_runtime_checkable(self) -> None:
        """Проверяет что ParserFactory декорирован @runtime_checkable."""
        from parser_2gis.protocols import ParserFactory

        assert hasattr(ParserFactory, "_is_runtime_protocol"), (
            "ParserFactory должен быть @runtime_checkable"
        )

    def test_parser_factory_has_get_parser_method(self) -> None:
        """Проверяет что ParserFactory определяет метод get_parser."""
        from parser_2gis.protocols import ParserFactory

        assert hasattr(ParserFactory, "get_parser"), "ParserFactory должен иметь метод 'get_parser'"

    def test_parser_factory_impl_exists(self) -> None:
        """Проверяет что реализация ParserFactory существует."""
        from parser_2gis.parser.factory import ParserFactoryImpl

        assert ParserFactoryImpl is not None, "ParserFactoryImpl должен существовать"

    def test_parser_factory_impl_implements_protocol(self) -> None:
        """Проверяет что ParserFactoryImpl реализует ParserFactory Protocol."""
        from parser_2gis.parser.factory import ParserFactoryImpl

        # Проверяем наличие метода get_parser
        assert hasattr(ParserFactoryImpl, "get_parser"), (
            "ParserFactoryImpl должен иметь метод 'get_parser'"
        )


class TestWriterFactoryProtocol:
    """Тесты на проверку WriterFactory Protocol."""

    def test_writer_factory_protocol_exists(self) -> None:
        """Проверяет что WriterFactory Protocol существует."""
        from parser_2gis.protocols import WriterFactory

        assert WriterFactory is not None, "WriterFactory Protocol должен существовать"

    def test_writer_factory_is_runtime_checkable(self) -> None:
        """Проверяет что WriterFactory декорирован @runtime_checkable."""
        from parser_2gis.protocols import WriterFactory

        assert hasattr(WriterFactory, "_is_runtime_protocol"), (
            "WriterFactory должен быть @runtime_checkable"
        )

    def test_writer_factory_has_get_writer_method(self) -> None:
        """Проверяет что WriterFactory определяет метод get_writer."""
        from parser_2gis.protocols import WriterFactory

        assert hasattr(WriterFactory, "get_writer"), "WriterFactory должен иметь метод 'get_writer'"

    def test_writer_factory_impl_exists(self) -> None:
        """Проверяет что реализация WriterFactory существует."""
        from parser_2gis.writer.factory import WriterFactoryImpl

        assert WriterFactoryImpl is not None, "WriterFactoryImpl должен существовать"

    def test_writer_factory_impl_implements_protocol(self) -> None:
        """Проверяет что WriterFactoryImpl реализует WriterFactory Protocol."""
        from parser_2gis.writer.factory import WriterFactoryImpl

        # Проверяем наличие метода get_writer
        assert hasattr(WriterFactoryImpl, "get_writer"), (
            "WriterFactoryImpl должен иметь метод 'get_writer'"
        )


class TestBrowserServiceProtocol:
    """Тесты на проверку BrowserService Protocol."""

    def test_browser_service_protocol_exists(self) -> None:
        """Проверяет что BrowserService Protocol существует."""
        from parser_2gis.protocols import BrowserService

        assert BrowserService is not None, "BrowserService Protocol должен существовать"

    def test_browser_service_is_runtime_checkable(self) -> None:
        """Проверяет что BrowserService декорирован @runtime_checkable."""
        from parser_2gis.protocols import BrowserService

        assert hasattr(BrowserService, "_is_runtime_protocol"), (
            "BrowserService должен быть @runtime_checkable"
        )

    def test_browser_service_has_required_methods(self) -> None:
        """Проверяет что BrowserService определяет требуемые методы."""
        from parser_2gis.protocols import BrowserService

        required_methods = ["navigate", "get_html", "execute_js", "screenshot", "close"]

        for method_name in required_methods:
            assert hasattr(BrowserService, method_name), (
                f"BrowserService должен иметь метод '{method_name}'"
            )

    def test_chrome_remote_implements_browser_service(self) -> None:
        """Проверяет что ChromeRemote реализует BrowserService Protocol."""
        from parser_2gis.chrome.remote import ChromeRemote

        # Проверяем наличие всех методов
        for method_name in ["navigate", "get_html", "execute_js", "screenshot", "close"]:
            assert hasattr(ChromeRemote, method_name), (
                f"ChromeRemote должен иметь метод '{method_name}'"
            )


class TestOtherProtocols:
    """Тесты на проверку дополнительных Protocol."""

    @pytest.mark.parametrize(
        "protocol_name,required_methods",
        [
            ("LoggerProtocol", ["debug", "info", "warning", "error", "critical"]),
            ("ProgressCallback", ["__call__"]),
            ("LogCallback", ["__call__"]),
            ("CleanupCallback", ["__call__"]),
            ("CancelCallback", ["__call__"]),
            ("Writer", ["write", "close"]),
            ("Parser", ["parse", "get_stats"]),
        ],
        ids=[
            "LoggerProtocol",
            "ProgressCallback",
            "LogCallback",
            "CleanupCallback",
            "CancelCallback",
            "Writer",
            "Parser",
        ],
    )
    def test_protocol_exists_with_methods(
        self, protocol_name: str, required_methods: List[str]
    ) -> None:
        """Проверяет что Protocol существует и имеет требуемые методы.

        Args:
            protocol_name: Имя Protocol для проверки.
            required_methods: Список требуемых методов.

        Raises:
            AssertionError: Если Protocol не существует или не имеет методов.
        """
        from parser_2gis.protocols import (
            CancelCallback,
            CleanupCallback,
            LogCallback,
            LoggerProtocol,
            Parser,
            ProgressCallback,
            Writer,
        )

        protocols_map: Dict[str, type] = {
            "LoggerProtocol": LoggerProtocol,
            "ProgressCallback": ProgressCallback,
            "LogCallback": LogCallback,
            "CleanupCallback": CleanupCallback,
            "CancelCallback": CancelCallback,
            "Writer": Writer,
            "Parser": Parser,
        }

        protocol = protocols_map.get(protocol_name)
        assert protocol is not None, f"Protocol {protocol_name} не найден"

        for method_name in required_methods:
            assert hasattr(protocol, method_name), (
                f"{protocol_name} должен иметь метод '{method_name}'"
            )

    def test_all_protocols_are_runtime_checkable(self) -> None:
        """Проверяет что все Protocol декорированы @runtime_checkable."""
        from parser_2gis.protocols import (
            BrowserService,
            CacheBackend,
            CancelCallback,
            CleanupCallback,
            ExecutionBackend,
            LogCallback,
            LoggerProtocol,
            Parser,
            ParserFactory,
            ProgressCallback,
            Writer,
            WriterFactory,
        )

        all_protocols = [
            BrowserService,
            CacheBackend,
            CancelCallback,
            CleanupCallback,
            ExecutionBackend,
            LogCallback,
            LoggerProtocol,
            Parser,
            ParserFactory,
            ProgressCallback,
            Writer,
            WriterFactory,
        ]

        for protocol in all_protocols:
            assert hasattr(protocol, "_is_runtime_protocol"), (
                f"{protocol.__name__} должен быть @runtime_checkable"
            )


class TestProtocolsModuleExports:
    """Тесты на проверку экспорта из protocols.py."""

    def test_protocols_module_exists(self) -> None:
        """Проверяет что protocols.py существует."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        protocols_py = project_root / "protocols.py"

        assert protocols_py.exists(), "protocols.py должен существовать"

    def test_protocols_module_exports_all(self) -> None:
        """Проверяет что protocols.py экспортирует все Protocol."""
        from parser_2gis import protocols

        expected_exports = [
            "LoggerProtocol",
            "ProgressCallback",
            "LogCallback",
            "CleanupCallback",
            "CancelCallback",
            "Writer",
            "Parser",
            "BrowserService",
            "CacheBackend",
            "ExecutionBackend",
            "ParserFactory",
            "WriterFactory",
        ]

        missing_exports = []
        for export_name in expected_exports:
            if not hasattr(protocols, export_name):
                missing_exports.append(export_name)

        assert len(missing_exports) == 0, f"protocols.py не экспортирует: {missing_exports}"

    def test_all_dunder_all_defined(self) -> None:
        """Проверяет что __all__ определён в protocols.py."""
        from parser_2gis import protocols

        assert hasattr(protocols, "__all__"), "protocols.py должен определять __all__"

        all_exports = protocols.__all__
        assert isinstance(all_exports, list), "__all__ должен быть списком"
        assert len(all_exports) > 0, "__all__ не должен быть пустым"

    def test_all_exports_match_actual_exports(self) -> None:
        """Проверяет что __all__ соответствует реальным экспортам."""
        from parser_2gis import protocols

        all_exports = protocols.__all__

        missing = []
        for export_name in all_exports:
            if not hasattr(protocols, export_name):
                missing.append(export_name)

        assert len(missing) == 0, f"__all__ содержит несуществующие экспорты: {missing}"


class TestProtocolUsageInCodebase:
    """Тесты на использование Protocol в кодовой базе."""

    def test_cache_backend_used_in_type_hints(self) -> None:
        """Проверяет что CacheBackend используется в type hints."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        found_usage = False

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                if "CacheBackend" in content:
                    found_usage = True
                    break

            except (SyntaxError, UnicodeDecodeError):
                continue

        assert found_usage, "CacheBackend должен использоваться в кодовой базе"

    def test_browser_service_used_in_type_hints(self) -> None:
        """Проверяет что BrowserService используется в type hints."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        found_usage = False

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                if "BrowserService" in content:
                    found_usage = True
                    break

            except (SyntaxError, UnicodeDecodeError):
                continue

        assert found_usage, "BrowserService должен использоваться в кодовой базе"

    def test_parser_factory_used_in_type_hints(self) -> None:
        """Проверяет что ParserFactory используется в type hints."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        found_usage = False

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")

                if "ParserFactory" in content:
                    found_usage = True
                    break

            except (SyntaxError, UnicodeDecodeError):
                continue

        assert found_usage, "ParserFactory должен использоваться в кодовой базе"


__all__ = [
    "TestCacheBackendProtocol",
    "TestExecutionBackendProtocol",
    "TestParserFactoryProtocol",
    "TestWriterFactoryProtocol",
    "TestBrowserServiceProtocol",
    "TestOtherProtocols",
    "TestProtocolsModuleExports",
    "TestProtocolUsageInCodebase",
]
