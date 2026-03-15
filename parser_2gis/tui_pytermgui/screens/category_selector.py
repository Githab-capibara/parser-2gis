"""
Экран выбора категорий для парсинга.

Поддерживает навигацию с клавиатуры:
- Tab/Shift+Tab - переключение между элементами
- Enter - активация checkbox/кнопки
- Esc - возврат назад
- Фокус на InputField для поиска
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

from ..widgets import Checkbox, NavigableContainer, ButtonWidget, ScrollArea

if TYPE_CHECKING:
    from .app import TUIApp


class CategorySelectorScreen:
    """
    Экран выбора категорий.

    Предоставляет поиск и множественный выбор категорий с поддержкой навигации.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана выбора категорий.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._categories: list[dict[str, str]] = []
        self._filtered_categories: list[dict[str, str]] = []
        self._selected_indices: set[int] = set()
        self._search_field: ptg.InputField | None = None
        self._category_container: NavigableContainer | None = None
        self._counter_label: ptg.Label | None = None
        # Хранилище для checkbox виджетов
        self._checkboxes: list[Checkbox] = []
        # Контейнер для кнопок
        self._button_container: NavigableContainer | None = None

        self._load_categories()

    def _load_categories(self) -> None:
        """Загрузить список категорий."""
        self._categories = self._app.get_categories()
        self._filtered_categories = self._categories.copy()

        # Восстановить ранее выбранные категории
        selected_names = set(self._app.selected_categories)
        for i, category in enumerate(self._categories):
            if category.get("name") in selected_names:
                self._selected_indices.add(i)

    def create_window(self) -> ptg.Window:
        """
        Создать окно выбора категорий.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Выбор категорий[/bold cyan]",
            justify="center",
        )

        # Поле поиска
        self._search_field = ptg.InputField(
            placeholder="Поиск категории...",
            on_change=self._filter_categories,
        )

        # Контейнер для категорий (будет заполнен динамически)
        self._category_container = NavigableContainer()
        self._category_container.set_app(self._app)
        self._populate_categories()

        # Счётчик выбранных категорий
        selected_count = len(self._selected_indices)
        total_count = len(self._categories)
        self._counter_label = ptg.Label(
            f"[green]Выбрано: {selected_count}[/green] из {total_count}",
            justify="center",
        )

        # Кнопки управления в навигируемом контейнере
        self._button_container = NavigableContainer(
            box="EMPTY",
        )
        self._button_container.set_app(self._app)
        
        self._button_container.add_widget(ButtonWidget("Выбрать все", self._select_all))
        self._button_container.add_widget(ButtonWidget("Снять все", self._deselect_all))
        self._button_container.add_widget(ButtonWidget("Назад", self._go_back))
        self._button_container.add_widget(ButtonWidget("Далее", self._next))

        # Создание окна
        window = ptg.Window(
            "",
            header,
            "",
            ptg.Label("[dim]Введите название категории для поиска:[/dim]"),
            self._search_field,
            "",
            ptg.Splitter(
                ptg.Label("[bold]Список категорий:[/bold]"),
                self._counter_label,
            ),
            "",
            ScrollArea(
                self._category_container,
                height=15,
            ),
            "",
            self._button_container,
            width=80,
            box="DOUBLE",
        ).set_title("[bold green]Выбор категорий для парсинга[/bold green]")

        # Установить фокус на поле поиска
        if self._search_field:
            self._search_field.focus()

        return window.center()

    def _populate_categories(self) -> None:
        """Заполнить контейнер категориями."""
        if not self._category_container:
            return

        # Очистить контейнер
        self._category_container.widgets.clear()
        self._checkboxes.clear()

        for i, category in enumerate(self._filtered_categories):
            category_name = category.get("name", "Неизвестно")

            is_selected = i in self._selected_indices

            # Создать checkbox с правильным API
            checkbox = Checkbox(
                label=category_name,
                value=is_selected,
                on_change=lambda checked, idx=i: self._toggle_category(idx, checked),
            )

            self._checkboxes.append(checkbox)
            self._category_container.add_widget(checkbox)

    def _filter_categories(self, field: ptg.InputField) -> None:
        """
        Фильтровать категории по поисковому запросу.

        Args:
            field: Поле ввода с запросом
        """
        query = field.value.lower().strip()

        if not query:
            self._filtered_categories = self._categories.copy()
        else:
            self._filtered_categories = [
                cat for cat in self._categories
                if query in cat.get("name", "").lower()
            ]

        self._populate_categories()
        self._update_counter()

    def _toggle_category(self, index: int, checked: bool) -> None:
        """
        Переключить выбор категории.

        Args:
            index: Индекс категории в отфильтрованном списке
            checked: Состояние чекбокса
        """
        # Найти оригинальный индекс категории
        original_category = self._filtered_categories[index]
        original_index = self._categories.index(original_category)

        if checked:
            self._selected_indices.add(original_index)
        else:
            self._selected_indices.discard(original_index)

        self._update_counter()

    def _select_all(self, *args) -> None:
        """Выбрать все категории."""
        for i in range(len(self._filtered_categories)):
            original_category = self._filtered_categories[i]
            original_index = self._categories.index(original_category)
            self._selected_indices.add(original_index)

        # Обновить checkbox виджеты
        for checkbox in self._checkboxes:
            checkbox.value = True

        self._update_counter()

    def _deselect_all(self, *args) -> None:
        """Снять все категории."""
        self._selected_indices.clear()

        # Обновить checkbox виджеты
        for checkbox in self._checkboxes:
            checkbox.value = False

        self._update_counter()

    def _update_counter(self) -> None:
        """Обновить счётчик выбранных категорий."""
        if self._counter_label:
            selected_count = len(self._selected_indices)
            total_count = len(self._categories)
            self._counter_label.set_format(
                f"[green]Выбрано: {selected_count}[/green] из {total_count}"
            )

    def _go_back(self, *args) -> None:
        """Вернуться назад."""
        self._app.go_back()

    def _next(self, *args) -> None:
        """Перейти к следующему экрану."""
        # Сохранить выбранные категории
        selected_names = [
            self._categories[i].get("name", "")
            for i in sorted(self._selected_indices)
        ]
        self._app.selected_categories = selected_names

        # Перейти к главному меню
        self._app.go_back()
