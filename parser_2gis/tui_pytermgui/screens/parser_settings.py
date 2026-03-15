"""
Экран настроек парсера.

Поддерживает навигацию с клавиатуры:
- Tab/Shift+Tab - переключение между полями
- Enter - активация checkbox/кнопки
- Esc - возврат назад
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

from ..widgets import Checkbox, NavigableContainer, ButtonWidget

if TYPE_CHECKING:
    from .app import TUIApp


class ParserSettingsScreen:
    """
    Экран настроек парсера.

    Предоставляет форму для настройки всех параметров парсера с поддержкой навигации.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана настроек парсера.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._config = app.get_config()
        self._parser_config = self._config.parser

        # Поля формы
        self._fields: dict[str, ptg.InputField | Checkbox] = {}
        # Контейнер для навигации
        self._form_container: NavigableContainer | None = None
        self._button_container: NavigableContainer | None = None

    def create_window(self) -> ptg.Window:
        """
        Создать окно настроек парсера.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Настройки парсера[/]",
            justify="center",
        )

        # Основной контейнер формы с навигацией
        self._form_container = NavigableContainer(
            box="EMPTY",
        )
        self._form_container.set_app(self._app)

        # Поле: Max records
        self._fields["max_records"] = ptg.InputField(
            label="Макс. записей:",
            value=str(self._parser_config.max_records),
            validators=[self._validate_positive_int],
        )
        self._form_container.add_widget(self._fields["max_records"])

        # Поле: Delay between clicks
        self._fields["delay_between_clicks"] = ptg.InputField(
            label="Задержка между кликами (мс):",
            value=str(self._parser_config.delay_between_clicks),
            validators=[self._validate_non_negative_int],
        )
        self._form_container.add_widget(self._fields["delay_between_clicks"])

        # Поле: Skip 404
        self._fields["skip_404_response"] = Checkbox(
            label="Пропускать 404 ответы",
            value=self._parser_config.skip_404_response,
        )
        self._form_container.add_widget(self._fields["skip_404_response"])

        # Поле: Use GC
        self._fields["use_gc"] = Checkbox(
            label="Использовать сборщик мусора",
            value=self._parser_config.use_gc,
        )
        self._form_container.add_widget(self._fields["use_gc"])

        # Поле: GC pages interval
        self._fields["gc_pages_interval"] = ptg.InputField(
            label="Интервал GC (страниц):",
            value=str(self._parser_config.gc_pages_interval),
            validators=[self._validate_positive_int],
        )
        self._form_container.add_widget(self._fields["gc_pages_interval"])

        # Поле: Stop on first 404
        self._fields["stop_on_first_404"] = Checkbox(
            label="Останавливать при первом 404",
            value=self._parser_config.stop_on_first_404,
        )
        self._form_container.add_widget(self._fields["stop_on_first_404"])

        # Поле: Max consecutive empty pages
        self._fields["max_consecutive_empty_pages"] = ptg.InputField(
            label="Макс. пустых страниц подряд:",
            value=str(self._parser_config.max_consecutive_empty_pages),
            validators=[self._validate_positive_int],
        )
        self._form_container.add_widget(self._fields["max_consecutive_empty_pages"])

        # Поле: Max retries
        self._fields["max_retries"] = ptg.InputField(
            label="Макс. попыток retry:",
            value=str(self._parser_config.max_retries),
            validators=[self._validate_positive_int],
        )
        self._form_container.add_widget(self._fields["max_retries"])

        # Поле: Retry on network errors
        self._fields["retry_on_network_errors"] = Checkbox(
            label="Retry при сетевых ошибках",
            value=self._parser_config.retry_on_network_errors,
        )
        self._form_container.add_widget(self._fields["retry_on_network_errors"])

        # Поле: Retry delay base
        self._fields["retry_delay_base"] = ptg.InputField(
            label="Базовая задержка retry (сек):",
            value=str(self._parser_config.retry_delay_base),
            validators=[self._validate_positive_int],
        )
        self._form_container.add_widget(self._fields["retry_delay_base"])

        # Поле: Memory threshold
        self._fields["memory_threshold"] = ptg.InputField(
            label="Порог памяти для очистки (МБ):",
            value=str(self._parser_config.memory_threshold),
            validators=[self._validate_positive_int],
        )
        self._form_container.add_widget(self._fields["memory_threshold"])

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
            ptg.Label("[dim]Настройте параметры парсера:[/]"),
            "",
            ptg.Label("[bold]Основные настройки:[/]"),
            "",
            self._form_container,
            "",
            self._button_container,
            width=70,
            box="DOUBLE",
            title="[bold green]Настройки парсера[/]",
        )

        # Установить фокус на первый элемент
        self._form_container.focus_first()

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

    def _validate_non_negative_int(self, value: str) -> tuple[bool, str]:
        """
        Проверить, что значение - неотрицательное целое число.

        Args:
            value: Значение для проверки

        Returns:
            Кортеж (успешно, сообщение об ошибке)
        """
        try:
            num = int(value)
            if num < 0:
                return False, "Введите неотрицательное число"
            return True, ""
        except ValueError:
            return False, "Введите целое число"

    def _save(self, *args) -> None:
        """Сохранить настройки."""
        # Получить значения из полей
        max_records = int(self._fields["max_records"].value)  # type: ignore
        delay_between_clicks = int(self._fields["delay_between_clicks"].value)  # type: ignore
        skip_404 = self._fields["skip_404_response"].value  # type: ignore
        use_gc = self._fields["use_gc"].value  # type: ignore
        gc_interval = int(self._fields["gc_pages_interval"].value)  # type: ignore
        stop_on_404 = self._fields["stop_on_first_404"].value  # type: ignore
        max_empty = int(self._fields["max_consecutive_empty_pages"].value)  # type: ignore
        max_retries = int(self._fields["max_retries"].value)  # type: ignore
        retry_on_errors = self._fields["retry_on_network_errors"].value  # type: ignore
        retry_delay = int(self._fields["retry_delay_base"].value)  # type: ignore
        memory_threshold = int(self._fields["memory_threshold"].value)  # type: ignore

        # Обновить конфигурацию
        self._parser_config.max_records = max_records
        self._parser_config.delay_between_clicks = delay_between_clicks
        self._parser_config.skip_404_response = skip_404
        self._parser_config.use_gc = use_gc
        self._parser_config.gc_pages_interval = gc_interval
        self._parser_config.stop_on_first_404 = stop_on_404
        self._parser_config.max_consecutive_empty_pages = max_empty
        self._parser_config.max_retries = max_retries
        self._parser_config.retry_on_network_errors = retry_on_errors
        self._parser_config.retry_delay_base = retry_delay
        self._parser_config.memory_threshold = memory_threshold

        # Сохранить конфигурацию
        self._app.save_config()

        # Показать сообщение об успехе
        self._show_message("Настройки сохранены!", "success")

    def _reset(self, *args) -> None:
        """Сбросить настройки к значениям по умолчанию."""
        from ...parser.options import ParserOptions

        default_options = ParserOptions()

        # Обновить поля Checkbox (можно использовать .value = )
        self._fields["skip_404_response"].value = default_options.skip_404_response  # type: ignore
        self._fields["use_gc"].value = default_options.use_gc  # type: ignore
        self._fields["stop_on_first_404"].value = default_options.stop_on_first_404  # type: ignore
        self._fields["retry_on_network_errors"].value = default_options.retry_on_network_errors  # type: ignore

        # Обновить поля InputField (нужно использовать delete_back() + insert_text())
        self._set_input_field_value(
            self._fields["max_records"], str(default_options.max_records)
        )
        self._set_input_field_value(
            self._fields["delay_between_clicks"], str(default_options.delay_between_clicks)
        )
        self._set_input_field_value(
            self._fields["gc_pages_interval"], str(default_options.gc_pages_interval)
        )
        max_empty_pages = default_options.max_consecutive_empty_pages
        self._set_input_field_value(
            self._fields["max_consecutive_empty_pages"], str(max_empty_pages)
        )
        self._set_input_field_value(
            self._fields["max_retries"], str(default_options.max_retries)
        )
        self._set_input_field_value(
            self._fields["retry_delay_base"], str(default_options.retry_delay_base)
        )
        self._set_input_field_value(
            self._fields["memory_threshold"], str(default_options.memory_threshold)
        )

        # Обновить конфигурацию
        self._parser_config.max_records = default_options.max_records
        self._parser_config.delay_between_clicks = default_options.delay_between_clicks
        self._parser_config.skip_404_response = default_options.skip_404_response
        self._parser_config.use_gc = default_options.use_gc
        self._parser_config.gc_pages_interval = default_options.gc_pages_interval
        self._parser_config.stop_on_first_404 = default_options.stop_on_first_404
        self._parser_config.max_consecutive_empty_pages = default_options.max_consecutive_empty_pages
        self._parser_config.max_retries = default_options.max_retries
        self._parser_config.retry_on_network_errors = default_options.retry_on_network_errors
        self._parser_config.retry_delay_base = default_options.retry_delay_base
        self._parser_config.memory_threshold = default_options.memory_threshold

    def _go_back(self, *args) -> None:
        """Вернуться назад."""
        self._app.go_back()

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

    def _show_message(self, message: str, level: str = "info") -> None:
        """
        Показать сообщение пользователю.

        Args:
            message: Текст сообщения
            level: Уровень (info, success, warning, error)
        """
        # TODO: Реализовать всплывающее сообщение
        pass
