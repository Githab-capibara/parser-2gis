"""
Экран выбора городов для парсинга на Textual.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Static


class CitySelectorScreen(Screen):
    """Экран выбора городов."""

    BINDINGS = [
        Binding("escape", "go_back", "Назад"),
        Binding("a", "select_all", "Выбрать все"),
        Binding("d", "deselect_all", "Снять все"),
    ]

    CSS = """
    /* Центрирование экрана выбора городов */
    CitySelectorScreen {
        align: center middle;
    }

    /* Главный контейнер */
    #city-selector-container {
        width: 100%;
        max-width: 90;
        min-width: 60;
        height: 80%;
        background: $surface-darken-2;
        border: solid $primary;
        padding: 1 2;
        align: center middle;
    }

    /* Заголовок */
    .header {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    /* Панель поиска */
    .search-panel {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Поле поиска */
    .search-input {
        width: 100%;
    }

    /* Панель счётчика */
    .counter-panel {
        width: 100%;
        height: 3;
        content-align: left middle;
        margin: 1 0;
        background: $surface-darken-3;
    }

    /* Контейнер списка городов */
    .city-list-container {
        width: 100%;
        height: 1fr;
        border: solid $secondary;
    }

    /* Ряд кнопок */
    .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    /* Кнопки в ряду */
    .button-row Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def __init__(self) -> None:
        """Инициализация экрана."""
        super().__init__()
        self._cities: list[dict] = []
        self._filtered_cities: list[dict] = []
        self._selected_indices: set[int] = set()
        self._checkboxes: list[Checkbox] = []

    def compose(self) -> ComposeResult:
        """Создать интерфейс."""
        with Container(id="city-selector-container"):
            # Заголовок
            yield Static("🏙️ Выбор городов", classes="header")

            # Поиск
            with Container(classes="search-panel"):
                yield Input(
                    placeholder="🔍 Введите название города...",
                    id="city-search",
                    classes="search-input",
                )

            # Счётчик
            yield Static("Выбрано: 0 из 0", id="city-counter", classes="counter-panel")

            # Список городов
            with ScrollableContainer(id="city-list", classes="city-list-container"):
                # Города будут добавлены динамически
                pass

            # Кнопки
            with Horizontal(classes="button-row"):
                yield Button("✅ Выбрать все", id="select-all", variant="success")
                yield Button("❌ Снять все", id="deselect-all", variant="error")
                yield Button("➡️ Далее", id="next", variant="primary")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_mount(self) -> None:
        """Загрузка городов."""
        self._load_cities()
        self._populate_cities()
        self._update_counter()

        # Фокус на поле поиска
        search_input = self.query_one("#city-search", Input)
        search_input.focus()

    def _load_cities(self) -> None:
        """Загрузить список городов."""
        self._cities = self.app.get_cities()  # type: ignore
        self._filtered_cities = self._cities.copy()

        # Восстановить ранее выбранные города
        selected_names = set(self.app.selected_cities)  # type: ignore
        for i, city in enumerate(self._cities):
            if city.get("name") in selected_names:
                self._selected_indices.add(i)

    def _populate_cities(self) -> None:
        """Заполнить список городов."""
        container = self.query_one("#city-list", ScrollableContainer)
        container.remove_children()
        self._checkboxes.clear()

        for i, city in enumerate(self._filtered_cities):
            city_name = city.get("name", "Неизвестно")
            country = city.get("country_code", "").upper()

            is_selected = i in self._selected_indices

            checkbox = Checkbox(
                f"{city_name} ({country})",
                value=is_selected,
                id=f"city-{i}",
            )
            self._checkboxes.append(checkbox)
            container.mount(checkbox)

    def _update_counter(self) -> None:
        """Обновить счётчик выбранных городов."""
        selected_count = len(self._selected_indices)
        total_count = len(self._cities)

        counter = self.query_one("#city-counter", Static)
        counter.update(f"Выбрано: {selected_count} из {total_count}")

        # Обновить кнопку "Далее"
        next_button = self.query_one("#next", Button)
        if selected_count > 0:
            next_button.label = f"➡️ Далее ({selected_count})"
            next_button.disabled = False
        else:
            next_button.label = "➡️ Далее (0)"
            next_button.disabled = True

    def on_input_changed(self, event: Input.Changed) -> None:
        """Фильтрация городов."""
        if event.input.id == "city-search":
            query = event.value.lower().strip()

            if not query:
                self._filtered_cities = self._cities.copy()
            else:
                self._filtered_cities = [
                    city
                    for city in self._cities
                    if query in city.get("name", "").lower()
                ]

            self._populate_cities()
            self._update_counter()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Изменение выбора города."""
        checkbox_id = event.checkbox.id
        if checkbox_id and checkbox_id.startswith("city-"):
            try:
                index = int(checkbox_id.split("-")[1])
                original_city = self._filtered_cities[index]
                original_index = self._cities.index(original_city)

                if event.value:
                    self._selected_indices.add(original_index)
                else:
                    self._selected_indices.discard(original_index)

                self._update_counter()
            except (ValueError, IndexError):
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработка кнопок."""
        button_id = event.button.id

        if button_id == "select-all":
            for i in range(len(self._filtered_cities)):
                original_city = self._filtered_cities[i]
                original_index = self._cities.index(original_city)
                self._selected_indices.add(original_index)

            for checkbox in self._checkboxes:
                checkbox.value = True
            self._update_counter()

        elif button_id == "deselect-all":
            self._selected_indices.clear()

            for checkbox in self._checkboxes:
                checkbox.value = False
            self._update_counter()

        elif button_id == "next":
            # Сохранить выбранные города
            selected_names = [
                self._cities[i].get("name", "") for i in sorted(self._selected_indices)
            ]
            self.app.selected_cities = selected_names  # type: ignore
            self.app.push_screen("category_selector")  # type: ignore

        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_select_all(self) -> None:
        """Выбрать все города."""
        for checkbox in self._checkboxes:
            checkbox.value = True

    def action_deselect_all(self) -> None:
        """Снять все города."""
        for checkbox in self._checkboxes:
            checkbox.value = False
