"""
Интерфейсы и Protocol для разрыва циклических зависимостей.

Этот модуль содержит Protocol для основных интерфейсов проекта,
что позволяет устранить циклические импорты между модулями.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LoggerProtocol(Protocol):
    """Protocol для логгера.

    Используется для разрыва циклической зависимости между
    common.py и logger.py.
    """

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Логирование debug сообщения."""
        ...

    def info(self, msg: str, *args, **kwargs) -> None:
        """Логирование info сообщения."""
        ...

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Логирование warning сообщения."""
        ...

    def error(self, msg: str, *args, **kwargs) -> None:
        """Логирование error сообщения."""
        ...

    def critical(self, msg: str, *args, **kwargs) -> None:
        """Логирование critical сообщения."""
        ...


__all__ = ["LoggerProtocol"]
