"""
Экран выбора категорий для парсинга на Textual.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Static


class CategorySelectorScreen(Screen):
    """Экран выбора категорий."""

    BINDINGS = [
        Binding("escape", "go_back", "Назад"),
        Binding("a", "select_all", "Выбрать все"),
        Binding("d", "deselect_all", "Снять все"),
    ]

    CSS = """
    /* Центрирование экрана выбора категорий */
    CategorySelectorScreen {
        align: center middle;
    }

    /* Главный контейнер */
    #category-selector-container {
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

    /* Контейнер списка категорий */
    .category-list-container {
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
        self._categories: list[dict] = []
        self._filtered_categories: list[dict] = []
        self._selected_indices: set[int] = set()
        self._checkboxes: list[Checkbox] = []
        self._id_to_index: dict[str, int] = {}  # Маппинг ID категории -> индекс в _categories

    def compose(self) -> ComposeResult:
        """Создать интерфейс."""
        with Container(id="category-selector-container"):
            # Заголовок
            yield Static("📂 Выбор категорий", classes="header")

            # Поиск
            with Container(classes="search-panel"):
                yield Input(
                    placeholder="🔍 Введите название категории...",
                    id="category-search",
                    classes="search-input",
                )

            # Счётчик
            yield Static("Выбрано: 0 из 0", id="category-counter", classes="counter-panel")

            # Список категорий
            with ScrollableContainer(id="category-list", classes="category-list-container"):
                # Категории будут добавлены динамически
                pass

            # Кнопки
            with Horizontal(classes="button-row"):
                yield Button("✅ Выбрать все", id="select-all", variant="success")
                yield Button("❌ Снять все", id="deselect-all", variant="error")
                yield Button("➡️ Далее", id="next", variant="primary")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_mount(self) -> None:
        """Загрузка категорий."""
        self._load_categories()
        self._populate_categories()
        self._update_counter()

        # Фокус на поле поиска
        search_input = self.query_one("#category-search", Input)
        search_input.focus()

    def _load_categories(self) -> None:
        """Загрузить список категорий из приложения.

        Получает категории через метод app.get_categories() и восстанавливает
        ранее выбранные пользователем категории из app.selected_categories.

        Raises:
            AttributeError: Если метод get_categories недоступен в приложении.
        """
        # Получить категории из приложения и сделать глубокую копию
        # Это предотвращает мутацию глобальной константы CATEGORIES_93
        categories_from_app = self.app.get_categories()  # type: ignore
        self._categories = [cat.copy() for cat in categories_from_app]
        self._filtered_categories = self._categories.copy()

        # Создать маппинг: индекс в оригинальном списке -> категория
        # Каждая категория получает уникальный индекс независимо от rubric_code
        for i, cat in enumerate(self._categories):
            # Сохраняем оригинальный индекс в самой категории для последующего использования
            cat["original_index"] = i
            self._id_to_index[str(i)] = i

        # Восстановить ранее выбранные категории
        selected_names = set(self.app.selected_categories)  # type: ignore
        for i, cat in enumerate(self._categories):
            if cat.get("name") in selected_names:
                self._selected_indices.add(i)

    def _populate_categories(self) -> None:
        """Заполнить интерфейс списком категорий.

        Очищает контейнер списка и создаёт Checkbox виджеты для каждой
        категории из отфильтрованного списка.

        Raises:
            RuntimeError: Если категория не имеет original_index.
        """
        container = self.query_one("#category-list", ScrollableContainer)
        container.remove_children()
        self._checkboxes.clear()

        for cat in self._filtered_categories:
            cat_name = cat.get("name", "Неизвестно")

            # Получить оригинальный индекс из категории (гарантирует уникальность)
            original_index = cat.get("original_index")
            if original_index is None:
                # Это не должно произойти, если _load_categories отработал корректно
                msg = f"Категория '{cat_name}' не имеет original_index"
                raise RuntimeError(msg)

            is_selected = original_index in self._selected_indices

            # Используем оригинальный индекс для уникального ID
            checkbox = Checkbox(f"{cat_name}", value=is_selected, id=f"category-{original_index}")
            self._checkboxes.append(checkbox)
            container.mount(checkbox)

    def _update_counter(self) -> None:
        """Обновить счётчик выбранных категорий и состояние кнопки "Далее".

        Вычисляет количество выбранных категорий и обновляет текст счётчика.
        Кнопка "Далее" становится активной только если выбрана хотя бы одна категория.
        """
        selected_count = len(self._selected_indices)
        total_count = len(self._categories)

        counter = self.query_one("#category-counter", Static)
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

        Фильтрует список категорий по введённому запросу и обновляет интерфейс.

        Args:
            event: Событие изменения текста в Input виджете.
        """
        if event.input.id == "category-search":
            query = event.value.lower().strip()

            if not query:
                self._filtered_categories = self._categories.copy()
            else:
                self._filtered_categories = [
                    cat for cat in self._categories if query in cat.get("name", "").lower()
                ]

            self._populate_categories()
            self._update_counter()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Обработать изменение состояния Checkbox категории.

        Добавляет или удаляет индекс категории из множества выбранных.

        Args:
            event: Событие изменения состояния Checkbox.
        """
        checkbox_id = event.checkbox.id
        if checkbox_id and checkbox_id.startswith("category-"):
            # Извлекаем оригинальный индекс из ID (формат: "category-{index}")
            index_str = checkbox_id.split("-", 1)[1]
            try:
                index = int(index_str)
                if event.value:
                    self._selected_indices.add(index)
                else:
                    self._selected_indices.discard(index)

                self._update_counter()
            except ValueError:
                # Если индекс не удалось преобразовать, игнорируем
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки на экране.

        Обрабатывает кнопки: "Выбрать все", "Снять все", "Далее", "Назад".

        Args:
            event: Событие нажатия кнопки.
        """
        button_id = event.button.id

        if button_id == "select-all":
            # Выбрать все категории из отфильтрованного списка
            for cat in self._filtered_categories:
                # Получить оригинальный индекс из категории (гарантирует уникальность)
                original_index = cat.get("original_index")
                if original_index is not None:
                    self._selected_indices.add(original_index)

            for checkbox in self._checkboxes:
                checkbox.value = True
            self._update_counter()

        elif button_id == "deselect-all":
            # Снять все выбранные категории
            self._selected_indices.clear()

            for checkbox in self._checkboxes:
                checkbox.value = False
            self._update_counter()

        elif button_id == "next":
            # Сохранить выбранные категории
            selected_names = [
                self._categories[i].get("name", "") for i in sorted(self._selected_indices)
            ]
            self.app.selected_categories = selected_names  # type: ignore
            self.app.push_screen("parsing")  # type: ignore

        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_select_all(self) -> None:
        """Выбрать все отображённые категории.

        Устанавливает значение всех Checkbox в True.
        """
        for checkbox in self._checkboxes:
            checkbox.value = True

    def action_deselect_all(self) -> None:
        """Снять выбор со всех категорий.

        Устанавливает значение всех Checkbox в False.
        """
        for checkbox in self._checkboxes:
            checkbox.value = False
