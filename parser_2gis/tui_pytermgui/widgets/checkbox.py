"""
Кастомный виджет Checkbox с поддержкой label и on_change.

Поддерживает навигацию с клавиатуры:
- Enter - переключение состояния
- Визуальное отображение фокуса
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
    - Обработка клавиши Enter для переключения
    - Визуальное отображение фокуса
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
        self._focused = False

        # Символы для checkbox
        self._checked_symbol = "[green]✓[/]"
        self._unchecked_symbol = "[dim]○[/]"

        # Стили для отображения фокуса
        self._focused_prefix = "[bold cyan on dark_gray]>[/]"
        self._unfocused_prefix = "  "

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

    @property
    def focused(self) -> bool:
        """Получить состояние фокуса."""
        return self._focused

    @focused.setter
    def focused(self, value: bool) -> None:
        """
        Установить состояние фокуса.

        Args:
            value: True если виджет в фокусе
        """
        self._focused = value

    def get_lines(self) -> list[str]:
        """
        Получить строки для отображения.

        Returns:
            Список строк для рендеринга
        """
        symbol = self._checked_symbol if self._value else self._unchecked_symbol
        prefix = self._focused_prefix if self._focused else self._unfocused_prefix

        # Добавляем визуальное отображение фокуса
        if self._focused:
            line = f"{prefix}[bold cyan]{symbol} {self._label}[/]"
            # Преобразовать TIM-теги в ANSI-коды для правильного отображения
            return [ptg.tim.parse(line)]
        line = f"{prefix}{symbol} {self._label}"
        # Преобразовать TIM-теги в ANSI-коды для правильного отображения
        return [ptg.tim.parse(line)]

    def handle_key(self, key: str) -> bool:
        """
        Обработать нажатие клавиши.

        Args:
            key: Код нажатой клавиши

        Returns:
            True если клавиша обработана
        """
        # Вызываем базовый обработчик
        if super().handle_key(key):
            return True

        # Обработка клавиши Enter для переключения состояния
        if key == ptg.keys.ENTER:
            self.toggle()
            return True

        return False

    def on_left_click(self, event: ptg.MouseEvent) -> bool:
        """
        Обработчик левого клика.

        Args:
            event: Событие мыши

        Returns:
            True если событие обработано
        """
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

    def focus(self) -> None:
        """Получить фокус."""
        self._focused = True

    def blur(self) -> None:
        """Потерять фокус."""
        self._focused = False
