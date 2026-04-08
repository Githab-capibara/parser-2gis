"""Protocol для типизации TUI приложения Parser2GIS.

Этот модуль предоставляет Protocol ITuiApp, который описывает контракт
между экранами (Screen) и главным приложением (Parser2GISApp).
Использование Protocol устраняет необходимость в массовых
`# type: ignore[attr-defined]` при обращении к `self.app` из экранов.

Пример использования:
    >>> from .protocols import ITuiApp
    >>> class MyScreen(Screen):
    ...     app: ITuiApp  # type: ignore[assignment]
    ...     def on_mount(self) -> None:
    ...         cities = self.app.get_cities()  # type-checker понимает тип
"""

from __future__ import annotations

from typing import Any, Protocol

from parser_2gis.config import Configuration


class ITuiApp(Protocol):
    """Protocol главного приложения TUI Parser2GIS.

    Описывает все публичные атрибуты и методы, к которым обращаются экраны.
    """

    # -------------------------------------------------------------------------
    # Состояние (атрибуты)
    # -------------------------------------------------------------------------
    selected_cities: list[str]
    selected_categories: list[str]

    # -------------------------------------------------------------------------
    # Данные
    # -------------------------------------------------------------------------
    def get_cities(self) -> list[dict[str, Any]]:
        """Возвращает список доступных городов."""
        ...

    def get_categories(self) -> list[dict[str, str | int]]:
        """Возвращает список категорий."""
        ...

    def get_config(self) -> Configuration:
        """Возвращает текущую конфигурацию."""
        ...

    def save_config(self) -> None:
        """Сохраняет конфигурацию."""
        ...

    # -------------------------------------------------------------------------
    # Навигация
    # -------------------------------------------------------------------------
    def switch_screen(self, screen_id: str) -> None:
        """Переключает активный экран."""
        ...

    def pop_screen(self) -> None:
        """Возвращает к предыдущему экрану."""
        ...

    def push_screen(self, screen_id: str) -> None:
        """Добавляет новый экран в стек."""
        ...

    def exit(self) -> None:
        """Завершает работу приложения."""
        ...

    # -------------------------------------------------------------------------
    # Парсинг
    # -------------------------------------------------------------------------
    def start_parsing(self, cities: list[dict], categories: list[dict]) -> None:
        """Запускает процесс парсинга."""
        ...

    def stop_parsing(self) -> None:
        """Останавливает процесс парсинга."""
        ...

    # -------------------------------------------------------------------------
    # Уведомления
    # -------------------------------------------------------------------------
    def notify(self, message: str, *, title: str = "", timeout: float = 5) -> None:
        """Отправляет уведомление."""
        ...

    def notify_user(self, message: str, level: str = "info") -> None:
        """Отправляет уведомление пользователю."""
        ...
