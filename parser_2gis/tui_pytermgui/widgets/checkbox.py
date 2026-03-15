"""
Кастомный виджет Checkbox с поддержкой label и on_change.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import pytermgui as ptg


class Checkbox(ptg.Widget):
    """
    Кастомный Checkbox с поддержкой label и on_change.

    Реализует правильный API pytermgui:
    - Создаётся без параметров в базовом классе
    - Обработка кликов через on_left_click
    - Поддержка callback при изменении состояния
    """

    def __init__(
        self,
        label: str = "",
        value: bool = False,
        on_change: Optional[Callable[[bool], Any]] = None,
        **attrs: Any,
    ) -> None:
        """
        Инициализация Checkbox.

        Args:
            label: Текстовая метка рядом с checkbox
            value: Начальное состояние (True = отмечено)
            on_change: Callback функция, вызываемая при изменении состояния
            **attrs: Дополнительные атрибуты для Widget
        """
        # Инициализация базового класса без параметров
        super().__init__(**attrs)

        self._label = label
        self._value = value
        self._on_change = on_change

        # Символы для checkbox
        self._checked_symbol = "[green]✓[/green]"
        self._unchecked_symbol = "[dim]○[/dim]"

    @property
    def value(self) -> bool:
        """Получить текущее значение checkbox."""
        return self._value

    @value.setter
    def value(self, new_value: bool) -> None:
        """Установить новое значение checkbox."""
        if self._value != new_value:
            self._value = new_value
            if self._on_change:
                self._on_change(new_value)

    def get_lines(self) -> list[str]:
        """
        Получить строки для отображения.

        Returns:
            Список строк для рендеринга
        """
        symbol = self._checked_symbol if self._value else self._unchecked_symbol
        return [f"{symbol} {self._label}"]

    def on_left_click(self, event: ptg.MouseEvent) -> bool:
        """
        Обработчик левого клика.

        Args:
            event: Событие мыши

        Returns:
            True если событие обработано
        """
        # Вызываем базовый обработчик
        if super().on_left_click(event):
            return True

        # Переключаем состояние
        self._value = not self._value

        # Вызываем callback если есть
        if self._on_change:
            self._on_change(self._value)

        return True

    def toggle(self) -> None:
        """Переключить состояние checkbox."""
        self._value = not self._value
        if self._on_change:
            self._on_change(self._value)
