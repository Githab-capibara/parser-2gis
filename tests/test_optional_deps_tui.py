"""Тест проверяет что все опциональные TUI зависимости установлены."""

import pytest


def test_textual_is_installed():
    """Проверяет что textual импортируется."""
    try:
        import textual
    except ImportError:
        pytest.fail("textual не установлен. Установите: pip install textual")


def test_textual_version():
    """Проверяет минимальную версию textual."""
    import textual
    from packaging import version

    min_version = version.parse("0.50.0")
    actual_version = version.parse(textual.__version__)

    assert (
        actual_version >= min_version
    ), f"Версия textual ({actual_version}) меньше минимальной ({min_version})"


def test_textual_widgets_importable():
    """Проверяет что основные виджеты textual доступны."""
    try:
        from textual.app import App, ComposeResult
        from textual.containers import Container, VerticalScroll
        from textual.widgets import Button, Footer, Header, Input, Label, Static
    except ImportError as e:
        pytest.fail(f"Не удалось импортировать виджет textual: {e}")
