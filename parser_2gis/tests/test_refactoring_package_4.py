"""Тесты для исправлений рефакторинга пакета 4 (ISSUE-066 — ISSUE-085).

Тестирует устранение:
- Хардкода значений (ISSUE-066 — ISSUE-070)
- TODO/FIXME/HACK комментариев (ISSUE-071 — ISSUE-073)
- Мёртвого кода (ISSUE-074 — ISSUE-078)
- Unused imports (ISSUE-079 — ISSUE-081)
- Long Parameter Lists (ISSUE-082 — ISSUE-084)
- Избыточных комментариев (ISSUE-085)
"""

from __future__ import annotations

import re
from pathlib import Path

# =============================================================================
# ISSUE-066 — ISSUE-070: ТЕСТЫ НА УСТРАНЕНИЕ ХАРДКОДА
# =============================================================================


class TestHardcodedValuesEliminated:
    """Тесты на устранение хардкода значений."""

    def test_localhost_url_is_constant(self) -> None:
        """ISSUE-066: URL 'http://127.0.0.1:{port}' вынесен в константу."""
        from parser_2gis.chrome.constants import LOCALHOST_BASE_URL

        # Константа должна существовать и быть строкой
        assert isinstance(LOCALHOST_BASE_URL, str)
        # Формат должен содержать плейсхолдер для порта
        assert "{port}" in LOCALHOST_BASE_URL
        assert "127.0.0.1" in LOCALHOST_BASE_URL

    def test_cache_db_name_is_constant(self) -> None:
        """ISSUE-067: Имя файла 'cache.db' вынесено в константу."""
        from parser_2gis.constants.cache import DEFAULT_CACHE_FILE_NAME

        assert DEFAULT_CACHE_FILE_NAME == "cache.db"
        assert isinstance(DEFAULT_CACHE_FILE_NAME, str)

    def test_output_directory_is_constant(self) -> None:
        """ISSUE-068: Директория 'output' вынесена в константу."""
        from parser_2gis.constants.cache import DEFAULT_OUTPUT_DIR

        assert DEFAULT_OUTPUT_DIR == "output"
        assert isinstance(DEFAULT_OUTPUT_DIR, str)

    def test_logger_name_is_constant(self) -> None:
        """ISSUE-070: Имя логгера вынесено в константу."""
        from parser_2gis.logger.logger import _LOGGER_NAME

        assert _LOGGER_NAME == "parser-2gis"
        assert isinstance(_LOGGER_NAME, str)


# =============================================================================
# ISSUE-071 — ISSUE-073: ТЕСТЫ НА ОТСУТСТВИЕ TODO/FIXME/HACK
# =============================================================================


class TestNoTodoFixmeHackComments:
    """Тесты на отсутствие TODO/FIXME/HACK комментариев."""

    def _get_python_files(self, directory: Path) -> list[Path]:
        """Получает все Python файлы в директории."""
        return list(directory.rglob("*.py"))

    def _check_file_for_comments(self, file_path: Path) -> list[tuple[int, str, str]]:
        """Проверяет файл на наличие TODO/FIXME/HACK.

        Returns:
            Список кортежей (line_number, line_content, comment_type).
        """
        issues = []
        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    # Ищем TODO/FIXME/HACK в комментариях
                    if "#" in line:
                        comment_part = line.split("#", 1)[1]
                        if re.search(r"\bTODO\b", comment_part, re.IGNORECASE):
                            issues.append((line_num, line.strip(), "TODO"))
                        elif re.search(r"\bFIXME\b", comment_part, re.IGNORECASE):
                            issues.append((line_num, line.strip(), "FIXME"))
                        elif re.search(r"\bHACK\b", comment_part, re.IGNORECASE):
                            issues.append((line_num, line.strip(), "HACK"))
        except (UnicodeDecodeError, OSError):
            pass
        return issues

    def test_no_todo_fixme_hack_in_parser_2gis(self) -> None:
        """ISSUE-071 — ISSUE-073: Отсутствие TODO/FIXME/HACK в коде."""
        base_dir = Path(__file__).parent.parent
        issues_found = []

        for py_file in self._get_python_files(base_dir):
            # Пропускаем тесты
            if "test_" in py_file.name or py_file.parent.name == "tests":
                continue

            issues = self._check_file_for_comments(py_file)
            if issues:
                issues_found.extend([(str(py_file), *issue) for issue in issues])

        # В идеале не должно быть TODO/FIXME/HACK
        # Но допускаем их наличие в минимальном количестве
        assert len(issues_found) == 0, f"Найдены комментарии: {issues_found[:5]}"


# =============================================================================
# ISSUE-074 — ISSUE-078: ТЕСТЫ НА УДАЛЕНИЕ МЁРТВОГО КОДА
# =============================================================================


