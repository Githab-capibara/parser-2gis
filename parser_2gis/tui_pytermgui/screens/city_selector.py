"""
Экран выбора городов для парсинга.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytermgui as ptg

if TYPE_CHECKING:
    from .app import TUIApp


class CitySelectorScreen:
    """
    Экран выбора городов.

    Предоставляет поиск и множественный выбор городов.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана выбора городов.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._cities: list[dict[str, Any]] = []
        self._filtered_cities: list[dict[str, Any]] = []
        self._selected_indices: set[int] = set()
        self._search_field: ptg.InputField | None = None
        self._city_container: ptg.Container | None = None
        self._counter_label: ptg.Label | None = None

        self._load_cities()

    def _load_cities(self) -> None:
        """Загрузить список городов."""
        self._cities = self._app.get_cities()
        self._filtered_cities = self._cities.copy()

        # Восстановить ранее выбранные города
        selected_names = set(self._app.selected_cities)
        for i, city in enumerate(self._cities):
            if city.get("name") in selected_names:
                self._selected_indices.add(i)

    def create_window(self) -> ptg.Window:
        """
        Создать окно выбора городов.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Выбор городов[/bold cyan]",
            justify="center",
        )

        # Поле поиска
        self._search_field = ptg.InputField(
            placeholder="Поиск города...",
            on_change=self._filter_cities,
        )

        # Контейнер для городов (будет заполнен динамически)
        self._city_container = ptg.Container()
        self._populate_cities()

        # Счётчик выбранных городов
        selected_count = len(self._selected_indices)
        total_count = len(self._cities)
        self._counter_label = ptg.Label(
            f"[green]Выбрано: {selected_count}[/green] из {total_count}",
            justify="center",
        )

        # Кнопки управления
        button_select_all = ptg.Button(
            "Выбрать все",
            callback=self._select_all,
            style="primary",
        )

        button_deselect_all = ptg.Button(
            "Снять все",
            callback=self._deselect_all,
            style="primary",
        )

        button_back = ptg.Button(
            "Назад",
            callback=self._go_back,
            style="primary",
        )

        button_next = ptg.Button(
            "Далее",
            callback=self._next,
            style="secondary",
        )

        # Создание окна
        window = ptg.Window(
            "",
            header,
            "",
            ptg.Label("[dim]Введите название города для поиска:[/dim]"),
            self._search_field,
            "",
            ptg.Splitter(
                ptg.Label("[bold]Список городов:[/bold]"),
                self._counter_label,
            ),
            "",
            ptg.ScrollArea(
                self._city_container,
                height=15,
            ),
            "",
            ptg.BoxLayout(
                button_select_all,
                button_deselect_all,
                direction="horizontal",
            ),
            "",
            ptg.BoxLayout(
                button_back,
                button_next,
                direction="horizontal",
            ),
            width=80,
            box="DOUBLE",
        ).set_title("[bold green]Выбор городов для парсинга[/bold green]")

        return window.center()

    def _populate_cities(self) -> None:
        """Заполнить контейнер городами."""
        if not self._city_container:
            return

        self._city_container.widgets.clear()

        for i, city in enumerate(self._filtered_cities):
            city_name = city.get("name", "Неизвестно")
            country = city.get("country_code", "").upper()

            is_selected = i in self._selected_indices
            checkbox = ptg.Checkbox(
                label=f"{city_name} ({country})",
                value=is_selected,
                on_change=lambda checked, idx=i: self._toggle_city(idx, checked),
            )

            self._city_container.add_widget(checkbox)

    def _filter_cities(self, field: ptg.InputField) -> None:
        """
        Фильтровать города по поисковому запросу.

        Args:
            field: Поле ввода с запросом
        """
        query = field.value.lower().strip()

        if not query:
            self._filtered_cities = self._cities.copy()
        else:
            self._filtered_cities = [
                city for city in self._cities
                if query in city.get("name", "").lower()
            ]

        self._populate_cities()
        self._update_counter()

    def _toggle_city(self, index: int, checked: bool) -> None:
        """
        Переключить выбор города.

        Args:
            index: Индекс города в отфильтрованном списке
            checked: Состояние чекбокса
        """
        # Найти оригинальный индекс города
        original_city = self._filtered_cities[index]
        original_index = self._cities.index(original_city)

        if checked:
            self._selected_indices.add(original_index)
        else:
            self._selected_indices.discard(original_index)

        self._update_counter()

    def _select_all(self, *args) -> None:
        """Выбрать все города."""
        for i in range(len(self._filtered_cities)):
            original_city = self._filtered_cities[i]
            original_index = self._cities.index(original_city)
            self._selected_indices.add(original_index)

        self._populate_cities()
        self._update_counter()

    def _deselect_all(self, *args) -> None:
        """Снять все города."""
        self._selected_indices.clear()
        self._populate_cities()
        self._update_counter()

    def _update_counter(self) -> None:
        """Обновить счётчик выбранных городов."""
        if self._counter_label:
            selected_count = len(self._selected_indices)
            total_count = len(self._cities)
            self._counter_label.set_format(
                f"[green]Выбрано: {selected_count}[/green] из {total_count}"
            )

    def _go_back(self, *args) -> None:
        """Вернуться назад."""
        self._app.go_back()

    def _next(self, *args) -> None:
        """Перейти к следующему экрану."""
        # Сохранить выбранные города
        selected_names = [
            self._cities[i].get("name", "")
            for i in sorted(self._selected_indices)
        ]
        self._app.selected_cities = selected_names

        # Перейти к выбору категорий
        self._app._show_category_selector()
