"""
Тесты для выявления ошибок импорта в TUI модулях.

Проверяют:
1. Корректность импортов в TUI экранах.
2. Доступность модулей paths, cache и других критических модулей.
3. Отсутствие ошибок импорта при загрузке TUI экранов.
"""

import pathlib
import tempfile

import pytest


class TestTUIImports:
    """Тесты для проверки импортов в TUI модулях."""

    def test_paths_module_importable(self):
        """Проверка, что модуль paths импортируется."""
        try:
            from parser_2gis import paths

            assert paths is not None
            assert hasattr(paths, "user_path")
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать parser_2gis.paths: {e}")

    def test_cache_module_importable(self):
        """Проверка, что модуль cache импортируется."""
        try:
            from parser_2gis.cache import CacheManager

            assert CacheManager is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать parser_2gis.cache: {e}")

    def test_other_screens_imports(self):
        """
        Проверка, что other_screens.py не содержит ошибок импорта.

        Тест выявляет ошибки типа:
        - from ..paths import cache_path (неправильный относительный импорт)
        - from ..cache import CacheManager (неправильный относительный импорт)

        Правильно:
        - from parser_2gis.paths import cache_path
        - from parser_2gis.cache import CacheManager
        """
        try:
            from parser_2gis.tui_textual.screens.other_screens import AboutScreen, CacheViewerScreen

            assert CacheViewerScreen is not None
            assert AboutScreen is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать other_screens: {e}")
        except ModuleNotFoundError as e:
            pytest.fail(f"Ошибка импорта модуля в other_screens: {e}")


class TestTUIModuleImports:
    """Тесты для проверки импортов во всех TUI экранах."""

    def test_all_screens_importable(self):
        """Проверка, что все TUI экраны импортируются без ошибок."""
        screens_to_test = [
            "parser_2gis.tui_textual.screens.main_menu",
            "parser_2gis.tui_textual.screens.city_selector",
            "parser_2gis.tui_textual.screens.category_selector",
            "parser_2gis.tui_textual.screens.settings",
            "parser_2gis.tui_textual.screens.other_screens",
        ]

        for screen_module in screens_to_test:
            try:
                __import__(screen_module)
            except ImportError as e:
                pytest.fail(f"Не удалось импортировать {screen_module}: {e}")
            except ModuleNotFoundError as e:
                pytest.fail(f"Ошибка импорта в {screen_module}: {e}")

    def test_tui_app_importable(self):
        """Проверка, что TUI приложение импортируется без ошибок."""
        try:
            from parser_2gis.tui_textual.app import TUIApp

            assert TUIApp is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать TUI приложение: {e}")
        except ModuleNotFoundError as e:
            pytest.fail(f"Ошибка импорта в TUI приложении: {e}")


class TestRelativeImportErrors:
    """
    Тесты для обнаружения некорректных относительных импортов.

    Относительные импорты вида 'from ..module' работают только
    когда модуль находится на правильном уровне вложенности.
    """

    def test_no_invalid_relative_imports_in_screens(self):
        """
        Проверка отсутствия некорректных относительных импортов в экранах.

        Скриншоты находятся в parser_2gis.tui_textual.screens.*,
        поэтому импорты из parser_2gis должны использовать:
        - Абсолютные: from parser_2gis.module import ...
        - Или относительные с тремя точками: from ...module import ...
        """
        import os
        import re

        screens_dir = os.path.join(
            os.path.dirname(__file__), "..", "parser_2gis", "tui_textual", "screens"
        )
        screens_dir = os.path.abspath(screens_dir)

        # Паттерн для поиска некорректных импортов
        # from ..paths, from ..cache, from ..config и т.д.
        # Это неправильно, потому что screens находится на 2 уровня вложенности
        # от parser_2gis, а не на 1
        invalid_pattern = re.compile(
            r"^from \.\. (paths|cache|config|data|parallel_parser)\s+import"
        )

        errors = []
        for filename in os.listdir(screens_dir):
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(screens_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            matches = invalid_pattern.findall(content, re.MULTILINE)
            if matches:
                errors.append(f"Файл {filename} содержит некорректные импорты: {matches}")

        if errors:
            pytest.fail(
                "Обнаружены некорректные относительные импорты в TUI экранах:\n" + "\n".join(errors)
            )

    def test_cache_viewer_screen_imports_correctly(self):
        """
        Проверка, что CacheViewerScreen использует правильные импорты.

        Тест специально проверяет, что импорты в CacheViewerScreen
        используют абсолютные пути (from parser_2gis.xxx import),
        а не относительные (from ..xxx import).
        """
        import inspect

        from parser_2gis.tui_textual.screens.other_screens import CacheViewerScreen

        # Получаем исходный код метода _load_cache_stats
        source = inspect.getsource(CacheViewerScreen._load_cache_stats)

        # Проверяем, что используется правильный импорт
        assert (
            "from parser_2gis.paths import" in source or "from ...paths import" in source
        ), "CacheViewerScreen должен использовать правильный импорт paths"

    def test_cache_viewer_action_clear_imports_correctly(self):
        """
        Проверка, что action_clear_cache использует правильные импорты.
        """
        import inspect

        from parser_2gis.tui_textual.screens.other_screens import CacheViewerScreen

        # Получаем исходный код метода action_clear_cache
        source = inspect.getsource(CacheViewerScreen.action_clear_cache)

        # Проверяем, что используются правильные импорты
        assert (
            "from parser_2gis.cache import" in source or "from ...cache import" in source
        ), "action_clear_cache должен использовать правильный импорт cache"

        assert (
            "from parser_2gis.paths import" in source or "from ...paths import" in source
        ), "action_clear_cache должен использовать правильный импорт paths"


class TestCriticalModuleAvailability:
    """Тесты для проверки доступности критических модулей."""

    def test_user_path_function_exists(self):
        """Проверка, что функция user_path существует и вызывается."""
        from parser_2gis.paths import user_path

        result = user_path()
        assert isinstance(result, pathlib.Path)

    def test_cache_manager_instantiable(self):
        """Проверка, что CacheManager может быть создан."""
        from parser_2gis.cache import CacheManager

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_manager = CacheManager(cache_dir=pathlib.Path(tmpdir))
            assert cache_manager is not None

    def test_config_module_accessible(self):
        """Проверка доступности модуля config."""
        try:
            from parser_2gis.config import Configuration

            assert Configuration is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать Configuration: {e}")

    def test_parallel_parser_module_accessible(self):
        """Проверка доступности модуля parallel_parser."""
        try:
            from parser_2gis.parallel_parser import ParallelCityParser

            assert ParallelCityParser is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать ParallelCityParser: {e}")
