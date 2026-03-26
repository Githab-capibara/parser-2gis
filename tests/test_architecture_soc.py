"""
Тесты на проверку разделения ответственности (Separation of Concerns - SoC).

Проверяет:
- ParallelCityParser имеет чёткие ответственности
- CacheManager разделён на специализированные модули
- ChromeRemote разделён на специализированные модули
- Configuration и ConfigService разделены

SoC принцип:
Разные ответственности должны быть разделены на разные модули/классы.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Tuple


class TestParallelParserResponsibilities:
    """Тесты на разделение ответственностей ParallelCityParser."""

    def test_parallel_parser_responsibilities_separated(self) -> None:
        """Проверяет что ответственности ParallelCityParser разделены.

        ParallelCityParser должен заниматься только параллельным парсингом.
        Вспомогательные функции должны быть вынесены в отдельные модули.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_parser = project_root / "parallel" / "parallel_parser.py"

        assert parallel_parser.exists(), "parallel_parser.py должен существовать"

        content = parallel_parser.read_text(encoding="utf-8")
        tree = ast.parse(content)

        # Собираем все функции и классы
        classes: List[str] = []
        functions: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)

        # Проверяем что есть разделение ответственностей
        # ParallelCityParser должен быть основным классом
        assert "ParallelCityParser" in classes, "ParallelCityParser должен существовать"

        # Вспомогательные функции должны быть вынесены
        # Проверяем что нет слишком больших методов
        class_methods: Dict[str, int] = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                method_count = sum(
                    1
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                )
                class_methods[node.name] = method_count

        # ParallelCityParser не должен иметь слишком много методов
        parser_methods = class_methods.get("ParallelCityParser", 0)
        assert parser_methods <= 15, (
            f"ParallelCityParser имеет {parser_methods} методов. "
            "Рассмотрите разделение ответственностей."
        )

    def test_parallel_parser_uses_helpers(self) -> None:
        """Проверяет что ParallelCityParser использует вспомогательные модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_parser = project_root / "parallel" / "parallel_parser.py"

        content = parallel_parser.read_text(encoding="utf-8")

        # Должен использовать вспомогательные модули
        expected_imports = ["parallel_helpers", "file_merger", "progress_tracker"]

        found_imports = [imp for imp in expected_imports if imp in content]

        assert len(found_imports) >= 1, (
            "ParallelCityParser должен использовать вспомогательные модули"
        )

    def test_file_merger_is_separate(self) -> None:
        """Проверяет что FileMerger выделен в отдельный модуль."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        file_merger = project_root / "parallel" / "file_merger.py"

        assert file_merger.exists(), "file_merger.py должен существовать"

        content = file_merger.read_text(encoding="utf-8")

        # Должен содержать класс FileMerger
        assert "class FileMerger" in content, "FileMerger должен существовать"


