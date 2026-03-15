"""
Базовый класс для виджетов с поддержкой навигации с клавиатуры.

Предоставляет общую функциональность для обработки клавиш:
- Tab - переключение фокуса на следующий элемент
- Shift+Tab - переключение фокуса на предыдущий элемент
- Enter - активация элемента
- Esc - возврат назад
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import pytermgui as ptg

if TYPE_CHECKING:
    from ..app import TUIApp


class NavigableWidget(ptg.Widget):
    """
    Базовый класс для виджетов с поддержкой навигации.

    Реализует обработку клавиатурных событий для навигации
    между элементами интерфейса.
    """

    def __init__(self, *args, **kwargs) -> None:
        """
        Инициализация навигируемого виджета.

        Args:
            *args: Позиционные аргументы для базового класса
            **kwargs: Именованные аргументы для базового класса
        """
        super().__init__(*args, **kwargs)
        self._focused = False
        self._app: Optional[TUIApp] = None

    def set_app(self, app: TUIApp) -> None:
        """
        Установить ссылку на приложение.

        Args:
            app: Экземпляр приложения TUIApp
        """
        self._app = app

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
        # Принудительная перерисовка при изменении фокуса
        if self._app and hasattr(self._app, '_manager'):
            manager = getattr(self._app, '_manager', None)
            if manager:
                manager.force_full_redraw = True

    def handle_key(self, key: str) -> bool:
        """
        Обработать нажатие клавиши.

        Args:
            key: Код нажатой клавиши

        Returns:
            True если клавиша обработана, False иначе
        """
        # Вызываем базовый обработчик
        if super().handle_key(key):
            return True

        # Обработка клавиши Enter для активации
        if key == ptg.keys.ENTER:
            return self.on_enter()

        return False

    def on_enter(self) -> bool:
        """
        Обработчик нажатия Enter.

        Returns:
            True если событие обработано
        """
        # По умолчанию ничего не делаем
        return False

    def focus(self) -> None:
        """Получить фокус."""
        self.focused = True

    def blur(self) -> None:
        """Потерять фокус."""
        self.focused = False

    def get_lines(self) -> list[str]:
        """
        Получить строки для отображения.

        Returns:
            Список строк для рендеринга
        """
        return []


class NavigableContainer(ptg.Container):
    """
    Контейнер с поддержкой навигации между дочерними виджетами.

    Реализует циклическую навигацию с клавиатуры:
    - Tab - следующий элемент
    - Shift+Tab - предыдущий элемент
    """

    def __init__(self, *widgets, **kwargs) -> None:
        """
        Инициализация навигируемого контейнера.

        Args:
            *widgets: Дочерние виджеты
            **kwargs: Аргументы для базового класса Container
        """
        super().__init__(*widgets, **kwargs)
        self._focus_index = -1
        self._app = None

    def set_app(self, app) -> None:
        """
        Установить ссылку на приложение.

        Args:
            app: Экземпляр приложения
        """
        self._app = app
        # Передать app всем дочерним виджетам
        for widget in self._widgets:
            if hasattr(widget, 'set_app'):
                widget.set_app(app)

    @property
    def focus_index(self) -> int:
        """Индекс текущего сфокусированного виджета."""
        return self._focus_index

    @focus_index.setter
    def focus_index(self, value: int) -> None:
        """
        Установить индекс фокуса.

        Args:
            value: Новый индекс фокуса
        """
        # Снять фокус с текущего виджета
        if 0 <= self._focus_index < len(self._widgets):
            widget = self._widgets[self._focus_index]
            if hasattr(widget, 'blur'):
                widget.blur()

        # Циклическая навигация
        if value < 0:
            value = len(self._widgets) - 1
        elif value >= len(self._widgets):
            value = 0

        self._focus_index = value

        # Установить фокус на новый виджет
        if 0 <= self._focus_index < len(self._widgets):
            widget = self._widgets[self._focus_index]
            if hasattr(widget, 'focus'):
                widget.focus()

        # Принудительная перерисовка
        if self._app and hasattr(self._app, '_manager'):
            manager = getattr(self._app, '_manager', None)
            if manager:
                manager.force_full_redraw = True

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

        # Обработка Tab - следующий элемент
        if key == ptg.keys.TAB:
            self.focus_next()
            return True

        # Обработка Shift+Tab - предыдущий элемент
        if key == ptg.keys.SHIFT_TAB:
            self.focus_prev()
            return True

        # Если есть сфокусированный виджет, передать клавишу ему
        if 0 <= self._focus_index < len(self._widgets):
            widget = self._widgets[self._focus_index]
            if hasattr(widget, 'handle_key'):
                if widget.handle_key(key):
                    return True

        return False

    def focus_next(self) -> None:
        """Переключить фокус на следующий виджет."""
        self.focus_index = self._focus_index + 1

    def focus_prev(self) -> None:
        """Переключить фокус на предыдущий виджет."""
        self.focus_index = self._focus_index - 1

    def focus_first(self) -> None:
        """Установить фокус на первый виджет."""
        if self._widgets:
            self.focus_index = 0

    def add_widget(self, widget, focus: bool = False) -> None:
        """
        Добавить виджет в контейнер.

        Args:
            widget: Виджет для добавления
            focus: Установить ли фокус на этот виджет
        """
        self._add_widget(widget)
        # Передать app новому виджету
        if self._app and hasattr(widget, 'set_app'):
            widget.set_app(self._app)
        # Установить фокус если нужно
        if focus:
            self.focus_index = len(self._widgets) - 1

    def get_focused_widget(self):
        """
        Получить текущий сфокусированный виджет.

        Returns:
            Сфокусированный виджет или None
        """
        if 0 <= self._focus_index < len(self._widgets):
            return self._widgets[self._focus_index]
        return None


class ButtonWidget(NavigableWidget):
    """
    Виджет кнопки с поддержкой навигации.

    Обёртка над стандартной кнопкой pytermgui с добавлением
    обработки клавиш Enter и визуального отображения фокуса.
    """

    def __init__(
        self,
        label: str,
        callback=None,
        **kwargs
    ) -> None:
        """
        Инициализация кнопки.

        Args:
            label: Текст кнопки
            callback: Функция обратного вызова при активации
            **kwargs: Дополнительные аргументы для NavigableWidget
        """
        super().__init__(**kwargs)
        self._label = label
        self._callback = callback
        self._base_style = "[bold white on blue]"
        self._focused_style = "[bold black on cyan]"

    def get_lines(self) -> list[str]:
        """
        Получить строки для отображения.

        Returns:
            Список строк для рендеринга
        """
        style = self._focused_style if self._focused else self._base_style
        return [f"{style} {self._label} [/]"]

    def handle_key(self, key: str) -> bool:
        """
        Обработать нажатие клавиши.

        Args:
            key: Код нажатой клавиши

        Returns:
            True если клавиша обработана
        """
        if super().handle_key(key):
            return True

        # Обработка Enter для активации
        if key == ptg.keys.ENTER:
            self.activate()
            return True

        return False

    def on_enter(self) -> bool:
        """
        Обработчик нажатия Enter.

        Returns:
            True если событие обработано
        """
        self.activate()
        return True

    def activate(self) -> None:
        """Активировать кнопку (вызвать callback)."""
        if self._callback:
            self._callback()

    def on_left_click(self, event: ptg.MouseEvent) -> bool:
        """
        Обработчик левого клика.

        Args:
            event: Событие мыши

        Returns:
            True если событие обработано
        """
        # Активируем кнопку при клике
        self.activate()
        return True
