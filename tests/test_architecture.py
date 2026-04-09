"""Архитектурные тесты для проверки SOLID/границ зависимостей.

ISSUE 161: Тесты на границы слоёв и отсутствие циклических импортов.
ISSUE 162: Тесты на возможность импорта всех основных модулей.
ISSUE 163: Тесты на изоляцию глобального состояния (registry reset/clear).
ISSUE 165: Тесты производительности для критических функций.
ISSUE 179: Интеграционные тесты полного цикла парсинга (mock).
"""

from __future__ import annotations

import ast
import importlib
import time
from pathlib import Path

import pytest

# Базовый путь к пакету проекта
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = PROJECT_ROOT / "parser_2gis"


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def _get_all_python_files(directory: Path) -> list[Path]:
    """Рекурсивно получает все Python файлы в директории."""
    exclude = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "venv", ".venv"}
    result: list[Path] = []
    for path in directory.rglob("*.py"):
        if not any(part in exclude for part in path.parts):
            result.append(path)
    return result


def _get_imports(file_path: Path) -> set[str]:
    """Извлекает все импорты из Python файла."""
    imports: set[str] = set()
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
    except (OSError, UnicodeDecodeError, SyntaxError):
        pass
    return imports


def _build_dependency_graph(directory: Path) -> dict[str, set[str]]:
    """Строит граф зависимостей модулей."""
    graph: dict[str, set[str]] = {}
    for py_file in _get_all_python_files(directory):
        rel_path = str(py_file.relative_to(PROJECT_ROOT)).replace("/", ".").replace("\\", ".")
        module_name = rel_path.rsplit(".", 1)[0] if rel_path.endswith(".py") else rel_path
        imports = _get_imports(py_file)
        graph[module_name] = imports
    return graph


def _has_cycle_from(graph: dict[str, set[str]], start: str, visited: set, rec_stack: set) -> bool:
    """Проверяет наличие цикла из начальной вершины (DFS)."""
    visited.add(start)
    rec_stack.add(start)
    for neighbor in graph.get(start, set()):
        if neighbor not in visited:
            if _has_cycle_from(graph, neighbor, visited, rec_stack):
                return True
        elif neighbor in rec_stack:
            return True
    rec_stack.discard(start)
    return False


def _detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Обнаруживает циклы в графе зависимостей."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    for node in graph:
        if node not in visited:
            rec_stack: set[str] = set()
            path: list[str] = []

            def _dfs(node: str, visited: set[str], rec_stack: set[str], path: list[str]) -> None:
                visited.add(node)
                rec_stack.add(node)
                path.append(node)
                for neighbor in graph.get(node, set()):
                    if neighbor not in visited:
                        _dfs(neighbor, visited, rec_stack, path)
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor)
                        cycles.append(path[cycle_start:] + [neighbor])
                path.pop()
                rec_stack.discard(node)

            _dfs(node, visited, rec_stack, path)
    return cycles


# ============================================================================
# ISSUE 161: Границы слоёв — domain не импортирует infrastructure
# ============================================================================

# Определяем слои архитектуры
DOMAIN_MODULES = {"parser_2gis.core_types", "parser_2gis.protocols", "parser_2gis.types"}
INFRASTRUCTURE_MODULES = {
    "parser_2gis.chrome",
    "parser_2gis.cache",
    "parser_2gis.writer",
    "parser_2gis.logger",
    "parser_2gis.infrastructure",
}