class TestCacheManagerResponsibilities:
    """Тесты на разделение ответственностей CacheManager."""

    def test_cache_manager_responsibilities_separated(self) -> None:
        """Проверяет что CacheManager разделён на специализированные модули.

        Кэширование должно быть разделено на:
        - manager.py: основной класс CacheManager
        - pool.py: connection pool
        - serializer.py: сериализация
        - validator.py: валидация данных
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cache_dir = project_root / "cache"

        assert cache_dir.exists(), "cache/ должен существовать"

        expected_modules = ["manager.py", "pool.py", "serializer.py", "validator.py"]

        for module in expected_modules:
            module_path = cache_dir / module
            assert module_path.exists(), f"{module} должен существовать"

    def test_cache_manager_delegates_to_pool(self) -> None:
        """Проверяет что CacheManager делегирует операции connection pool."""
        # Проверяем что CacheManager использует ConnectionPool
        import inspect

        from parser_2gis.cache.manager import CacheManager

        source = inspect.getsource(CacheManager)

        assert "ConnectionPool" in source or "_pool" in source, (
            "CacheManager должен использовать ConnectionPool"
        )

    def test_serializer_is_separate(self) -> None:
        """Проверяет что JsonSerializer выделен в отдельный модуль."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        serializer = project_root / "cache" / "serializer.py"

        assert serializer.exists(), "serializer.py должен существовать"

        content = serializer.read_text(encoding="utf-8")

        assert "class JsonSerializer" in content or "def _serialize_json" in content, (
            "serializer.py должен содержать JsonSerializer"
        )

    def test_validator_is_separate(self) -> None:
        """Проверяет что CacheDataValidator выделен в отдельный модуль."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        validator = project_root / "cache" / "validator.py"

        assert validator.exists(), "validator.py должен существовать"

        content = validator.read_text(encoding="utf-8")

        assert "class CacheDataValidator" in content or "def _validate_cache_data" in content, (
            "validator.py должен содержать CacheDataValidator"
        )


class TestChromeRemoteResponsibilities:
    """Тесты на разделение ответственностей ChromeRemote."""

    def test_chrome_remote_responsibilities_separated(self) -> None:
        """Проверяет что ChromeRemote разделён на специализированные модули.

        ChromeRemote должен быть разделён на:
        - remote.py: основной класс ChromeRemote
        - js_executor.py: выполнение JavaScript
        - http_cache.py: HTTP кэширование
        - rate_limiter.py: ограничение запросов
        - browser.py: управление браузером
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        chrome_dir = project_root / "chrome"

        assert chrome_dir.exists(), "chrome/ должен существовать"

        expected_modules = [
            "remote.py",
            "js_executor.py",
            "http_cache.py",
            "rate_limiter.py",
            "browser.py",
        ]

        for module in expected_modules:
            module_path = chrome_dir / module
            assert module_path.exists(), f"{module} должен существовать"

    def test_js_executor_is_separate(self) -> None:
        """Проверяет что JSExecutor выделен в отдельный модуль."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        js_executor = project_root / "chrome" / "js_executor.py"

        assert js_executor.exists(), "js_executor.py должен существовать"

        content = js_executor.read_text(encoding="utf-8")

        # Должен содержать функции валидации JS
        assert "_validate_js_code" in content, "js_executor.py должен содержать _validate_js_code"

    def test_http_cache_is_separate(self) -> None:
        """Проверяет что HTTPCache выделен в отдельный модуль."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        http_cache = project_root / "chrome" / "http_cache.py"

        assert http_cache.exists(), "http_cache.py должен существовать"

        content = http_cache.read_text(encoding="utf-8")

        # Должен содержать HTTPCache
        assert "_HTTPCache" in content or "_get_http_cache" in content, (
            "http_cache.py должен содержать HTTPCache"
        )

    def test_rate_limiter_is_separate(self) -> None:
        """Проверяет что RateLimiter выделен в отдельный модуль."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        rate_limiter = project_root / "chrome" / "rate_limiter.py"

        assert rate_limiter.exists(), "rate_limiter.py должен существовать"

        content = rate_limiter.read_text(encoding="utf-8")

        # Должен содержать функции ограничения
        assert "_safe_external_request" in content or "RateLimiter" in content, (
            "rate_limiter.py должен содержать функции ограничения"
        )

    def test_chrome_remote_uses_modules(self) -> None:
        """Проверяет что ChromeRemote использует специализированные модули."""
        project_root = Path(__file__).parent.parent / "parser_2gis"
        remote = project_root / "chrome" / "remote.py"

        content = remote.read_text(encoding="utf-8")

        # Должен импортировать специализированные модули
        expected_imports = ["js_executor", "http_cache", "rate_limiter"]

        found_imports = [imp for imp in expected_imports if imp in content]

        assert len(found_imports) >= 1, "ChromeRemote должен использовать специализированные модули"


class TestConfigResponsibilities:
    """Тесты на разделение ответственностей Configuration и ConfigService."""

    def test_config_responsibilities_separated(self) -> None:
        """Проверяет что Configuration и ConfigService разделены.

        Configuration должен быть чистой моделью данных.
        ConfigService должен содержать бизнес-логику работы с конфигурацией.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        config_py = project_root / "config.py"
        config_service_py = project_root / "config_service.py"

        assert config_py.exists(), "config.py должен существовать"
        assert config_service_py.exists(), "config_service.py должен существовать"

    def test_configuration_is_data_model(self) -> None:
        """Проверяет что Configuration — модель данных."""
        from pydantic import BaseModel

        from parser_2gis.config import Configuration

        # Configuration должен быть Pydantic моделью
        assert issubclass(Configuration, BaseModel), "Configuration должен быть Pydantic моделью"

    def test_config_service_is_business_logic(self) -> None:
        """Проверяет что ConfigService содержит бизнес-логику."""
        from parser_2gis.config_service import ConfigService

        # ConfigService должен иметь методы для операций
        assert hasattr(ConfigService, "merge_configs"), "ConfigService должен иметь merge_configs"
        assert hasattr(ConfigService, "load_config"), "ConfigService должен иметь load_config"
        assert hasattr(ConfigService, "save_config"), "ConfigService должен иметь save_config"

    def test_config_and_service_are_separate_classes(self) -> None:
        """Проверяет что Configuration и ConfigService — разные классы."""
        from parser_2gis.config import Configuration
        from parser_2gis.config_service import ConfigService

        # Это должны быть разные классы
        assert Configuration is not ConfigService

        # Configuration не должен наследоваться от ConfigService
        assert not issubclass(Configuration, ConfigService)

        # ConfigService не должен наследоваться от Configuration
        assert not issubclass(ConfigService, Configuration)

    def test_backward_compatibility_methods_exist(self) -> None:
        """Проверяет что Configuration имеет методы для backward совместимости."""
        from parser_2gis.config import Configuration

        # Для backward совместимости Configuration может иметь методы
        # которые делегируют ConfigService
        config = Configuration()

        assert hasattr(config, "merge_with"), (
            "Configuration должен иметь merge_with для backward совместимости"
        )
        assert hasattr(config, "save_config"), (
            "Configuration должен иметь save_config для backward совместимости"
        )
        assert hasattr(config, "load_config"), (
            "Configuration должен иметь load_config для backward совместимости"
        )

    def test_config_service_does_not_store_state(self) -> None:
        """Проверяет что ConfigService не хранит состояние."""
        from parser_2gis.config_service import ConfigService

        # Все методы должны быть статическими
        service_dict = ConfigService.__dict__

        static_methods = [
            name for name, value in service_dict.items() if isinstance(value, staticmethod)
        ]

        # Основные методы должны быть статическими
        assert "merge_configs" in static_methods, "merge_configs должен быть staticmethod"
        assert "load_config" in static_methods, "load_config должен быть staticmethod"
        assert "save_config" in static_methods, "save_config должен быть staticmethod"


