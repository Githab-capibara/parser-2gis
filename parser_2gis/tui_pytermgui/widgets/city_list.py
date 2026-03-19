"""
Список городов для TUI Parser2GIS.
"""

from typing import Any, Callable, Optional

import pytermgui as ptg

from .checkbox import Checkbox


class CityList:
    """
    Виджет списка городов.

    Предоставляет список городов с чекбоксами для выбора.
    """

    def __init__(
        self,
        cities: list[dict[str, Any]],
        selected_indices: Optional[set[int]] = None,
        on_select: Optional[Callable[[int, bool], None]] = None,
    ) -> None:
        """
        Инициализация списка городов.

        Args:
            cities: Список городов (словари с ключами name, code, domain, country_code)
            selected_indices: Индексы выбранных городов
            on_select: Callback при изменении выбора
        """
        self._cities = cities
        self._selected_indices = selected_indices or set()
        self._on_select = on_select
        self._container: Optional[ptg.Container] = None

        self._populate()

    def _populate(self) -> None:
        """Заполнить контейнер городами."""
        if not self._container:
            self._container = ptg.Container()

        # Исправлено: используем _widgets для доступа к списку виджетов
        if hasattr(self._container, "_widgets"):
            self._container._widgets.clear()
        elif hasattr(self._container, "widgets"):
            self._container.widgets.clear()

        for i, city in enumerate(self._cities):
            city_name = city.get("name", "Неизвестно")
            country = city.get("country_code", "").upper()

            is_selected = i in self._selected_indices
            checkbox = Checkbox(
                label=f"{city_name} ({country})",
                value=is_selected,
                on_change=lambda checked, idx=i: self._toggle_city(idx, checked),
            )

            # Исправлено: используем _add_widget вместо add_widget
            if hasattr(self._container, "_add_widget"):
                self._container._add_widget(checkbox)
            elif hasattr(self._container, "add_widget"):
                self._container.add_widget(checkbox)

    def _toggle_city(self, index: int, checked: bool) -> None:
        """
        Переключить выбор города.

        Args:
            index: Индекс города
            checked: Состояние чекбокса
        """
        if checked:
            self._selected_indices.add(index)
        else:
            self._selected_indices.discard(index)

        if self._on_select:
            self._on_select(index, checked)

    def render(self) -> ptg.Container:
        """
        Рендерить список городов.

        Returns:
            Container со списком городов
        """
        if not self._container:
            self._populate()

        return self._container

    def select_all(self) -> None:
        """Выбрать все города."""
        for i in range(len(self._cities)):
            self._selected_indices.add(i)

        if self._container:
            self._populate()

    def deselect_all(self) -> None:
        """Снять все города."""
        self._selected_indices.clear()

        if self._container:
            self._populate()

    def get_selected(self) -> list[str]:
        """
        Получить список выбранных городов.

        Returns:
            Список названий выбранных городов
        """
        return [self._cities[i].get("name", "") for i in sorted(self._selected_indices)]

    @property
    def selected_count(self) -> int:
        """Количество выбранных городов."""
        return len(self._selected_indices)

    @property
    def total_count(self) -> int:
        """Общее количество городов."""
        return len(self._cities)
