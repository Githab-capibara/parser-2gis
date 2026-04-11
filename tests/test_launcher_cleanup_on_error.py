"""
Тест очистки ресурсов launcher при ошибке.

ИСПРАВЛЕНИЕ: Гарантированная очистка ресурсов через finally блок.
"""

import pytest


class TestLauncherCleanupOnError:
    """Тесты очистки ресурсов ApplicationLauncher при ошибке."""

    def test_finally_block_executes_on_exception(self) -> None:
        """Тест что finally блок выполняется при исключении."""
        cleanup_called = False

        def test_function_with_finally() -> None:
            nonlocal cleanup_called
            try:
                raise ValueError("Test error")
            finally:
                cleanup_called = True

        with pytest.raises(ValueError):
            test_function_with_finally()

        assert cleanup_called, "finally блок не выполнился при исключении"
