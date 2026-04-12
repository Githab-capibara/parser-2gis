"""Экран выбора категорий для парсинга на Textual."""

from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Input, Static

from ..protocols import ITuiApp


class CategorySelectorScreen(Screen):
    """Экран выбора категорий."""

    app: ITuiApp

    BINDINGS: ClassVar[list[Binding]] = [
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

    /* Заголовок — #73: идентичен в city_selector, parsing_screen, settings, other_screens */
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
        self._categories: list[dict[str, Any]] = []
        self._filtered_categories: list[dict[str, Any]] = []
        self._selected_indices: set[int] = set()
        self._checkboxes: list[Checkbox] = []
        self._id_to_index: dict[str, int] = {}  # Маппинг ID категории -> индекс в _categories
        self._population_counter: int = 0  # Счетчик для генерации уникальных ID

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

            # Список категорий (заполняется динамически в _populate_categories)
            with ScrollableContainer(id="category-list", classes="category-list-container"):
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
        categories_from_app = self.app.get_categories()
        self._categories = [cat.copy() for cat in categories_from_app]
        self._filtered_categories = self._categories.copy()

        # Создать маппинг: индекс в оригинальном списке -> категория
        # Каждая категория получает уникальный индекс независимо от rubric_code
        for i, cat in enumerate(self._categories):
            # Сохраняем оригинальный индекс в самой категории для последующего использования
            cat["original_index"] = i
            self._id_to_index[str(i)] = i

        # Восстановить ранее выбранные категории
        selected_names = set(self.app.selected_categories)
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
        # Очищаем контейнер полностью и сбрасываем ссылки на чекбоксы
        container = self.query_one("#category-list", ScrollableContainer)

        # Удаляем все дочерние виджеты из контейнера
        # Используем remove_children() для очистки контейнера
        container.remove_children()
        self._checkboxes.clear()

        # Создать новые Checkbox виджеты БЕЗ ID - это предотвращает DuplicateIds
        # Для идентификации будем использовать атрибуты и позицию в списке
        for _idx, cat in enumerate(self._filtered_categories):
            cat_name = cat.get("name", "Неизвестно")

            # Получить оригинальный индекс из категории (гарантирует уникальность)
            original_index = cat.get("original_index")
            if original_index is None:
                # Это не должно произойти, если _load_categories отработал корректно
                msg = f"Категория '{cat_name}' не имеет original_index"
                raise RuntimeError(msg)

            is_selected = original_index in self._selected_indices

            # НЕ используем ID - это предотвращает ошибку DuplicateIds
            # Сохраняем original_index как атрибут виджета
            checkbox = Checkbox(f"{cat_name}", value=is_selected)
            checkbox.original_index = original_index
            self._checkboxes.append(checkbox)

        # Смонтировать все виджеты за один раз
        if self._checkboxes:
            container.mount_all(self._checkboxes)

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
        # Получить оригинальный индекс из атрибута виджета
        original_index = getattr(event.checkbox, "original_index", None)
        if original_index is not None and event.value:
            self._selected_indices.add(original_index)
        elif original_index is not None:
            self._selected_indices.discard(original_index)

            self._update_counter()

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
            # Проверка что города выбраны перед переходом к парсингу
            selected_cities = self.app.selected_cities
            if not selected_cities:
                # Показать уведомление об ошибке
                self.app.notify("❌ Сначала выберите города в меню '📁 Выбрать города'", timeout=5)
                # Записать в лог
                self.app.notify_user("Попытка запуска без выбранных городов", level="error")
                return

            # Сохранить выбранные категории
            selected_names = [
                self._categories[i].get("name", "") for i in sorted(self._selected_indices)
            ]
            self.app.selected_categories = selected_names
            # Используем switch_screen для замены текущего экрана вместо push_screen
            # Это предотвращает накопление экранов в стеке
            self.app.switch_screen("parsing")

        elif button_id == "back":
            self.app.pop_screen()

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
