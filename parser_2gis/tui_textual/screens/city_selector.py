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
        """Загрузить список городов из приложения.

        Получает города через метод app.get_cities() и восстанавливает
        ранее выбранные пользователем города из app.selected_cities.

        Raises:
            AttributeError: Если метод get_cities недоступен в приложении.
        """
        self._cities = self.app.get_cities()  # type: ignore
        self._filtered_cities = self._cities.copy()

        # Восстановить ранее выбранные города
        selected_names = set(self.app.selected_cities)  # type: ignore
        for i, city in enumerate(self._cities):
            if city.get("name") in selected_names:
                self._selected_indices.add(i)

    def _populate_cities(self) -> None:
        """Заполнить интерфейс списком городов.

        Очищает контейнер списка и создаёт Checkbox виджеты для каждого
        города из отфильтрованного списка с указанием кода страны.
        Использует подход без ID для виджетов Checkbox, чтобы избежать
        ошибки DuplicateIds при фильтрации.
        """
        container = self.query_one("#city-list", ScrollableContainer)

        # Удаляем все дочерние виджеты из контейнера
        container.remove_children()
        self._checkboxes.clear()

        # Создать новые Checkbox виджеты БЕЗ ID - это предотвращает DuplicateIds
        # Для идентификации используем атрибут city_code
        for i, city in enumerate(self._filtered_cities):
            city_name = city.get("name", "Неизвестно")
            country = city.get("country_code", "").upper()
            city_code = city.get("code", str(i))

            is_selected = i in self._selected_indices

            # НЕ используем ID - это предотвращает ошибку DuplicateIds
            # Сохраняем city_code как атрибут виджета
            checkbox = Checkbox(f"{city_name} ({country})", value=is_selected)
            checkbox.city_code = city_code  # type: ignore
            self._checkboxes.append(checkbox)

        # Смонтировать все виджеты за один раз
        if self._checkboxes:
            container.mount_all(self._checkboxes)

    def _update_counter(self) -> None:
        """Обновить счётчик выбранных городов и состояние кнопки "Далее".

        Вычисляет количество выбранных городов и обновляет текст счётчика.
        Кнопка "Далее" становится активной только если выбран хотя бы один город.
        """
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
        """Обработать изменение текста в поле поиска.

        Фильтрует список городов по введённому запросу и обновляет интерфейс.

        Args:
            event: Событие изменения текста в Input виджете.
        """
        if event.input.id == "city-search":
            query = event.value.lower().strip()

            if not query:
                self._filtered_cities = self._cities.copy()
            else:
                self._filtered_cities = [
                    city for city in self._cities if query in city.get("name", "").lower()
                ]

            self._populate_cities()
            self._update_counter()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Обработать изменение состояния Checkbox города.

        Добавляет или удаляет индекс города из множества выбранных.
        Корректно обрабатывает映射 между отфильтрованным и полным списком.

        Args:
            event: Событие изменения состояния Checkbox.
        """
        # Получить city_code из атрибута виджета
        city_code = getattr(event.checkbox, "city_code", None)
        if city_code is not None:
            # Найти город по коду в отфильтрованном списке
            try:
                filtered_city = next(
                    city for city in self._filtered_cities if city.get("code") == city_code
                )
                # Найти оригинальный индекс города в полном списке
                original_index = self._cities.index(filtered_city)

                if event.value:
                    self._selected_indices.add(original_index)
                else:
                    self._selected_indices.discard(original_index)

                self._update_counter()
            except StopIteration:
                # Город не найден в отфильтрованном списке
                app_logger.debug("Город не найден в отфильтрованном списке")
            except ValueError:
                # Город не найден в полном списке
                app_logger.debug("Город не найден в полном списке")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки на экране.

        Обрабатывает кнопки: "Выбрать все", "Снять все", "Далее", "Назад".

        Args:
            event: Событие нажатия кнопки.
        """
        button_id = event.button.id

        if button_id == "select-all":
            # Выбрать все города из отфильтрованного списка
            for city in self._filtered_cities:
                original_index = self._cities.index(city)
                self._selected_indices.add(original_index)

            # Обновить состояние Checkbox
            for checkbox in self._checkboxes:
                checkbox.value = True
            self._update_counter()

        elif button_id == "deselect-all":
            # Снять выбор со всех городов
            self._selected_indices.clear()

            # Обновить состояние Checkbox
            for checkbox in self._checkboxes:
                checkbox.value = False
            self._update_counter()

        elif button_id == "next":
            # Сохранить выбранные города
            selected_names = [
                self._cities[i].get("name", "") for i in sorted(self._selected_indices)
            ]
            self.app.selected_cities = selected_names  # type: ignore
            # Используем switch_screen для замены текущего экрана вместо push_screen
            # Это предотвращает накопление экранов в стеке
            self.app.switch_screen("category_selector")  # type: ignore

        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_select_all(self) -> None:
        """Выбрать все отображённые города.

        Устанавливает значение всех Checkbox в True.
        """
        for checkbox in self._checkboxes:
            checkbox.value = True

    def action_deselect_all(self) -> None:
        """Снять выбор со всех городов.

        Устанавливает значение всех Checkbox в False.
        """
        for checkbox in self._checkboxes:
            checkbox.value = False
