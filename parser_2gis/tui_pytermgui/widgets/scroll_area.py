"""
Кастомные виджеты для TUI Parser2GIS.
"""

from __future__ import annotations

from typing import Any

import pytermgui as ptg


class ScrollArea(ptg.ScrollableWidget):
    """
    Виджет области с прокруткой.

    Обёртка над ScrollableWidget для создания прокручиваемой области
    с фиксированной высотой.

    Attributes:
        content: Контент для отображения
        height: Фиксированная высота области
    """

    def __init__(self, content: ptg.Widget, height: int = 10, **kwargs: Any) -> None:
        """
        Инициализация области прокрутки.

        Args:
            content: Виджет контента для отображения
            height: Высота области прокрутки
            **kwargs: Дополнительные аргументы для ScrollableWidget
        """
        super().__init__(**kwargs)
        self._content = content
        self._height = height
        self._scroll_offset = 0

    def get_lines(self) -> list[str]:
        """
        Получить линии для отображения.

        Returns:
            Список строк для отображения
        """
        # Получить строки от контента
        content_lines = []

        # Если контент - контейнер с виджетами
        if hasattr(self._content, "widgets"):
            # Используем публичный API для доступа к виджетам
            widgets = getattr(self._content, "widgets", [])
            if widgets:
                for widget in widgets:
                    if hasattr(widget, "get_lines"):
                        try:
                            lines = widget.get_lines()
                            if isinstance(lines, (list, tuple)):
                                content_lines.extend(lines)
                            else:
                                content_lines.append(str(lines))
                        except Exception as widget_error:
                            # При ошибке добавляем строковое представление виджета
                            content_lines.append(str(widget))
                            from ..logger import logger

                            logger.debug(
                                "Ошибка при получении строк виджета: %s", widget_error
                            )
                    else:
                        content_lines.append(str(widget))
        elif hasattr(self._content, "get_lines"):
            lines = self._content.get_lines()
            if isinstance(lines, (list, tuple)):
                content_lines.extend(lines)
            else:
                content_lines = [str(lines)]
        else:
            # Преобразовать контент в строки
            content_str = str(self._content)
            content_lines = content_str.split("\n")

        # Применить прокрутку с проверкой на выход за границы
        if self._scroll_offset > 0 and self._scroll_offset < len(content_lines):
            content_lines = content_lines[self._scroll_offset :]

        # Обрезать по высоте
        return content_lines[: self._height]

    def __len__(self) -> int:
        """Вернуть высоту области."""
        return self._height


__all__ = ["ScrollArea"]
