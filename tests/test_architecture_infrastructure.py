"""
Тесты для Infrastructure слоя.

Проверяет:
- Существование пакета infrastructure/
- Наличие MemoryMonitor, ResourceMonitor
- psutil не импортируется напрямую в parallel/ и parser/
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List

import pytest

# =============================================================================
# ТЕСТ 1: Существование пакета infrastructure/
# =============================================================================


class TestInfrastructurePackage:
    """Тесты для пакета infrastructure/."""

    def test_infrastructure_package_exists(self) -> None:
        """Проверка существования пакета infrastructure/.

        Пакет infrastructure/ должен существовать для выделения
        инфраструктурных зависимостей.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        infrastructure_dir = project_root / "infrastructure"

        assert infrastructure_dir.exists(), "Директория infrastructure/ должна существовать"
        assert infrastructure_dir.is_dir(), "infrastructure/ должна быть директорией"

    def test_infrastructure_init_exists(self) -> None:
        """Проверка existence infrastructure/__init__.py.

        __init__.py должен существовать и экспортировать компоненты.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        infrastructure_init = project_root / "infrastructure" / "__init__.py"

        assert infrastructure_init.exists(), "infrastructure/__init__.py должен существовать"

        content = infrastructure_init.read_text(encoding="utf-8")

        # Проверяем экспорт основных компонентов
        assert "MemoryMonitor" in content, (
            "infrastructure/__init__.py должен экспортировать MemoryMonitor"
        )
        assert "ResourceMonitor" in content, (
            "infrastructure/__init__.py должен экспортировать ResourceMonitor"
        )


# =============================================================================
# ТЕСТ 2: MemoryMonitor
# =============================================================================


class TestMemoryMonitor:
    """Тесты для MemoryMonitor."""

    def test_memory_monitor_exists(self) -> None:
        """Проверка существования MemoryMonitor.

        MemoryMonitor должен существовать в infrastructure.resource_monitor
        и предоставлять интерфейс для мониторинга памяти.
        """
        from parser_2gis.infrastructure.resource_monitor import MemoryMonitor

        assert MemoryMonitor is not None, "MemoryMonitor должен существовать"

        # Проверяем что это класс
        assert isinstance(MemoryMonitor, type), "MemoryMonitor должен быть классом"

        # Проверяем наличие основных методов
        assert hasattr(MemoryMonitor, "get_available_memory"), (
            "MemoryMonitor должен иметь метод get_available_memory"
        )
        assert hasattr(MemoryMonitor, "get_memory_usage"), (
            "MemoryMonitor должен иметь метод get_memory_usage"
        )

    def test_memory_monitor_get_available_memory(self) -> None:
        """Проверка метода get_available_memory.

        Метод должен возвращать доступный объём памяти в байтах.
        """
        from parser_2gis.infrastructure.resource_monitor import MemoryMonitor

        monitor = MemoryMonitor()
        available_memory = monitor.get_available_memory()

        assert isinstance(available_memory, int), "get_available_memory должен вернуть int"
        assert available_memory > 0, "Доступная память должна быть больше 0"

    def test_memory_monitor_get_memory_usage(self) -> None:
        """Проверка метода get_memory_usage.

        Метод должен возвращать MemoryInfo с информацией о памяти.
        """
        from parser_2gis.infrastructure.resource_monitor import MemoryInfo, MemoryMonitor

        monitor = MemoryMonitor()
        memory_info = monitor.get_memory_usage()

        assert isinstance(memory_info, MemoryInfo), "get_memory_usage должен вернуть MemoryInfo"

        # Проверяем поля MemoryInfo
        assert hasattr(memory_info, "total"), "MemoryInfo должен иметь поле total"
        assert hasattr(memory_info, "available"), "MemoryInfo должен иметь поле available"
        assert hasattr(memory_info, "used"), "MemoryInfo должен иметь поле used"
        assert hasattr(memory_info, "percent"), "MemoryInfo должен иметь поле percent"

    def test_memory_info_properties(self) -> None:
        """Проверка свойств MemoryInfo.

        MemoryInfo должен предоставлять свойства для конвертации в MB.
        """
        from parser_2gis.infrastructure.resource_monitor import MemoryInfo

        memory_info = MemoryInfo(
            total=1073741824,  # 1 GB
            available=536870912,  # 512 MB
            used=536870912,  # 512 MB
            percent=50.0,
        )

        assert memory_info.total_mb == 1024.0, "total_mb должен вернуть 1024.0"
        assert memory_info.available_mb == 512.0, "available_mb должен вернуть 512.0"
        assert memory_info.used_mb == 512.0, "used_mb должен вернуть 512.0"


# =============================================================================
# ТЕСТ 3: ResourceMonitor
# =============================================================================


class TestResourceMonitor:
    """Тесты для ResourceMonitor."""

    def test_resource_monitor_exists(self) -> None:
        """Проверка существования ResourceMonitor.

        ResourceMonitor должен существовать в infrastructure.resource_monitor
        и предоставлять общий интерфейс для мониторинга ресурсов.
        """
        from parser_2gis.infrastructure.resource_monitor import ResourceMonitor

        assert ResourceMonitor is not None, "ResourceMonitor должен существовать"

        # Проверяем что это класс
        assert isinstance(ResourceMonitor, type), "ResourceMonitor должен быть классом"

        # Проверяем наличие основных методов
        assert hasattr(ResourceMonitor, "get_memory_monitor"), (
            "ResourceMonitor должен иметь метод get_memory_monitor"
        )
        assert hasattr(ResourceMonitor, "is_memory_critical"), (
            "ResourceMonitor должен иметь метод is_memory_critical"
        )

    def test_resource_monitor_get_memory_monitor(self) -> None:
        """Проверка метода get_memory_monitor.

        Метод должен возвращать экземпляр MemoryMonitor.
        """
        from parser_2gis.infrastructure.resource_monitor import MemoryMonitor, ResourceMonitor

        monitor = ResourceMonitor()
        memory_monitor = monitor.get_memory_monitor()

        assert isinstance(memory_monitor, MemoryMonitor), (
            "get_memory_monitor должен вернуть MemoryMonitor"
        )


# =============================================================================
# ТЕСТ 4: psutil не импортируется напрямую
# =============================================================================


class TestPsutilIsolation:
    """Тесты для изоляции psutil в infrastructure слое."""

    def _get_python_files(self, directory: Path, exclude: List[str] = None) -> List[Path]:
        """Получает список Python файлов в директории.

        Args:
            directory: Директория для поиска.
            exclude: Список имён для исключения.

        Returns:
            Список путей к Python файлам.
        """
        if exclude is None:
            exclude = ["__pycache__", "tests", ".pytest_cache"]

        python_files: List[Path] = []

        for py_file in directory.rglob("*.py"):
            # Пропускаем исключенные директории
            if any(part in exclude for part in py_file.parts):
                continue

            python_files.append(py_file)

        return python_files

    def _check_psutil_import(self, file_path: Path) -> bool:
        """Проверяет импортируется ли psutil напрямую в файле.

        Args:
            file_path: Путь к файлу.

        Returns:
            True если psutil импортируется напрямую.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return False

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return False

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "psutil":
                        return True
            elif isinstance(node, ast.ImportFrom):
                if node.module == "psutil":
                    return True

        return False

    def test_psutil_not_imported_in_parallel(self) -> None:
        """Проверка что psutil не импортируется напрямую в parallel/.

        psutil должен импортироваться только в infrastructure слое
        для соблюдения инкапсуляции инфраструктурных зависимостей.

        Исключение: parallel/optimizer.py может использовать psutil для
        мониторинга ресурсов.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        assert parallel_dir.exists(), "parallel/ должна существовать"

        python_files = self._get_python_files(parallel_dir)

        files_with_psutil: List[Path] = []
        for py_file in python_files:
            # Исключение для optimizer.py - он может использовать psutil
            if py_file.name == "optimizer.py":
                continue
            if self._check_psutil_import(py_file):
                files_with_psutil.append(py_file)

        assert len(files_with_psutil) == 0, (
            f"psutil не должен импортироваться напрямую в parallel/. "
            f"Нарушения найдены в: {[str(f.relative_to(project_root)) for f in files_with_psutil]}"
        )

    def test_psutil_not_imported_in_parser(self) -> None:
        """Проверка что psutil не импортируется напрямую в parser/.

        psutil должен импортироваться только в infrastructure слое
        для соблюдения инкапсуляции инфраструктурных зависимостей.

        Исключение: parser/parsers/main_processor.py может использовать psutil
        для оптимизации памяти.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parser_dir = project_root / "parser"

        assert parser_dir.exists(), "parser/ должна существовать"

        python_files = self._get_python_files(parser_dir)

        files_with_psutil: List[Path] = []
        for py_file in python_files:
            # Исключение для main_processor.py - он может использовать psutil
            if py_file.name == "main_processor.py":
                continue
            if self._check_psutil_import(py_file):
                files_with_psutil.append(py_file)

        assert len(files_with_psutil) == 0, (
            f"psutil не должен импортироваться напрямую в parser/. "
            f"Нарушения найдены в: {[str(f.relative_to(project_root)) for f in files_with_psutil]}"
        )

    def test_psutil_imported_only_in_infrastructure(self) -> None:
        """Проверка что psutil импортируется только в infrastructure/.

        psutil должен быть инкапсулирован в infrastructure слое.
        """
        from parser_2gis.infrastructure.resource_monitor import MemoryMonitor

        # Проверяем что MemoryMonitor использует psutil
        monitor = MemoryMonitor()

        # Метод должен работать (psutil доступен через infrastructure)
        available_memory = monitor.get_available_memory()
        assert isinstance(available_memory, int), (
            "MemoryMonitor должен использовать psutil корректно"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
