"""
Финальные тесты для подтверждения миграции на Textual TUI.

Эти тесты подтверждают:
1. Старый TUI (tui_pytermgui) полностью удален
2. Новый TUI (tui_textual) работает корректно
3. Все ссылки в проекте обновлены на новый TUI
4. Точки входа используют новый TUI
"""

import sys
from pathlib import Path

import pytest

# Добавляем проект в path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOldTUIRemoved:
    """Тесты для подтверждения удаления старого TUI."""

    def test_tui_pytermgui_directory_not_exists(self):
        """Тест: Директория tui_pytermgui не существует."""
        project_root = Path(__file__).parent.parent
        old_tui_dir = project_root / "parser_2gis" / "tui_pytermgui"

        assert not old_tui_dir.exists(), f"Старый TUI модуль должен быть удален: {old_tui_dir}"

    def test_tui_pytermgui_import_fails(self):
        """Тест: Импорт tui_pytermgui вызывает ImportError."""
        with pytest.raises(ImportError):
            from parser_2gis import tui_pytermgui  # noqa: F401

    def test_no_pytermgui_references_in_code(self):
        """Тест: В коде нет ссылок на pytermgui."""
        project_root = Path(__file__).parent.parent
        parser_dir = project_root / "parser_2gis"

        pytermgui_refs = []

        for py_file in parser_dir.rglob("*.py"):
            # Пропускаем кэш директории
            if "__pycache__" in str(py_file):
                continue

            content = py_file.read_text(encoding="utf-8")

            if "pytermgui" in content.lower():
                pytermgui_refs.append(str(py_file))

        assert len(pytermgui_refs) == 0, f"Найдены ссылки на pytermgui в файлах: {pytermgui_refs}"


class TestNewTUIExists:
    """Тесты для подтверждения существования нового TUI."""

    def test_tui_textual_directory_exists(self):
        """Тест: Директория tui_textual существует."""
        project_root = Path(__file__).parent.parent
        new_tui_dir = project_root / "parser_2gis" / "tui_textual"

        assert new_tui_dir.exists(), f"Новый TUI модуль должен существовать: {new_tui_dir}"

    def test_tui_textual_app_exists(self):
        """Тест: Файл app.py существует в tui_textual."""
        project_root = Path(__file__).parent.parent
        app_file = project_root / "parser_2gis" / "tui_textual" / "app.py"

        assert app_file.exists(), f"Файл приложения должен существовать: {app_file}"

    def test_tui_textual_screens_exist(self):
        """Тест: Все экраны существуют в tui_textual."""
        project_root = Path(__file__).parent.parent
        screens_dir = project_root / "parser_2gis" / "tui_textual" / "screens"

        expected_screens = [
            "main_menu.py",
            "city_selector.py",
            "category_selector.py",
            "parsing_screen.py",
            "settings.py",
            "other_screens.py",
        ]

        for screen_file in expected_screens:
            screen_path = screens_dir / screen_file
            assert screen_path.exists(), f"Экран должен существовать: {screen_path}"

    def test_tui_textual_importable(self):
        """Тест: tui_textual модуль импортируется."""
        from parser_2gis.tui_textual import Parser2GISTUI, TUIApp, run_tui

        assert TUIApp is not None
        assert Parser2GISTUI is not None
        assert callable(run_tui)


class TestMainModuleUsesNewTUI:
    """Тесты для подтверждения, что main.py использует новый TUI."""

    def test_main_imports_tui_textual(self):
        """Тест: main.py импортирует tui_textual."""
        import importlib.util
        from pathlib import Path

        # Загружаем модуль main.py напрямую
        main_path = Path(__file__).parent.parent / "parser_2gis" / "main.py"
        _spec = importlib.util.spec_from_file_location("main_module", main_path)

        # Читаем исходный код напрямую из файла
        source = main_path.read_text(encoding="utf-8")

        assert "tui_textual" in source, "main.py должен импортировать tui_textual"

    def test_main_does_not_import_tui_pytermgui(self):
        """Тест: main.py не импортирует tui_pytermgui."""
        from pathlib import Path

        # Загружаем модуль main.py напрямую
        main_path = Path(__file__).parent.parent / "parser_2gis" / "main.py"

        # Читаем исходный код напрямую из файла
        source = main_path.read_text(encoding="utf-8")

        assert "tui_pytermgui" not in source, "main.py не должен импортировать tui_pytermgui"

    def test_run_new_tui_omsk_uses_textual(self):
        """Тест: run_new_tui_omsk использует textual."""
        from pathlib import Path

        # Загружаем модуль main.py напрямую
        main_path = Path(__file__).parent.parent / "parser_2gis" / "main.py"

        # Читаем исходный код напрямую из файла
        source = main_path.read_text(encoding="utf-8")

        # Проверяем что импорт использует tui_textual (не обязательно точно эту строку)
        assert "tui_textual" in source, "main.py должен импортировать из tui_textual"
        assert "pytermgui" not in source, "main.py не должен импортировать из pytermgui"


