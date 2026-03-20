"""Модуль Chrome для управления браузером.

Предоставляет классы и функции для работы с Chrome:
- ChromeRemote - удалённое управление через DevTools Protocol
- ChromeOptions - настройка параметров браузера
"""

from .options import ChromeOptions
from .remote import ChromeRemote

__all__ = ["ChromeRemote", "ChromeOptions"]
