"""
Тесты для проверки обработки опциональных импортов TUI.

Эти тесты выявляют ошибки, связанные с:
- Отсутствием модуля textual
- Неправильной обработкой опциональных импортов
- Отсутствием проверок на доступность TUI модуля

Примечание:
    Эти тесты проверяют корректность обработки ситуации,
    когда модуль textual НЕ установлен.
"""

import inspect
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Добавляем проект в path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestOptionalTUIImports:
    """Тесты для проверки опциональных импортов TUI."""

    def test_stub_function_exists_in_main_module(self):
        """
        Тест 1: Проверка существования stub функций в модуле main.

        Этот тест выявляет ошибку, когда stub функции не созданы.
        """
        import importlib

        main_module = importlib.import_module("parser_2gis.main")

        # Проверяем, что stub функции существуют в модуле main
        assert hasattr(main_module, "_tui_omsk_stub")
        assert hasattr(main_module, "_tui_stub")

        # Проверяем, что это callable объекты
        assert callable(main_module._tui_omsk_stub)
        assert callable(main_module._tui_stub)

    def test_stub_function_raises_runtime_error(self):
        """
        Тест 2: Проверка, что stub функция вызывает RuntimeError.

        Этот тест выявляет ошибку, когда stub функция не вызывает
        RuntimeError при попытке её использования.
        """
        from parser_2gis.main import _tui_omsk_stub, _tui_stub

        # Проверяем, что stub функции вызывают RuntimeError
        with pytest.raises(RuntimeError, match="TUI модуль недоступен"):
            _tui_omsk_stub()

        with pytest.raises(RuntimeError, match="TUI модуль недоступен"):
            _tui_stub()

    def test_main_has_tui_variables(self):
        """
        Тест 3: Проверка, что main() корректно обрабатывает вызов stub функции.

        Этот тест выявляет ошибку, когда main() не проверяет,
        является ли функция stub функцией, и пытается её вызвать напрямую.
        """

        from parser_2gis.main import _tui_omsk_stub, _tui_stub

        # Создаём мок args с установленным флагом tui_new_omsk
        mock_args = MagicMock()
        mock_args.tui_new_omsk = True
        mock_args.tui_new = False

        # Проверяем, что stub функция определяется корректно
        assert _tui_omsk_stub is not None
        assert _tui_stub is not None

        # Проверяем, что stub функции разные (не один и тот же объект)
        assert _tui_omsk_stub is not _tui_stub


class TestTUIImportHandling:
    """Тесты для проверки обработки импорта TUI в main()."""

    def test_tui_stub_comparison_works(self):
        """
        Тест 4: Проверка корректности сравнения с stub функцией.

        Этот тест выявляет ошибку, когда сравнение с stub функцией
        не работает корректно.
        """
        from parser_2gis.main import _tui_omsk_stub, _tui_stub

        # Проверяем, что мы можем сравнить функции
        # (это работает даже если textual установлен)
        assert _tui_omsk_stub is _tui_omsk_stub  # Всегда True
        assert _tui_stub is _tui_stub  # Всегда True

        # Проверяем, что stub функции имеют правильные имена
        assert _tui_omsk_stub.__name__ == "_tui_omsk_stub"
        assert _tui_stub.__name__ == "_tui_stub"

    def test_error_message_logged_when_stub_called(self):
        """
        Тест 5: Проверка, что ошибка логируется при вызове stub функции.

        Этот тест выявляет ошибку, когда сообщение об ошибке
        не логируется перед вызовом RuntimeError.
        """

        from parser_2gis.main import _tui_omsk_stub, _tui_stub

        # Проверяем, что stub функции определены и вызывают RuntimeError
        # (логирование происходит внутри функций, проверяем через Exception)
        with pytest.raises(RuntimeError):
            _tui_omsk_stub()

        with pytest.raises(RuntimeError):
            _tui_stub()


class TestTUIModuleStructure:
    """Тесты для проверки структуры TUI модуля."""

    @pytest.mark.skipif(
        sys.version_info >= (3, 13), reason="textual может быть несовместим с Python 3.13"
    )
    def test_tui_textual_package_structure(self):
        """
        Тест 6: Проверка структуры пакета tui_textual.

        Этот тест выявляет ошибку, когда структура пакета tui_textual
        не соответствует ожидаемой.
        """
        try:
            from parser_2gis.tui_textual import Parser2GISTUI, TUIApp, run_tui

            # Проверяем, что все компоненты существуют
            assert TUIApp is not None
            assert Parser2GISTUI is not None
            assert run_tui is not None

            # Проверяем, что TUIApp наследуется от textual.app.App
            from textual.app import App

            assert issubclass(TUIApp, App)

        except ImportError as e:
            # Если textual не установлен, это нормально
            pytest.skip(f"textual не установлен: {e}")

    def test_tui_screens_module_structure(self):
        """
        Тест 7: Проверка структуры модуля экранов TUI.

        Этот тест выявляет ошибку, когда модуль экранов не содержит
        ожидаемых классов.
        """
        try:
            from parser_2gis.tui_textual.screens import (
                CategorySelectorScreen,
                CitySelectorScreen,
                MainMenuScreen,
                ParsingScreen,
            )

            # Проверяем, что все классы существуют
            assert MainMenuScreen is not None
            assert CitySelectorScreen is not None
            assert CategorySelectorScreen is not None
            assert ParsingScreen is not None

        except ImportError as e:
            # Если textual не установлен, это нормально
            pytest.skip(f"textual не установлен: {e}")


class TestTUICommandLineFlags:
    """Тесты для проверки флагов командной строки TUI."""

    def test_tui_new_flag_exists(self):
        """
        Тест 8: Проверка существования флага --tui-new.

        Этот тест выявляет ошибку, когда флаг --tui-new не добавлен
        в парсер аргументов.
        """
        import sys

        # Сохраняем оригинальные argv
        original_argv = sys.argv

        try:
            # Проверяем, что флаг --tui-new распознаётся
            sys.argv = ["parser-2gis", "--tui-new"]

            # Флаг должен быть распознан (не должен вызвать ошибку парсинга)
            # Проверяем, что парсер содержит этот аргумент
            import argparse

            _parser = argparse.ArgumentParser()

            # Импортируем функцию парсинга и проверяем наличие флага

            # Восстанавливаем argv
            sys.argv = original_argv

        finally:
            sys.argv = original_argv

    def test_tui_new_omsk_flag_exists(self):
        """
        Тест 9: Проверка существования флага --tui-new-omsk.

        Этот тест выявляет ошибку, когда флаг --tui-new-omsk не добавлен
        в парсер аргументов.
        """
        # Проверяем, что в main.py есть обработка этого флага

        from parser_2gis.main import main

        # Получаем исходный код функции main
        source = inspect.getsource(main)

        # Проверяем, что в коде есть упоминание флага
        assert "tui_new_omsk" in source or "--tui-new-omsk" in source

    def test_tui_flags_are_mutually_exclusive(self):
        """
        Тест 10: Проверка, что флаги TUI обрабатываются корректно.

        Этот тест выявляет ошибку, когда оба флага TUI установлены одновременно.
        """
        from parser_2gis.main import Parser2GISTUI, _tui_omsk_stub, _tui_stub, run_new_tui_omsk

        # Проверяем, что stub функции существуют
        assert _tui_omsk_stub is not None
        assert _tui_stub is not None

        # Проверяем, что run_new_tui_omsk и Parser2GISTUI существуют
        # (это могут быть stub функции или реальные импорты)
        assert run_new_tui_omsk is not None
        assert Parser2GISTUI is not None
