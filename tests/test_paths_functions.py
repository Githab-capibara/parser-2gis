"""
Тесты для проверки наличия критических функций в модуле paths.

Этот тест предотвращает ошибки типа ImportError, когда в коде TUI
используются функции, которые не были определены в модуле paths.

Тест проверяет:
1. Наличие всех ожидаемых функций в модуле paths
2. Корректность работы каждой функции
3. Отсутствие ошибок импорта при использовании функций из TUI
"""

import pathlib


class TestPathsModuleFunctions:
    """Тесты для проверки наличия и работы функций в модуле paths."""

    def test_data_path_exists(self) -> None:
        """Проверка, что функция data_path существует и работает."""
        from parser_2gis.utils.paths import data_path

        result = data_path()
        assert isinstance(result, pathlib.Path)
        assert result.exists()

    def test_user_path_exists(self) -> None:
        """Проверка, что функция user_path существует и работает."""
        from parser_2gis.utils.paths import user_path

        # Проверяем для конфигурации
        config_path = user_path(is_config=True)
        assert isinstance(config_path, pathlib.Path)

        # Проверяем для данных
        data_path_result = user_path(is_config=False)
        assert isinstance(data_path_result, pathlib.Path)

    def test_image_path_exists(self) -> None:
        """Проверка, что функция image_path существует."""
        from parser_2gis.utils.paths import image_path

        # Проверяем, что функция определена
        assert callable(image_path)

    def test_image_data_exists(self) -> None:
        """Проверка, что функция image_data существует."""
        from parser_2gis.utils.paths import image_data

        # Проверяем, что функция определена
        assert callable(image_data)

    def test_cache_path_exists(self) -> None:
        """
        Проверка, что функция cache_path существует и работает.

        Этот тест предотвращает ошибку ImportError, когда функция
        используется в TUI, но не определена в модуле paths.
        """
        from parser_2gis.utils.paths import cache_path

        # Проверяем, что функция существует
        assert callable(cache_path)

        # Проверяем, что функция возвращает Path
        result = cache_path()
        assert isinstance(result, pathlib.Path)

        # Проверяем, что путь содержит 'parser-2gis'
        assert "parser-2gis" in str(result)

    def test_cache_path_uses_xdg_cache_home(self) -> None:
        """
        Проверка, что cache_path использует XDG_CACHE_HOME.

        Функция должна использовать переменную окружения XDG_CACHE_HOME
        или fallback на ~/.cache.
        """
        import os

        from parser_2gis.utils.paths import cache_path

        # Сохраняем оригинальное значение
        original_xdg = os.environ.get("XDG_CACHE_HOME")

        try:
            # Тест с кастомным XDG_CACHE_HOME
            test_cache_dir = "/tmp/test_cache_dir"
            os.environ["XDG_CACHE_HOME"] = test_cache_dir

            # Очищаем кэш lru_cache для пересчета
            cache_path.cache_clear()

            result = cache_path()
            assert str(result).startswith(test_cache_dir)
            assert "parser-2gis" in str(result)

        finally:
            # Восстанавливаем оригинальное значение
            if original_xdg is not None:
                os.environ["XDG_CACHE_HOME"] = original_xdg
            else:
                os.environ.pop("XDG_CACHE_HOME", None)

            # Очищаем кэш для возврата к оригинальному поведению
            cache_path.cache_clear()

    def test_cache_path_fallback_to_home_cache(self) -> None:
        """
        Проверка, что cache_path fallback на ~/.cache.

        Если XDG_CACHE_HOME не установлен, функция должна использовать
        ~/.cache как fallback.
        """
        import os

        from parser_2gis.utils.paths import cache_path

        # Сохраняем оригинальное значение
        original_xdg = os.environ.get("XDG_CACHE_HOME")

        try:
            # Удаляем XDG_CACHE_HOME
            os.environ.pop("XDG_CACHE_HOME", None)

            # Очищаем кэш lru_cache для пересчета
            cache_path.cache_clear()

            result = cache_path()

            # Проверяем, что путь содержит .cache
            assert ".cache" in str(result)
            assert "parser-2gis" in str(result)

        finally:
            # Восстанавливаем оригинальное значение
            if original_xdg is not None:
                os.environ["XDG_CACHE_HOME"] = original_xdg

            # Очищаем кэш
            cache_path.cache_clear()


class TestTUIPathImports:
    """
    Тесты для проверки импортов из paths в TUI модулях.

    Эти тесты предотвращают ошибки импорта, подобные той, что была
    в CacheViewerScreen, когда используется несуществующая функция.
    """

    def test_cache_viewer_screen_can_import_cache_path(self) -> None:
        """
        Проверка, что CacheViewerScreen может импортировать cache_path.

        Тест проверяет, что импорт cache_path из parser_2gis.paths
        работает корректно и может быть использован в TUI.
        """
        # Этот импорт должен работать без ошибок
        from parser_2gis.utils.paths import cache_path

        # Проверяем, что функция может быть вызвана
        result = cache_path()
        assert isinstance(result, pathlib.Path)

    def test_other_screens_module_has_valid_imports(self) -> None:
        """
        Проверка, что other_screens.py имеет валидные импорты.

        Тест проверяет, что все импорты в other_screens.py работают
        корректно, включая cache_path из parser_2gis.paths.
        """
        # Импортируем весь модуль other_screens
        from parser_2gis.tui_textual.screens import other_screens

        # Проверяем, что модуль загружен
        assert other_screens is not None

        # Проверяем, что классы определены
        assert hasattr(other_screens, "CacheViewerScreen")
        assert hasattr(other_screens, "AboutScreen")

    def test_all_paths_functions_used_in_tui_are_available(self) -> None:
        """
        Проверка, что все функции paths, используемые в TUI, доступны.

        Тест проверяет наличие всех функций, которые могут быть
        использованы в TUI экранах.
        """
        from parser_2gis.utils import paths

        # Список функций, которые должны быть доступны
        required_functions = ["data_path", "user_path", "image_path", "image_data", "cache_path"]

        for func_name in required_functions:
            assert hasattr(paths, func_name), (
                f"Функция '{func_name}' отсутствует в модуле paths. "
                f"Это может вызвать ImportError в TUI."
            )
            func = getattr(paths, func_name)
            assert callable(func), f"'{func_name}' не является вызываемым объектом"