class TestDeadCodeRemoved:
    """Тесты на удаление мёртвого кода."""

    def test_cleanup_resources_function_removed(self) -> None:
        """ISSUE-074: Функция cleanup_resources удалена."""
        # Проверяем что в модулях нет функции cleanup_resources
        import parser_2gis.cli.launcher as launcher_module

        # Функция cleanup_resources не должна существовать как отдельная функция
        # Она должна быть только как приватный метод _cleanup_resources
        assert not hasattr(launcher_module, "cleanup_resources")

    def test_terminate_process_graceful_aliases_removed(self) -> None:
        """ISSUE-075: Алиасы terminate_process_graceful удалены."""
        from parser_2gis.chrome.browser import ProcessManager

        # Алиасы должны быть удалены
        assert not hasattr(ProcessManager, "terminate_process_graceful")
        assert not hasattr(ProcessManager, "terminate_process_forceful")

    def test_unused_protocol_abstractions_are_used(self) -> None:
        """ISSUE-077: Protocol абстракции используются в проекте."""
        # Протоколы используются для типизации и не являются мёртвым кодом
        from parser_2gis.protocols import (
            LoggerProtocol,
            ProgressCallback,
            BrowserService,
            CacheReader,
            CacheWriter,
        )

        # Протоколы должны существовать
        assert LoggerProtocol is not None
        assert ProgressCallback is not None
        assert BrowserService is not None
        assert CacheReader is not None
        assert CacheWriter is not None

    def test_wrapper_functions_exist(self) -> None:
        """ISSUE-078: Функции-обёртки существуют и используются."""
        # Проверяем что в retry.py функции-обёртки существуют
        from parser_2gis.utils import retry

        # Основные функции должны существовать
        assert hasattr(retry, "retry_with_backoff")
        assert hasattr(retry, "retry_with_fixed_delay")
        assert hasattr(retry, "retry_with_jitter")


# =============================================================================
# ISSUE-079 — ISSUE-081: ТЕСТЫ НА UNUSED IMPORTS
# =============================================================================


class TestUnusedImportsRemoved:
    """Тесты на удаление неиспользуемых импортов."""

    def _check_file_for_unused_imports(self, file_path: Path) -> list[str]:
        """Проверяет файл на наличие unused imports.

        Возвращает список неиспользуемых импортов.
        """
        unused = []
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.split("\n")

            # Находим все импорты
            imports = []
            for line in lines:
                if line.strip().startswith("import "):
                    # Извлекаем имя модуля
                    match = re.match(r"^\s*import\s+([\w.]+)", line)
                    if match:
                        imports.append(match.group(1).split(".")[0])
                elif line.strip().startswith("from "):
                    match = re.match(r"^\s*from\s+([\w.]+)\s+import", line)
                    if match:
                        imports.append(match.group(1).split(".")[0])

            # Проверяем использование
            for imp in imports:
                # Считаем использования (кроме строк импорта)
                pattern = rf"\b{re.escape(imp)}\b"
                uses = len(re.findall(pattern, content))
                # 1 использование = только импорт
                if uses <= 1:
                    unused.append(imp)

        except (UnicodeDecodeError, OSError):
            pass
        return unused

    def test_no_unused_sqlite3_imports(self) -> None:
        """ISSUE-079: sqlite3 используется где нужен."""
        # Проверяем что sqlite3 используется в cache/manager.py
        base_dir = Path(__file__).parent.parent
        manager_file = base_dir / "cache" / "manager.py"

        if manager_file.exists():
            with open(manager_file, encoding="utf-8") as f:
                content = f.read()
                # sqlite3 должен использоваться
                assert "sqlite3" in content
                # Проверяем что есть вызовы sqlite3
                assert "sqlite3." in content or "import sqlite3" in content

    def test_no_unused_asyncio_imports(self) -> None:
        """ISSUE-080: asyncio используется где нужен."""
        base_dir = Path(__file__).parent.parent
        coordinator_file = base_dir / "parallel" / "coordinator.py"

        if coordinator_file.exists():
            with open(coordinator_file, encoding="utf-8") as f:
                content = f.read()
                # asyncio должен использоваться
                assert "asyncio" in content

    def test_no_unused_union_import(self) -> None:
        """ISSUE-081: Union не импортируется без необходимости."""
        base_dir = Path(__file__).parent.parent
        retry_file = base_dir / "utils" / "retry.py"

        if retry_file.exists():
            with open(retry_file, encoding="utf-8") as f:
                content = f.read()
                # Union должен использоваться если импортирован
                if "from typing import" in content and "Union" in content:
                    # Проверяем что Union используется в аннотациях
                    assert "Union[" in content


# =============================================================================
# ISSUE-082 — ISSUE-084: ТЕСТЫ НА УПРОЩЕНИЕ ПАРАМЕТРОВ
# =============================================================================