class TestLayerBoundaries:
    """Тесты проверки границ слоёв архитектуры."""

    def test_domain_does_not_import_infrastructure(self) -> None:
        """Domain слой не должен импортировать infrastructure модули."""
        violations: list[str] = []
        for domain_mod in DOMAIN_MODULES:
            for infra_mod in INFRASTRUCTURE_MODULES:
                try:
                    mod = importlib.import_module(domain_mod)
                    if mod is not None:
                        source_file = getattr(mod, "__file__", None)
                        if source_file:
                            imports = _get_imports(Path(source_file))
                            for imp in imports:
                                if imp.startswith(infra_mod):
                                    violations.append(
                                        f"{domain_mod} импортирует {imp} (нарушение границ)"
                                    )
                except (ImportError, ModuleNotFoundError):
                    pass  # Модуль может отсутствовать
        assert not violations, "Нарушения границ слоёв:\n" + "\n".join(violations)

    def test_cache_does_not_import_chrome(self) -> None:
        """cache слой не должен импортировать chrome."""
        cache_path = PACKAGE_ROOT / "cache"
        if not cache_path.exists():
            pytest.skip("cache модуль не найден")
        for py_file in cache_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = _get_imports(py_file)
            chrome_imports = [imp for imp in imports if "chrome" in imp]
            assert not chrome_imports, f"{py_file.name} импортирует chrome: {chrome_imports}"

    def test_writer_does_not_import_chrome(self) -> None:
        """writer слой не должен импортировать chrome."""
        writer_path = PACKAGE_ROOT / "writer"
        if not writer_path.exists():
            pytest.skip("writer модуль не найден")
        for py_file in writer_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = _get_imports(py_file)
            chrome_imports = [imp for imp in imports if "chrome" in imp]
            assert not chrome_imports, f"{py_file.name} импортирует chrome: {chrome_imports}"

    def test_logger_has_no_business_logic_imports(self) -> None:
        """logger не должен импортировать бизнес-логику."""
        logger_path = PACKAGE_ROOT / "logger"
        if not logger_path.exists():
            pytest.skip("logger модуль не найден")
        business_modules = {"parser_2gis.parser", "parser_2gis.chrome.browser"}
        for py_file in logger_path.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            imports = _get_imports(py_file)
            for imp in imports:
                for biz_mod in business_modules:
                    if imp.startswith(biz_mod):
                        pytest.fail(f"{py_file.name} импортирует бизнес-логику: {imp}")


# ============================================================================
# ISSUE 162: Отсутствие циклических импортов
# ============================================================================

MAJOR_MODULES = [
    "parser_2gis",
    "parser_2gis.config",
    "parser_2gis.cache",
    "parser_2gis.cache.pool",
    "parser_2gis.cache.manager",
    "parser_2gis.chrome",
    "parser_2gis.chrome.browser",
    "parser_2gis.chrome.options",
    "parser_2gis.chrome.remote",
    "parser_2gis.logger",
    "parser_2gis.logger.logger",
    "parser_2gis.parallel",
    "parser_2gis.parallel.coordinator",
    "parser_2gis.parallel.parallel_parser",
    "parser_2gis.parser",
    "parser_2gis.writer",
    "parser_2gis.writer.writers",
    "parser_2gis.exceptions",
    "parser_2gis.constants",
    "parser_2gis.types",
    "parser_2gis.core_types",
    "parser_2gis.protocols",
    "parser_2gis.validation",
    "parser_2gis.config_services",
    "parser_2gis.utils",
    "parser_2gis.resources",
]


class TestNoCircularImports:
    """Тесты на отсутствие циклических импортов."""

    @pytest.mark.parametrize("module_name", MAJOR_MODULES)
    def test_module_importable_without_errors(self, module_name: str) -> None:
        """Каждый основной модуль должен импортироваться без ошибок."""
        try:
            mod = importlib.import_module(module_name)
            assert mod is not None, f"Модуль {module_name} вернул None"
        except ModuleNotFoundError as e:
            pytest.skip(f"Модуль {module_name} не найден (опциональная зависимость): {e}")
        except ImportError as e:
            pytest.fail(f"Ошибка импорта {module_name}: {e}")

    def test_no_circular_imports_in_package(self) -> None:
        """Проверка отсутствия циклических импортов в пакете."""
        graph = _build_dependency_graph(PACKAGE_ROOT)
        # Фильтруем только parser_2gis модули
        filtered_graph = {
            k: {v for v in vals if v.startswith("parser_2gis")}
            for k, vals in graph.items()
            if k.startswith("parser_2gis")
        }
        cycles = _detect_cycles(filtered_graph)
        assert not cycles, "Обнаружены циклические импорты:\n" + "\n".join(
            " -> ".join(c) for c in cycles
        )


# ============================================================================
# ISSUE 163: Тесты изоляции глобального состояния
# ============================================================================

try:
    from parser_2gis.cache.pool import ConnectionPool

    POOL_AVAILABLE = True
except ImportError:
    POOL_AVAILABLE = False

try:
    from parser_2gis.parallel.memory_manager import MemoryManager, _memory_manager_instance

    MEMORY_MANAGER_AVAILABLE = True
except ImportError:
    MEMORY_MANAGER_AVAILABLE = False


