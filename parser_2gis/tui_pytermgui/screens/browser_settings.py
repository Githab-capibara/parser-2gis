"""
Экран настроек браузера.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

from ..widgets import Checkbox

if TYPE_CHECKING:
    from .app import TUIApp


class BrowserSettingsScreen:
    """
    Экран настроек браузера Chrome.

    Предоставляет форму для настройки всех параметров Chrome.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана настроек браузера.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._config = app.get_config()
        self._chrome_config = self._config.chrome

        # Поля формы
        self._fields: dict[str, ptg.InputField | Checkbox] = {}

    def create_window(self) -> ptg.Window:
        """
        Создать окно настроек браузера.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Настройки браузера Chrome[/bold cyan]",
            justify="center",
        )

        # Поле: Headless
        self._fields["headless"] = Checkbox(
            label="Headless (фоновый режим)",
            value=self._chrome_config.headless,
        )

        # Поле: Disable images
        self._fields["disable_images"] = Checkbox(
            label="Отключить изображения",
            value=self._chrome_config.disable_images,
        )

        # Поле: Start maximized
        self._fields["start_maximized"] = Checkbox(
            label="Запускать развёрнутым",
            value=self._chrome_config.start_maximized,
        )

        # Поле: Silent browser
        self._fields["silent_browser"] = Checkbox(
            label="Тихий режим (без отладочной информации)",
            value=self._chrome_config.silent_browser,
        )

        # Поле: Memory limit
        self._fields["memory_limit"] = ptg.InputField(
            label="Лимит памяти (МБ):",
            value=str(self._chrome_config.memory_limit),
            validators=[self._validate_positive_int],
        )

        # Поле: Binary path
        self._fields["binary_path"] = ptg.InputField(
            label="Путь к Chrome (опционально):",
            value=str(self._chrome_config.binary_path or ""),
            placeholder="/usr/bin/google-chrome",
        )

        # Кнопки управления
        button_save = ptg.Button(
            "Сохранить",
            onclick=self._save,
            style="secondary",
        )

        button_reset = ptg.Button(
            "Сбросить",
            onclick=self._reset,
            style="primary",
        )

        button_back = ptg.Button(
            "Назад",
            onclick=self._go_back,
            style="primary",
        )

        # Создание окна
        window = ptg.Window(
            "",
            header,
            "",
            ptg.Label("[dim]Настройте параметры браузера Chrome:[/dim]"),
            "",
            ptg.Container(
                ptg.Label("[bold]Основные настройки:[/bold]"),
                box="EMPTY_VERTICAL",
            ),
            "",
            self._fields["headless"],
            self._fields["disable_images"],
            self._fields["start_maximized"],
            self._fields["silent_browser"],
            "",
            ptg.Container(
                ptg.Label("[bold]Расширенные настройки:[/bold]"),
                box="EMPTY_VERTICAL",
            ),
            "",
            self._fields["memory_limit"],
            self._fields["binary_path"],
            "",
            ptg.Container(
                button_save,
                button_reset,
                button_back,
                box="EMPTY_HORIZONTAL",
            ),
            width=70,
            box="DOUBLE",
        ).set_title("[bold green]Настройки браузера[/bold green]")

        return window.center()

    def _validate_positive_int(self, value: str) -> tuple[bool, str]:
        """
        Проверить, что значение - положительное целое число.

        Args:
            value: Значение для проверки

        Returns:
            Кортеж (успешно, сообщение об ошибке)
        """
        try:
            num = int(value)
            if num <= 0:
                return False, "Введите положительное число"
            return True, ""
        except ValueError:
            return False, "Введите целое число"

    def _save(self, *args) -> None:
        """Сохранить настройки."""
        # Получить значения из полей
        headless = self._fields["headless"].value  # type: ignore
        disable_images = self._fields["disable_images"].value  # type: ignore
        start_maximized = self._fields["start_maximized"].value  # type: ignore
        silent_browser = self._fields["silent_browser"].value  # type: ignore

        memory_limit_str = self._fields["memory_limit"].value  # type: ignore
        binary_path_str = self._fields["binary_path"].value  # type: ignore

        try:
            memory_limit = int(memory_limit_str)
            if memory_limit <= 0:
                raise ValueError("Лимит памяти должен быть положительным")
        except ValueError:
            # Показать ошибку
            return

        # Обновить конфигурацию
        self._chrome_config.headless = headless
        self._chrome_config.disable_images = disable_images
        self._chrome_config.start_maximized = start_maximized
        self._chrome_config.silent_browser = silent_browser
        self._chrome_config.memory_limit = memory_limit

        if binary_path_str.strip():
            from pathlib import Path
            self._chrome_config.binary_path = Path(binary_path_str)
        else:
            self._chrome_config.binary_path = None

        # Сохранить конфигурацию
        self._app.save_config()

        # Показать сообщение об успехе
        self._show_message("Настройки сохранены!", "success")

    def _reset(self, *args) -> None:
        """Сбросить настройки к значениям по умолчанию."""
        from ...chrome.options import ChromeOptions

        default_options = ChromeOptions()

        # Обновить поля
        self._fields["headless"].value = default_options.headless  # type: ignore
        self._fields["disable_images"].value = default_options.disable_images  # type: ignore
        self._fields["start_maximized"].value = default_options.start_maximized  # type: ignore
        self._fields["silent_browser"].value = default_options.silent_browser  # type: ignore
        self._fields["memory_limit"].value = str(default_options.memory_limit)  # type: ignore
        self._fields["binary_path"].value = ""  # type: ignore

        # Обновить конфигурацию
        self._chrome_config.headless = default_options.headless
        self._chrome_config.disable_images = default_options.disable_images
        self._chrome_config.start_maximized = default_options.start_maximized
        self._chrome_config.silent_browser = default_options.silent_browser
        self._chrome_config.memory_limit = default_options.memory_limit
        self._chrome_config.binary_path = None

    def _go_back(self, *args) -> None:
        """Вернуться назад."""
        self._app.go_back()

    def _show_message(self, message: str, level: str = "info") -> None:
        """
        Показать сообщение пользователю.

        Args:
            message: Текст сообщения
            level: Уровень (info, success, warning, error)
        """
        # TODO: Реализовать всплывающее сообщение
        pass