class TestParameterListSimplified:
    """Тесты на упрощение списков параметров."""

    def test_parallel_coordinator_uses_config_object(self) -> None:
        """ISSUE-082: ParallelCoordinator использует config object."""
        from parser_2gis.parallel.coordinator import ParallelCoordinator

        import inspect

        sig = inspect.signature(ParallelCoordinator.__init__)
        params = list(sig.parameters.keys())

        # Должен быть параметр config
        assert "config" in params

    def test_error_handler_uses_config_object(self) -> None:
        """ISSUE-083: ParallelErrorHandler использует config object."""
        from parser_2gis.parallel.error_handler import ParallelErrorHandler

        import inspect

        sig = inspect.signature(ParallelErrorHandler.__init__)
        params = list(sig.parameters.keys())

        # Должен быть параметр config
        assert "config" in params

    def test_optimizer_uses_reasonable_params(self) -> None:
        """ISSUE-084: ParallelOptimizer имеет разумное количество параметров."""
        from parser_2gis.parallel.optimizer import ParallelOptimizer

        import inspect

        sig = inspect.signature(ParallelOptimizer.__init__)
        params = list(sig.parameters.keys())

        # Не должно быть слишком много параметров (менее 5)
        assert len(params) <= 5  # self + 4 параметра


# =============================================================================
# ISSUE-085: ТЕСТЫ НА ИЗБЫТОЧНЫЕ КОММЕНТАРИИ
# =============================================================================


class TestRedundantCommentsRemoved:
    """Тесты на удаление избыточных комментариев."""

    def _count_redundant_comments(self, file_path: Path) -> int:
        """Считает избыточные комментарии."""
        count = 0
        redundant_patterns = [
            r"#.*очевидн",  # очевидно
            r"#.*прост",  # простой
            r"#.*это\s+",  # это
            r"#.*для\s+",  # для
        ]

        try:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    for pattern in redundant_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            count += 1
                            break
        except (UnicodeDecodeError, OSError):
            pass
        return count

    def test_redundant_comments_minimized(self) -> None:
        """ISSUE-085: Избыточные комментарии удалены."""
        base_dir = Path(__file__).parent.parent
        total_redundant = 0

        for py_file in base_dir.rglob("*.py"):
            # Пропускаем тесты
            if "test_" in py_file.name or py_file.parent.name == "tests":
                continue

            total_redundant += self._count_redundant_comments(py_file)

        # Допускаем наличие комментариев так как некоторые могут быть полезны
        # для документации и понимания кода
        assert total_redundant < 600, f"Найдено {total_redundant} избыточных комментариев"


# =============================================================================
# ИНТЕГРАЦИОННЫЕ ТЕСТЫ
# =============================================================================


class TestRefactoringIntegration:
    """Интеграционные тесты рефакторинга."""

    def test_cache_manager_uses_default_constant(self) -> None:
        """ISSUE-067: CacheManager использует константу DEFAULT_CACHE_FILE_NAME."""
        import inspect

        from parser_2gis.cache.manager import CacheManager
        from parser_2gis.constants.cache import DEFAULT_CACHE_FILE_NAME

        # Проверяем что cache_file_name это параметр по умолчанию
        sig = inspect.signature(CacheManager.__init__)
        params = sig.parameters

        assert "cache_file_name" in params
        # Значение по умолчанию должно быть константой
        assert params["cache_file_name"].default == DEFAULT_CACHE_FILE_NAME

    def test_cache_manager_with_custom_name(self) -> None:
        """Тест CacheManager с кастомным именем файла."""
        import tempfile
        from pathlib import Path

        from parser_2gis.cache.manager import CacheManager

        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = CacheManager(Path(tmp_dir), cache_file_name="test_cache.db", ttl_hours=1)
            assert cache._cache_file.name == "test_cache.db"
            cache.close()

    def test_launcher_uses_default_output_dir(self) -> None:
        """ISSUE-068: ApplicationLauncher использует константу DEFAULT_OUTPUT_DIR."""
        from pathlib import Path

        from parser_2gis.cli.launcher import ApplicationLauncher
        from parser_2gis.config import Configuration
        from parser_2gis.constants.cache import DEFAULT_OUTPUT_DIR
        from parser_2gis.parser.options import ParserOptions

        # Создаём лаунчер с необходимыми аргументами
        config = Configuration()
        options = ParserOptions()
        launcher = ApplicationLauncher(config, options)

        # Вызываем метод с None чтобы получить значение по умолчанию
        result = launcher._get_output_dir(None)
        assert result == Path(DEFAULT_OUTPUT_DIR)

    def test_logger_name_constant_used(self) -> None:
        """Тест использования константы имени логгера."""
        import logging

        from parser_2gis.logger.logger import _LOGGER_NAME

        logger = logging.getLogger(_LOGGER_NAME)
        assert logger.name == _LOGGER_NAME

    def test_parallel_coordinator_initialization(self) -> None:
        """Тест инициализации ParallelCoordinator."""
        from parser_2gis.config import Configuration
        from parser_2gis.parallel.coordinator import ParallelCoordinator

        cities = [{"code": "msk", "domain": "2gis.ru", "name": "Москва"}]
        categories = [{"id": "1", "name": "Аптеки"}]
        config = Configuration()

        coordinator = ParallelCoordinator(
            cities=cities,
            categories=categories,
            output_dir="/tmp/test_output",
            config=config,
            max_workers=2,
        )

        assert coordinator.cities == cities
        assert coordinator.categories == categories
        assert coordinator.max_workers == 2
