"""
Список категорий для TUI Parser2GIS.
"""

from typing import Any, Callable, Optional

import pytermgui as ptg


class CategoryList:
    """
    Виджет списка категорий.

    Предоставляет список категорий с чекбоксами для выбора.
    """

    def __init__(
        self,
        categories: list[dict[str, Any]],
        selected_indices: Optional[set[int]] = None,
        on_select: Optional[Callable[[int, bool], None]] = None,
        height: int = 10,
    ) -> None:
        """
        Инициализация списка категорий.

        Args:
            categories: Список категорий (словари с ключами name, query, rubric_code)
            selected_indices: Индексы выбранных категорий
            on_select: Callback при изменении выбора
            height: Высота виджета
        """
        self._categories = categories
        self._selected_indices = selected_indices or set()
        self._on_select = on_select
        self._height = height
        self._container: Optional[ptg.Container] = None

        self._populate()

    def _populate(self) -> None:
        """Заполнить контейнер категориями."""
        if not self._container:
            self._container = ptg.Container()

        self._container.widgets.clear()

        for i, category in enumerate(self._categories):
            category_name = category.get("name", "Неизвестно")

            is_selected = i in self._selected_indices
            checkbox = ptg.Checkbox(
                label=category_name,
                value=is_selected,
                on_change=lambda checked, idx=i: self._toggle_category(idx, checked),
            )

            self._container.add_widget(checkbox)

    def _toggle_category(self, index: int, checked: bool) -> None:
        """
        Переключить выбор категории.

        Args:
            index: Индекс категории
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
        Рендерить список категорий.

        Returns:
            Container со списком категорий
        """
        if not self._container:
            self._populate()

        return self._container

    def select_all(self) -> None:
        """Выбрать все категории."""
        for i in range(len(self._categories)):
            self._selected_indices.add(i)

        if self._container:
            self._populate()

    def deselect_all(self) -> None:
        """Снять все категории."""
        self._selected_indices.clear()

        if self._container:
            self._populate()

    def get_selected(self) -> list[str]:
        """
        Получить список выбранных категорий.

        Returns:
            Список названий выбранных категорий
        """
        return [
            self._categories[i].get("name", "")
            for i in sorted(self._selected_indices)
        ]

    @property
    def selected_count(self) -> int:
        """Количество выбранных категорий."""
        return len(self._selected_indices)

    @property
    def total_count(self) -> int:
        """Общее количество категорий."""
        return len(self._categories)