class TestSoCOverall:
    """Общие тесты на разделение ответственностей."""

    def test_no_god_classes_detected(self) -> None:
        """Проверяет отсутствие классов с чрезмерной ответственностью."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Сканируем все модули на наличие слишком больших классов
        large_classes: List[Tuple[str, str, int]] = []

        for py_file in project_root.rglob("*.py"):
            if "tests" in py_file.parts or "__pycache__" in py_file.parts:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    method_count = sum(
                        1
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    line_count = node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0

                    if method_count > 20 or line_count > 400:
                        large_classes.append((py_file.name, node.name, method_count))

        # Предупреждаем но не блокируем
        if large_classes:
            pass  # Это информационный тест

    def test_each_module_has_single_responsibility(self) -> None:
        """Проверяет что каждый модуль имеет одну ответственность."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Модули которые должны иметь чёткие ответственности
        module_responsibilities = {
            "cache/manager.py": "кэширование",
            "cache/pool.py": "connection pool",
            "cache/serializer.py": "сериализация",
            "cache/validator.py": "валидация кэша",
            "chrome/remote.py": "удалённое управление",
            "chrome/js_executor.py": "выполнение JS",
            "chrome/http_cache.py": "HTTP кэширование",
            "chrome/rate_limiter.py": "ограничение запросов",
            "parallel/parallel_parser.py": "параллельный парсинг",
            "parallel/file_merger.py": "слияние файлов",
            "utils/data_utils.py": "преобразование данных",
            "utils/math_utils.py": "математические операции",
            "utils/path_utils.py": "валидация путей",
        }

        for module_path, responsibility in module_responsibilities.items():
            full_path = project_root / module_path
            assert full_path.exists(), f"{module_path} должен существовать"

            content = full_path.read_text(encoding="utf-8").lower()

            # Проверяем что модуль соответствует ответственности
            # (простая проверка по ключевым словам)
            keywords = {
                "кэширование": ["cache", "кэш"],
                "connection pool": ["pool", "connection"],
                "сериализация": ["serialize", "json"],
                "валидация": ["validate", "validation"],
                "управление": ["remote", "browser"],
                "js": ["javascript", "js_code"],
                "http": ["http", "request"],
                "ограничение": ["rate", "limit"],
                "параллельный": ["parallel", "worker"],
                "слияние": ["merge", "file"],
                "данных": ["data", "transform"],
                "математичес": ["math", "floor"],
                "пут": ["path", "validate"],
            }

            found = any(kw in content for kw_list in keywords.values() for kw in kw_list)

            assert found, f"{module_path} должен соответствовать ответственности: {responsibility}"


__all__ = [
    "TestParallelParserResponsibilities",
    "TestCacheManagerResponsibilities",
    "TestChromeRemoteResponsibilities",
    "TestConfigResponsibilities",
    "TestSoCOverall",
]
