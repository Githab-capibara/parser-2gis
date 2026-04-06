"""Вспомогательные функции для проверки логов в тестах."""

import pytest


def assert_log_contains(caplog: pytest.LogCaptureFixture, *expected_substrings: str) -> None:
    """Проверяет что лог содержит все указанные подстроки.

    Args:
        caplog: Фикстура caplog из pytest.
        *expected_substrings: Подстроки которые должны быть в логе.

    Raises:
        AssertionError: Если лог не содержит одну из подстрок.
    """
    log_text = caplog.text
    for expected in expected_substrings:
        assert expected in log_text, f"Лог не содержит: '{expected}'"


def assert_log_does_not_contain(
    caplog: pytest.LogCaptureFixture, *forbidden_substrings: str
) -> None:
    """Проверяет что лог НЕ содержит указанные подстроки.

    Args:
        caplog: Фикстура caplog из pytest.
        *forbidden_substrings: Подстроки которых не должно быть в логе.

    Raises:
        AssertionError: Если лог содержит одну из запрещённых подстрок.
    """
    log_text = caplog.text
    for forbidden in forbidden_substrings:
        assert forbidden not in log_text, f"Лог не должен содержать: '{forbidden}'"
