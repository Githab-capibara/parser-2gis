"""
Экран настроек браузера.

Поддерживает навигацию с клавиатуры:
- Tab/Shift+Tab - переключение между полями
- Enter - активация checkbox/кнопки
- Esc - возврат назад
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytermgui as ptg

from ..widgets import Checkbox, NavigableContainer, ButtonWidget

if TYPE_CHECKING:
    from .app import TUIApp


class BrowserSettingsScreen:
    """
    Экран настроек браузера Chrome.

    Предоставляет форму для настройки всех параметров Chrome с поддержкой навигации.
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
        # Контейнер для навигации
        self._form_container: NavigableContainer | None = None
        self._button_container: NavigableContainer | None = None

    def create_window(self) -> ptg.Window:
        """
        Создать окно настроек браузера.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Настройки браузера Chrome[/]",
            justify="center",
        )

        # Основной контейнер формы с навигацией
        self._form_container = NavigableContainer(
            box="EMPTY",
        )
        self._form_container.set_app(self._app)

        # Поле: Headless
        self._fields["headless"] = Checkbox(
            label="Headless (фоновый режим)",
            value=self._chrome_config.headless,
        )
        self._form_container.add_widget(self._fields["headless"])

        # Поле: Disable images
        self._fields["disable_images"] = Checkbox(
            label="Отключить изображения",
            value=self._chrome_config.disable_images,
        )
        self._form_container.add_widget(self._fields["disable_images"])

        # Поле: Start maximized
        self._fields["start_maximized"] = Checkbox(
            label="Запускать развёрнутым",
            value=self._chrome_config.start_maximized,
        )
        self._form_container.add_widget(self._fields["start_maximized"])

        # Поле: Silent browser
        self._fields["silent_browser"] = Checkbox(
            label="Тихий режим (без отладочной информации)",
            value=self._chrome_config.silent_browser,
        )
        self._form_container.add_widget(self._fields["silent_browser"])

        # Поле: Memory limit
        self._fields["memory_limit"] = ptg.InputField(
            label="Лимит памяти (МБ):",
            value=str(self._chrome_config.memory_limit),
            validators=[self._validate_positive_int],
        )
        self._form_container.add_widget(self._fields["memory_limit"])

        # Поле: Binary path
        self._fields["binary_path"] = ptg.InputField(
            label="Путь к Chrome (опционально):",
            value=str(self._chrome_config.binary_path or ""),
            placeholder="/usr/bin/google-chrome",
        )
        self._form_container.add_widget(self._fields["binary_path"])

        # Кнопки управления в навигируемом контейнере
        self._button_container = NavigableContainer(
            box="EMPTY",
        )
        self._button_container.set_app(self._app)

        self._button_container.add_widget(ButtonWidget("Сохранить", self._save))
        self._button_container.add_widget(ButtonWidget("Сбросить", self._reset))
        self._button_container.add_widget(ButtonWidget("Назад", self._go_back))

        # Создание окна
        window = ptg.Window(
            "",
            header,
            "",
            ptg.Label("[dim]Настройте параметры браузера Chrome:[/]"),
            "",
            ptg.Label("[bold]Основные настройки:[/]"),
            "",
            self._form_container,
            "",
            self._button_container,
            width=70,
            box="DOUBLE",
            title="[bold green]Настройки браузера[/]",
        )

        # Установить фокус на первый элемент
        self._form_container.focus_first()

        return window.center()

    def _set_input_field_value(self, field: ptg.InputField, value: str) -> None:
        """
        Установить значение для InputField.

        Args:
            field: Поле для установки значения
            value: Новое значение
        """
        # Очищаем текущее значение
        for _ in range(len(field.value)):
            field.delete_back()
        # Вставляем новое значение
        field.insert_text(value)

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
        except ValueError as e:
            # Показать ошибку пользователю
            error_message = str(e) if str(e) else "Неверное значение для лимита памяти"
            self._show_message(error_message, "error")
            return

        # Обновить конфигурацию
        self._chrome_config.headless = headless
        self._chrome_config.disable_images = disable_images
        self._chrome_config.start_maximized = start_maximized
        self._chrome_config.silent_browser = silent_browser
        self._chrome_config.memory_limit = memory_limit

        if binary_path_str.strip():
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

        # Обновить поля Checkbox (можно использовать .value = )
        self._fields["headless"].value = default_options.headless  # type: ignore
        self._fields["disable_images"].value = default_options.disable_images  # type: ignore
        self._fields["start_maximized"].value = default_options.start_maximized  # type: ignore
        self._fields["silent_browser"].value = default_options.silent_browser  # type: ignore

        # Обновить поля InputField (нужно использовать delete_back() + insert_text())
        self._set_input_field_value(self._fields["memory_limit"], str(default_options.memory_limit))
        self._set_input_field_value(self._fields["binary_path"], "")

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
