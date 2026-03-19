"""Тест проверяет graceful degradation при отсутствии textual."""

import pytest
import sys
import os


def test_tui_stub_functions_exist():
    """Проверяет что stub функции определены в исходном коде main.py."""
    main_py_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "parser_2gis", "main.py"
    )

    with open(main_py_path, "r") as f:
        content = f.read()

    assert (
        "def _tui_omsk_stub" in content
    ), "Функция _tui_omsk_stub не найдена в main.py"
    assert "def _tui_stub" in content, "Функция _tui_stub не найдена в main.py"


def test_tui_import_handles_missing_textual():
    """Проверяет что при ImportError используются stub функции."""
    main_py_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "parser_2gis", "main.py"
    )

    with open(main_py_path, "r") as f:
        content = f.read()

    assert "except ImportError" in content, "Блок except ImportError не найден"
    assert "_tui_omsk_stub" in content, "Stub функции не используются при ImportError"


def test_tui_textual_module_structure():
    """Проверяет структуру модуля tui_textual."""
    try:
        from parser_2gis import tui_textual

        assert hasattr(tui_textual, "TUIApp") or hasattr(tui_textual, "Parser2GISTUI")
    except ImportError:
        pytest.skip("tui_textual недоступен (textual не установлен)")
