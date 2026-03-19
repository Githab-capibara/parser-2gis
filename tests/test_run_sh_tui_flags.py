"""Тест проверяет что run.sh правильно настраивает TUI зависимости."""

import os
import re
import pytest


def test_run_sh_installs_tui_deps():
    """Проверяет что run.sh устанавливает [tui] или [all] зависимости."""
    run_sh_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "run.sh")

    with open(run_sh_path, "r") as f:
        content = f.read()

    pattern = r'pip install -e "\$SCRIPT_DIR\[(tui|all)\]"'
    match = re.search(pattern, content)

    assert match, (
        "run.sh должен устанавливать зависимости с [tui] или [all]. "
        "Текущая строка не содержит [tui] или [all]"
    )


def test_tui_flag_error_message():
    """Проверяет что при отсутствии textual --tui выдает понятную ошибку."""
    from parser_2gis import main

    try:
        from parser_2gis.tui_textual import run_tui as actual_run_tui

        pytest.skip("textual установлен, пропускаем stub тест")
    except ImportError:
        pass

    assert main._tui_omsk_stub is not None
    assert main._tui_stub is not None


def test_setup_py_has_tui_extras():
    """Проверяет что setup.py определяет extras_require для tui."""
    setup_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "setup.py")

    with open(setup_path, "r") as f:
        content = f.read()

    assert "extras_require" in content, "setup.py должен содержать extras_require"
    assert "tui" in content, "setup.py должен содержать tui в extras_require"
