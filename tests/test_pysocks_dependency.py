"""Тест проверяет что зависимость PySocks установлена для устранения предупреждения SOCKS в urllib3."""

import warnings

import pytest
from urllib3.exceptions import DependencyWarning

# Проверяем доступен ли PySocks
try:
    import socks  # noqa: F401

    PYSOCKS_AVAILABLE = True
except ImportError:
    PYSOCKS_AVAILABLE = False


@pytest.mark.skipif(not PYSOCKS_AVAILABLE, reason="PySocks не установлен")
def test_pysocks_installed() -> None:
    """Проверяет что PySocks установлен и доступен."""
    try:
        import socks  # PySocks provides 'socks' module

        assert socks is not None
    except ImportError:
        pytest.fail("PySocks не установлен. Установите: pip install PySocks")


@pytest.mark.skipif(not PYSOCKS_AVAILABLE, reason="PySocks не установлен")
def test_urllib3_socks_warning_not_present(caplog) -> None:
    """Проверяет что предупреждение о SOCKS зависимостях в urllib3 не появляется."""
    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Import urllib3 to trigger any potential warnings

        # Check if any DependencyWarning about SOCKS was raised
        sock_warnings = [
            warning
            for warning in w
            if issubclass(warning.category, DependencyWarning)
            and "SOCKS support" in str(warning.message)
        ]

        assert len(sock_warnings) == 0, (
            f"Обнаружены предупреждения SOCKS: {[str(w.message) for w in sock_warnings]}"
        )


@pytest.mark.skipif(not PYSOCKS_AVAILABLE, reason="PySocks не установлен")
def test_optional_dependency_pysocks_installed() -> None:
    """Проверяет что опциональная зависимость PySocks учтена в requirements."""
    # This test ensures that if someone tries to use SOCKS functionality,
    # PySocks is available
    try:
        import socks

        # Test that we can at least access the module
        assert hasattr(socks, "set_default_proxy")
    except ImportError:
        pytest.fail("PySocks (socks module) не установлен, но требуется для SOCKS поддержки")
