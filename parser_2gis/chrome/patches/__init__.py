from .pychrome import patch_pychrome

def patch_all():
    """Применяет все пользовательские патчи."""
    patch_pychrome()
