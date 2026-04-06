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
    def get_cities(self) -> list[dict[str, Any]]: ...
    def get_categories(self) -> list[dict[str, str | int]]: ...
    def get_config(self) -> Configuration: ...
    def save_config(self) -> None: ...

    # -------------------------------------------------------------------------
    # Навигация
    # -------------------------------------------------------------------------
    def switch_screen(self, screen_id: str) -> None: ...
    def pop_screen(self) -> None: ...
    def push_screen(self, screen_id: str) -> None: ...
    def exit(self) -> None: ...

    # -------------------------------------------------------------------------
    # Парсинг
    # -------------------------------------------------------------------------
    def start_parsing(self, cities: list[dict], categories: list[dict]) -> None: ...
    def stop_parsing(self) -> None: ...

    # -------------------------------------------------------------------------
    # Уведомления
    # -------------------------------------------------------------------------
    def notify(self, message: str, *, title: str = "", timeout: float = 5) -> None: ...
    def notify_user(self, message: str, level: str = "info") -> None: ...