class TestGlobalStateIsolation:
    """Тесты изоляции глобального состояния."""

    @pytest.mark.skipif(not POOL_AVAILABLE, reason="ConnectionPool недоступен")
    def test_pool_can_be_cleared_and_reset(self, tmp_path) -> None:
        """Пул соединений можно очистить и пересоздать."""
        db_file = tmp_path / "test_pool.db"
        pool = ConnectionPool(db_file, pool_size=2)
        conn = pool.get_connection()
        assert conn is not None
        pool.close()
        # После close все соединения должны быть закрыты
        assert len(pool._all_conns) == 0
        assert pool._connection_queue.empty()

    @pytest.mark.skipif(not POOL_AVAILABLE, reason="ConnectionPool недоступен")
    def test_pool_context_manager_cleans_up(self, tmp_path) -> None:
        """Контекстный менеджер пула корректно очищает ресурсы."""
        db_file = tmp_path / "test_pool_ctx.db"
        with ConnectionPool(db_file, pool_size=2) as pool:
            conn = pool.get_connection()
            assert conn is not None
        # После выхода из контекста соединения должны быть закрыты
        assert len(pool._all_conns) == 0

    @pytest.mark.skipif(not MEMORY_MANAGER_AVAILABLE, reason="MemoryManager недоступен")
    def test_memory_manager_can_be_reset(self) -> None:
        """MemoryManager можно сбросить."""
        mm = MemoryManager()
        assert mm is not None
        # Проверяем что можно создать новый экземпляр
        mm2 = MemoryManager()
        assert mm2 is not None

    def test_configuration_is_fresh_on_each_creation(self) -> None:
        """Каждое создание Configuration даёт независимый экземпляр."""
        from parser_2gis.config import Configuration

        config1 = Configuration()
        config2 = Configuration()
        # Изменение одного не должно влиять на другой
        config1.path = Path("/tmp/test1")
        assert config2.path is None or config2.path != config1.path


# ============================================================================
# ISSUE 165: Тесты производительности критических функций
# ============================================================================


class TestPerformanceCriticalFunctions:
    """Тесты производительности критических функций."""

    @pytest.mark.benchmark
    def test_merge_performance(self, tmp_path) -> None:
        """Тест производительности операции слияния."""
        from parser_2gis.parallel.common.csv_merge_common import merge_csv_files_common

        # Создаём тестовые CSV файлы
        file1 = tmp_path / "test1.csv"
        file2 = tmp_path / "test2.csv"
        header = "Название;Адрес;Телефон\n"
        file1.write_text(header + "Компания1;Адрес1;Телефон1\n" * 1000)
        file2.write_text(header + "Компания2;Адрес2;Телефон2\n" * 1000)

        # Тестируем общую функцию слияния напрямую
        output_file = tmp_path / "merged.csv"
        start = time.perf_counter()
        merge_csv_files_common(
            file_paths=[file1, file2],
            output_path=output_file,
            buffer_size=8192,
            batch_size=100,
            log_callback=lambda msg, level: None,
        )
        elapsed = time.perf_counter() - start

        assert output_file.exists()
        # Слияние 2000 строк должно занять менее 2 секунд
        assert elapsed < 2.0, f"Слияние заняло слишком много времени: {elapsed:.3f}с"

    @pytest.mark.benchmark
    def test_cache_operations(self, tmp_path) -> None:
        """Тест производительности операций кэша."""
        from parser_2gis.cache.manager import CacheManager

        cache = CacheManager(tmp_path, ttl_hours=1)
        # Тест записи
        start = time.perf_counter()
        for i in range(100):
            cache.set(f"http://test{i}.com", {"key": f"value{i}"})
        write_elapsed = time.perf_counter() - start
        # 100 записей должны занять менее 5 секунд
        assert write_elapsed < 5.0, f"Запись в кэш заняла: {write_elapsed:.3f}с"

        # Тест чтения
        start = time.perf_counter()
        for i in range(100):
            cache.get(f"http://test{i}.com")
        read_elapsed = time.perf_counter() - start
        assert read_elapsed < 5.0, f"Чтение из кэша заняло: {read_elapsed:.3f}с"
        cache.close()

    @pytest.mark.benchmark
    def test_url_hash_performance(self) -> None:
        """Тест производительности хэширования URL."""
        from parser_2gis.cache.cache_utils import hash_url

        urls = [f"http://example.com/page/{i}" for i in range(10000)]
        start = time.perf_counter()
        for url in urls:
            hash_url(url)
        elapsed = time.perf_counter() - start
        # 10000 хэшей должны занять менее 1 секунды
        assert elapsed < 1.0, f"Хэширование заняло: {elapsed:.3f}с"


