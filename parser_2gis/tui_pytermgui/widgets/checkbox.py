"""
Кастомный виджет Checkbox с поддержкой label и on_change.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

import pytermgui as ptg


class Checkbox(ptg.Container):
    """
    Кастомный Checkbox с поддержкой label и on_change.

    Обёртка над стандартным Checkbox из pytermgui, добавляющая поддержку:
    - label: текстовая метка рядом с checkbox
    - value: начальное состояние (checked/unchecked)
    - on_change: callback при изменении состояния
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
            **attrs: Дополнительные атрибуты для Container
        """
        super().__init__(box="EMPTY_HORIZONTAL", **attrs)

        self._on_change = on_change
        self._value = value

        # Создаём стандартный Checkbox
        self._checkbox = ptg.Checkbox(
            checked=value,
            callback=self._on_toggle,
        )

        # Создаём Label с текстом
        self._label = ptg.Label(label)

        # Добавляем виджеты в контейнер (используем приватный метод _add_widget)
        self._add_widget(self._checkbox)
        self._add_widget(self._label)

    @property
    def value(self) -> bool:
        """Получить текущее значение checkbox."""
        return self._value

    @value.setter
    def value(self, new_value: bool) -> None:
        """Установить новое значение checkbox."""
        if self._value != new_value:
            self._value = new_value
            # Синхронизируем с внутренним checkbox
            if self._checkbox.checked != new_value:
                self._checkbox.toggle(run_callback=False)

    def _on_toggle(self, checked: bool) -> None:
        """
        Обработчик переключения checkbox.

        Args:
            checked: Новое состояние checkbox
        """
        self._value = checked
        if self._on_change:
            self._on_change(checked)

    def toggle(self) -> None:
        """Переключить состояние checkbox."""
        self._checkbox.toggle()
