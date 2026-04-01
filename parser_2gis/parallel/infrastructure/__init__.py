"""
Инфраструктурный модуль для параллельного парсинга.

Предоставляет базовые инфраструктурные компоненты:
- FileManager: Управление файлами
- SemaphoreManager: Управление семафорами
"""

from .file_manager import FileManager
from .semaphore_manager import SemaphoreManager

__all__ = ["FileManager", "SemaphoreManager"]