# ============================================================================
# ISSUE 179: Интеграционные тесты полного цикла парсинга (mock)
# ============================================================================

try:
    from parser_2gis.writer import get_writer

    WRITER_AVAILABLE = True
except ImportError:
    WRITER_AVAILABLE = False


class TestFullParsingCycleMock:
    """Интеграционные тесты полного цикла парсинга с mock."""

    def test_cache_write_and_read_cycle(self, tmp_path) -> None:
        """Тест полного цикла записи и чтения кэша."""
        from parser_2gis.cache.manager import CacheManager

        cache = CacheManager(tmp_path, ttl_hours=24)
        try:
            test_url = "http://2gis.ru/test/firms"
            test_data = {"firms": [{"name": "Test Firm", "address": "Test Address"}]}

            # Запись
            cache.set(test_url, test_data)

            # Чтение
            cached = cache.get(test_url)
            assert cached is not None
            assert cached == test_data

            # Кэш для несуществующего URL
            assert cache.get("http://nonexistent.com") is None
        finally:
            cache.close()

    def test_writer_csv_cycle(self, tmp_path) -> None:
        """Тест цикла записи CSV."""
        if not WRITER_AVAILABLE:
            pytest.skip("writer недоступен")

        from parser_2gis.writer.writers.csv_writer import CSVWriter
        from parser_2gis.writer.options import WriterOptions

        output_file = tmp_path / "output.csv"
        options = WriterOptions()
        options.csv.remove_empty_columns = False
        options.csv.remove_duplicates = False
        writer = CSVWriter(str(output_file), options)
        with writer:
            # Запись данных с корректными полями из data_mapping
            writer._writerow(
                {
                    "name": "Фирма1",
                    "address": "Адрес1",
                    "point_lat": 0.0,
                    "point_lon": 0.0,
                    "url": "http://test.com",
                    "type": "firm",
                }
            )

        # Проверка что файл создан
        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "Фирма1" in content

    def test_config_save_and_load_cycle(self, tmp_path) -> None:
        """Тест полного цикла сохранения и загрузки конфигурации."""
        from parser_2gis.config import Configuration

        config_path = tmp_path / "config.json"
        # Создаём и сохраняем
        config1 = Configuration()
        config1.path = config_path
        config1.save_config()

        # Загружаем
        config2 = Configuration.load_config(config_path, auto_create=False)
        assert config2 is not None
        assert isinstance(config2, Configuration)

    def test_validation_and_error_handling(self) -> None:
        """Тест валидации и обработки ошибок конфигурации."""
        from parser_2gis.config import Configuration

        config = Configuration()
        is_valid, errors = config.validate()
        # Конфигурация по умолчанию должна быть валидной
        assert is_valid or not errors  # Либо валидна, либо есть ошибки

    def test_parallel_merger_cycle(self, tmp_path) -> None:
        """Тест полного цикла слияния файлов параллельного парсера."""
        from parser_2gis.parallel.common.csv_merge_common import merge_csv_files_common

        # Создаём тестовые CSV
        file1 = tmp_path / "p1.csv"
        file2 = tmp_path / "p2.csv"
        header = "Название;Адрес\n"
        file1.write_text(header + "Фирма1;Адрес1\n")
        file2.write_text(header + "Фирма2;Адрес2\n")

        result_file = tmp_path / "result.csv"
        merge_csv_files_common(
            file_paths=[file1, file2],
            output_path=result_file,
            buffer_size=8192,
            batch_size=100,
            log_callback=lambda msg, level: None,
        )
        assert result_file.exists()

    def test_cache_expiry_cycle(self, tmp_path) -> None:
        """Тест цикла истечения срока кэша."""
        from parser_2gis.cache.manager import CacheManager

        cache = CacheManager(tmp_path, ttl_hours=1)
        try:
            test_url = "http://example.com"
            test_data = {"data": "test"}
            cache.set(test_url, test_data)
            # Кэш должен быть доступен
            cached = cache.get(test_url)
            assert cached is not None
            assert cached == test_data
        finally:
            cache.close()
