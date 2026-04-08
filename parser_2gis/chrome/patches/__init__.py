"""Модуль патчей для Chrome.

Предоставляет функции для применения пользовательских патчей
к библиотеке pychrome.
"""

from .pychrome import patch_pychrome


def patch_all() -> None:
    """Применяет все пользовательские патчи."""
    patch_pychrome()
