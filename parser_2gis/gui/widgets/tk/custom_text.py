from __future__ import annotations

import tkinter as tk
from typing import Any


class CustomText(tk.Text):
    """Пользовательский текстовый виджет, который сообщает о внутренних командах виджета."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Создаём прокси для базового виджета
        widget_name = self._w  # type: ignore[attr-defined]
        self._orig = widget_name + '_orig'
        self.tk.call('rename', widget_name, self._orig)
        self.tk.createcommand(widget_name, self._proxy)

    def _proxy(self, *args) -> Any:
        # Позволяем реальному виджету выполнить запрошенное действие
        cmd = (self._orig,) + args

        try:
            result = self.tk.call(cmd)
        except tk.TclError:
            result = ''

        # Генерируем событие, если что-то было добавлено или удалено,
        # или позиция курсора изменилась.
        if (
            args[0] in ('insert', 'replace', 'delete')
            or args[0:3] == ('mark', 'set', 'insert')
            or args[0:2] == ('xview', 'moveto')
            or args[0:2] == ('xview', 'scroll')
            or args[0:2] == ('yview', 'moveto')
            or args[0:2] == ('yview', 'scroll')
        ):

            self.event_generate('<<Change>>', when='tail')

        # Возвращаем то, что вернул реальный виджет
        return result