class TestSetupPyUsesTextual:
    """Тесты для подтверждения, что setup.py использует textual."""

    def test_setup_has_textual_dependency(self):
        """Тест: setup.py имеет textual в зависимостях."""
        project_root = Path(__file__).parent.parent
        setup_file = project_root / "setup.py"

        content = setup_file.read_text(encoding="utf-8")

        assert "textual>=" in content, "setup.py должен содержать textual в зависимостях"

    def test_setup_does_not_have_pytermgui(self):
        """Тест: setup.py не имеет pytermgui в зависимостях."""
        project_root = Path(__file__).parent.parent
        setup_file = project_root / "setup.py"

        content = setup_file.read_text(encoding="utf-8")

        assert "pytermgui" not in content, "setup.py не должен содержать pytermgui"


class TestTUIFunctionality:
    """Тесты для проверки функциональности нового TUI."""

    def test_tui_app_has_screens(self):
        """Тест: TUI приложение имеет все экраны."""
        from parser_2gis.tui_textual import TUIApp

        app = TUIApp()

        expected_screens = [
            "main_menu",
            "city_selector",
            "category_selector",
            "parsing",
            "browser_settings",
            "parser_settings",
            "output_settings",
            "cache_viewer",
            "about",
        ]

        for screen_name in expected_screens:
            assert screen_name in app.SCREENS, f"Экран {screen_name} должен быть зарегистрирован"

    def test_tui_app_has_bindings(self):
        """Тест: TUI приложение имеет горячие клавиши."""
        from parser_2gis.tui_textual import TUIApp

        app = TUIApp()

        assert len(app.BINDINGS) > 0, "TUI должен иметь горячие клавиши"

        binding_keys = [b.key for b in app.BINDINGS]
        assert "q" in binding_keys, "Должна быть клавиша выхода (q)"
        assert "escape" in binding_keys, "Должна быть клавиша назад (escape)"

    def test_tui_app_state_management(self):
        """Тест: TUI приложение управляет состоянием."""
        from parser_2gis.tui_textual import TUIApp

        app = TUIApp()

        # Проверка начального состояния
        assert app.selected_cities == []
        assert app.selected_categories == []

        # Обновление состояния
        app.selected_cities = ["Москва"]
        app.selected_categories = ["Аптеки"]

        assert app.selected_cities == ["Москва"]
        assert app.selected_categories == ["Аптеки"]

    def test_tui_app_config_methods(self):
        """Тест: TUI приложение имеет методы конфигурации."""
        from parser_2gis.tui_textual import TUIApp

        app = TUIApp()

        assert hasattr(app, "get_config"), "Должен быть метод get_config"
        assert hasattr(app, "save_config"), "Должен быть метод save_config"
        assert hasattr(app, "get_cities"), "Должен быть метод get_cities"
        assert hasattr(app, "get_categories"), "Должен быть метод get_categories"

    def test_tui_screens_have_compose(self):
        """Тест: Все экраны имеют метод compose."""
        from parser_2gis.tui_textual.screens import (
            AboutScreen,
            BrowserSettingsScreen,
            CacheViewerScreen,
            CategorySelectorScreen,
            CitySelectorScreen,
            MainMenuScreen,
            OutputSettingsScreen,
            ParserSettingsScreen,
            ParsingScreen,
        )

        screens = [
            MainMenuScreen,
            CitySelectorScreen,
            CategorySelectorScreen,
            ParsingScreen,
            BrowserSettingsScreen,
            ParserSettingsScreen,
            OutputSettingsScreen,
            CacheViewerScreen,
            AboutScreen,
        ]

        for screen_class in screens:
            assert hasattr(screen_class, "compose"), (
                f"{screen_class.__name__} должен иметь метод compose"
            )


class TestProjectStructure:
    """Тесты для проверки структуры проекта."""

    def test_only_one_tui_module_exists(self):
        """Тест: Существует только один TUI модуль."""
        project_root = Path(__file__).parent.parent
        parser_dir = project_root / "parser_2gis"

        tui_dirs = [d for d in parser_dir.iterdir() if d.is_dir() and d.name.startswith("tui_")]

        assert len(tui_dirs) == 1, (
            f"Должен быть только один TUI модуль, найдено: {[d.name for d in tui_dirs]}"
        )
        assert tui_dirs[0].name == "tui_textual", "TUI модуль должен называться tui_textual"

    def test_no_old_tui_test_files(self):
        """Тест: Нет тестов для старого TUI."""
        project_root = Path(__file__).parent.parent
        tests_dir = project_root / "tests"

        # Ищем файлы с именами, указывающими на старый TUI
        old_tui_tests = [f for f in tests_dir.glob("*.py") if "pytermgui" in f.name]

        assert len(old_tui_tests) == 0, (
            f"Не должно быть тестов для старого TUI: {[f.name for f in old_tui_tests]}"
        )
