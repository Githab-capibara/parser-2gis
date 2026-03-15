"""
Экран настроек вывода (CSV/XLSX/JSON).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

from ..widgets import Checkbox

if TYPE_CHECKING:
    from .app import TUIApp


class OutputSettingsScreen:
    """
    Экран настроек вывода.

    Предоставляет форму для настройки параметров вывода данных.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана настроек вывода.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._config = app.get_config()
        self._writer_config = self._config.writer
        self._csv_config = self._config.writer.csv

        # Поля формы
        self._fields: dict[str, ptg.InputField | Checkbox | ptg.SelectMenu] = {}

    def create_window(self) -> ptg.Window:
        """
        Создать окно настроек вывода.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Настройки вывода[/bold cyan]",
            justify="center",
        )

        # Поле: Encoding
        encodings = "utf-8-sig, utf-8, cp1251, cp1252, koi8-r, iso-8859-1"
        self._fields["encoding"] = ptg.InputField(
            label=f"Кодировка ({encodings}):",
            value=self._writer_config.encoding,
            placeholder="utf-8-sig",
        )

        # Поле: Verbose
        self._fields["verbose"] = Checkbox(
            label="Отображать наименования во время парсинга",
            value=self._writer_config.verbose,
        )

        # Поле: Add rubrics
        self._fields["add_rubrics"] = Checkbox(
            label="Добавлять колонку 'Рубрики'",
            value=self._csv_config.add_rubrics,
        )

        # Поле: Add comments
        self._fields["add_comments"] = Checkbox(
            label="Добавлять комментарии к ячейкам",
            value=self._csv_config.add_comments,
        )

        # Поле: Columns per entity
        self._fields["columns_per_entity"] = ptg.InputField(
            label="Колонок на сущность (1-5):",
            value=str(self._csv_config.columns_per_entity),
            validators=[self._validate_columns_per_entity],
        )

        # Поле: Remove empty columns
        self._fields["remove_empty_columns"] = Checkbox(
            label="Удалять пустые колонки",
            value=self._csv_config.remove_empty_columns,
        )

        # Поле: Remove duplicates
        self._fields["remove_duplicates"] = Checkbox(
            label="Удалять дубликаты",
            value=self._csv_config.remove_duplicates,
        )

        # Поле: Join char
        self._fields["join_char"] = ptg.InputField(
            label="Разделитель для списков:",
            value=self._csv_config.join_char,
            placeholder="; ",
        )

        # Кнопки управления - используем синтаксис [label, callback]
        button_save = ["Сохранить", self._save]
        button_reset = ["Сбросить", self._reset]
        button_back = ["Назад", self._go_back]

        # Создание окна
        window = ptg.Window(
            "",
            header,
            "",
            ptg.Label("[dim]Настройте параметры вывода данных:[/dim]"),
            "",
            ptg.Container(
                ptg.Label("[bold]Формат и кодировка:[/bold]"),
                box="EMPTY_VERTICAL",
            ),
            "",
            self._fields["encoding"],
            self._fields["verbose"],
            "",
            ptg.Container(
                ptg.Label("[bold]CSV настройки:[/bold]"),
                box="EMPTY_VERTICAL",
            ),
            "",
            self._fields["add_rubrics"],
            self._fields["add_comments"],
            self._fields["columns_per_entity"],
            self._fields["join_char"],
            "",
            ptg.Container(
                ptg.Label("[bold]Очистка данных:[/bold]"),
                box="EMPTY_VERTICAL",
            ),
            "",
            self._fields["remove_empty_columns"],
            self._fields["remove_duplicates"],
            "",
            ptg.Container(
                button_save,
                button_reset,
                button_back,
                box="EMPTY_HORIZONTAL",
            ),
            width=70,
            box="DOUBLE",
        ).set_title("[bold green]Настройки вывода[/bold green]")

        return window.center()

    def _validate_columns_per_entity(self, value: str) -> tuple[bool, str]:
        """
        Проверить, что значение в диапазоне 1-5.

        Args:
            value: Значение для проверки

        Returns:
            Кортеж (успешно, сообщение об ошибке)
        """
        try:
            num = int(value)
            if num < 1 or num > 5:
                return False, "Введите число от 1 до 5"
            return True, ""
        except ValueError:
            return False, "Введите целое число"

    def _save(self, *args) -> None:
        """Сохранить настройки."""
        # Получить значения из полей
        encoding = self._fields["encoding"].value  # type: ignore
        verbose = self._fields["verbose"].value  # type: ignore
        add_rubrics = self._fields["add_rubrics"].value  # type: ignore
        add_comments = self._fields["add_comments"].value  # type: ignore
        columns_per_entity = int(self._fields["columns_per_entity"].value)  # type: ignore
        remove_empty_columns = self._fields["remove_empty_columns"].value  # type: ignore
        remove_duplicates = self._fields["remove_duplicates"].value  # type: ignore
        join_char = self._fields["join_char"].value  # type: ignore

        # Обновить конфигурацию
        self._writer_config.encoding = encoding
        self._writer_config.verbose = verbose
        self._csv_config.add_rubrics = add_rubrics
        self._csv_config.add_comments = add_comments
        self._csv_config.columns_per_entity = columns_per_entity
        self._csv_config.remove_empty_columns = remove_empty_columns
        self._csv_config.remove_duplicates = remove_duplicates
        self._csv_config.join_char = join_char

        # Сохранить конфигурацию
        self._app.save_config()

        # Показать сообщение об успехе
        self._show_message("Настройки сохранены!", "success")

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

    def _reset(self, *args) -> None:
        """Сбросить настройки к значениям по умолчанию."""
        from ...writer.options import CSVOptions, WriterOptions

        default_writer = WriterOptions()
        default_csv = CSVOptions(columns_per_entity=3)

        # Обновить поля Checkbox (можно использовать .value = )
        self._fields["verbose"].value = default_writer.verbose  # type: ignore
        self._fields["add_rubrics"].value = default_csv.add_rubrics  # type: ignore
        self._fields["add_comments"].value = default_csv.add_comments  # type: ignore
        self._fields["remove_empty_columns"].value = default_csv.remove_empty_columns  # type: ignore
        self._fields["remove_duplicates"].value = default_csv.remove_duplicates  # type: ignore

        # Обновить поля InputField (нужно использовать delete_back() + insert_text())
        self._set_input_field_value(
            self._fields["encoding"], default_writer.encoding
        )
        self._set_input_field_value(
            self._fields["columns_per_entity"], str(default_csv.columns_per_entity)
        )
        self._set_input_field_value(self._fields["join_char"], default_csv.join_char)

        # Обновить конфигурацию
        self._writer_config.encoding = default_writer.encoding
        self._writer_config.verbose = default_writer.verbose
        self._csv_config.add_rubrics = default_csv.add_rubrics
        self._csv_config.add_comments = default_csv.add_comments
        self._csv_config.columns_per_entity = default_csv.columns_per_entity
        self._csv_config.remove_empty_columns = default_csv.remove_empty_columns
        self._csv_config.remove_duplicates = default_csv.remove_duplicates
        self._csv_config.join_char = default_csv.join_char

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
