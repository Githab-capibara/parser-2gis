from __future__ import annotations

import tkinter as tk
from typing import Any


class CustomEntry(tk.Entry):
    """Пользовательский виджет Entry, который сообщает о внутренних командах виджета."""
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Создаём прокси для базового виджета
        widget_name = self._w  # type: ignore[attr-defined]
        self._orig = widget_name + '_orig'
        self.tk.call('rename', widget_name, self._orig)
        self.tk.createcommand(widget_name, self._proxy)

    def _proxy(self, command: Any, *args) -> Any:
        # Позволяем реальному виджету выполнить запрошенное действие
        cmd = (self._orig, command) + args

        try:
            result = self.tk.call(cmd)
        except tk.TclError:
            result = ''

        # Генерируем событие, если что-то было добавлено или удалено
        if command in ('insert', 'delete', 'replace'):
            self.event_generate('<<Change>>', when='tail')

        return result
