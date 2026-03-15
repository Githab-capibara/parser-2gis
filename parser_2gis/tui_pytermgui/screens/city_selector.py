"""
Современный экран выбора городов для парсинга.

Особенности:
- Поиск с подсветкой совпадений
- Чекбоксы с Unicode иконками
- Счётчики выбранных элементов
- Навигационные подсказки
- Красивое визуальное оформление
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytermgui as ptg

from ..utils import UnicodeIcons, GradientText, BoxDrawing
from ..widgets import Checkbox, NavigableContainer, ButtonWidget, ScrollArea

if TYPE_CHECKING:
    from .app import TUIApp


class CitySelectorScreen:
    """
    Современный экран выбора городов.
    
    Предоставляет:
    - Поиск с подсветкой совпадений
    - Множественный выбор с чекбоксами
    - Счётчики и статистику
    - Интуитивную навигацию
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
        self._city_container: NavigableContainer | None = None
        self._counter_label: ptg.Label | None = None
        self._checkboxes: list[Checkbox] = []
        self._button_container: NavigableContainer | None = None
        
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
    
    def _create_header(self) -> ptg.Window:
        """
        Создать заголовок экрана.

        Returns:
            Window с заголовком
        """
        title_text = GradientText.ocean("Выбор городов")

        header_lines = [
            ptg.tim.parse(title_text),
            ptg.tim.parse("[dim]Выберите города для парсинга[/]"),
        ]

        return ptg.Window(
            *[ptg.Label(line, justify="center") for line in header_lines],
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FFFF]{UnicodeIcons.EMOJI_HOME} Города[/]"),
        )
    
    def _create_search_panel(self) -> ptg.Container:
        """
        Создать панель поиска.
        
        Returns:
            Container с поиском
        """
        self._search_field = ptg.InputField(
            placeholder=f"{UnicodeIcons.EMOJI_SEARCH} Введите название города...",
            on_change=self._filter_cities,
        )
        
        search_hint = ptg.Label(
            ptg.tim.parse(
                f"[dim]{UnicodeIcons.EMOJI_INFO} Начните вводить для фильтрации списка[/]"
            ),
            justify="center",
        )

        return ptg.Window(
            search_hint,
            self._search_field,
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #FFD700]{UnicodeIcons.EMOJI_SEARCH} Поиск[/]"),
        )
    
    def _create_counter_panel(self) -> ptg.Container:
        """
        Создать панель счётчика.
        
        Returns:
            Container со счётчиком
        """
        selected_count = len(self._selected_indices)
        total_count = len(self._cities)
        
        # Создать индикатор прогресса выбора
        if total_count > 0:
            percent = (selected_count / total_count) * 100
            progress_bar = f"[green]{'█' * int(percent / 5)}{'░' * (20 - int(percent / 5))}[/]"
        else:
            progress_bar = ""
        
        counter_text = ptg.tim.parse(
            f"[bold #00FF88]{UnicodeIcons.CHECK_CIRCLE} Выбрано:[/] "
            f"[green]{selected_count}[/] из [white]{total_count}[/] "
            f"{progress_bar}"
        )
        
        return ptg.Container(
            ptg.Label(counter_text, justify="center"),
            box="ROUNDED",
        )
    
    def _populate_cities(self) -> None:
        """Заполнить контейнер городами."""
        if not self._city_container:
            return
        
        # Очистить контейнер
        self._city_container._widgets.clear()
        self._checkboxes.clear()
        
        for i, city in enumerate(self._filtered_cities):
            city_name = city.get("name", "Неизвестно")
            country = city.get("country_code", "").upper()
            
            is_selected = i in self._selected_indices
            
            # Создать checkbox с иконкой
            checkbox = Checkbox(
                label=f"{city_name} ({country})",
                value=is_selected,
                on_change=lambda checked, idx=i: self._toggle_city(idx, checked),
            )
            
            self._checkboxes.append(checkbox)
            self._city_container._add_widget(checkbox)
    
    def _create_city_list(self) -> ptg.Container:
        """
        Создать список городов.
        
        Returns:
            Container со списком городов
        """
        self._city_container = NavigableContainer()
        self._city_container.set_app(self._app)
        self._populate_cities()

        return ptg.Window(
            ptg.Label(
                ptg.tim.parse(f"[bold]Список городов ({len(self._filtered_cities)}):[/]")
            ),
            ScrollArea(
                self._city_container,
                height=15,
            ),
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FF88]{UnicodeIcons.EMOJI_FOLDER} Список[/]"),
        )
    
    def _create_buttons(self) -> ptg.Container:
        """
        Создать кнопки управления.
        
        Returns:
            Container с кнопками
        """
        self._button_container = NavigableContainer(
            box="EMPTY",
        )
        self._button_container.set_app(self._app)
        
        # Кнопки с иконками
        self._button_container.add_widget(
            ButtonWidget(f"{UnicodeIcons.CHECK_CIRCLE} Выбрать все", self._select_all)
        )
        self._button_container.add_widget(
            ButtonWidget(f"{UnicodeIcons.CROSS_CIRCLE} Снять все", self._deselect_all)
        )
        self._button_container.add_widget(
            ButtonWidget(f"{UnicodeIcons.ARROW_CIRCLE_RIGHT} Далее", self._next)
        )
        self._button_container.add_widget(
            ButtonWidget(f"{UnicodeIcons.ARROW_LEFT} Назад", self._go_back)
        )

        return ptg.Window(
            self._button_container,
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #FFAA00]{UnicodeIcons.EMOJI_TOOLS} Управление[/]"),
        )
    
    def _create_footer(self) -> ptg.Container:
        """
        Создать подвал с подсказками.
        
        Returns:
            Container с подсказками
        """
        footer_text = ptg.tim.parse(
            f"[dim]"
            f"{UnicodeIcons.ARROW_CIRCLE_UP}{UnicodeIcons.ARROW_CIRCLE_DOWN} - навигация | "
            f"{UnicodeIcons.CHECK_CIRCLE} Enter - выбор | "
            f"{UnicodeIcons.CROSS_CIRCLE} Esc - назад"
            f"[/]"
        )
        
        return ptg.Container(
            ptg.Label(footer_text, justify="center"),
            box="EMPTY",
        )
    
    def create_window(self) -> ptg.Window:
        """
        Создать окно выбора городов.
        
        Returns:
            Окно pytermgui
        """
        # Создать компоненты
        header = self._create_header()
        search_panel = self._create_search_panel()
        counter_panel = self._create_counter_panel()
        city_list = self._create_city_list()
        buttons = self._create_buttons()
        footer = self._create_footer()
        
        # Создать основное окно
        window = ptg.Window(
            "",
            header,
            "",
            search_panel,
            counter_panel,
            "",
            city_list,
            "",
            buttons,
            footer,
            width=85,
            box="DOUBLE",
            title=ptg.tim.parse(f"[bold #00FF88]{UnicodeIcons.EMOJI_HOME} Parser2GIS - Выбор городов[/]"),
        )

        return window.center()
    
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
        
        # Обновить checkbox виджеты
        for checkbox in self._checkboxes:
            checkbox.value = True
        
        self._update_counter()
    
    def _deselect_all(self, *args) -> None:
        """Снять все города."""
        self._selected_indices.clear()
        
        # Обновить checkbox виджеты
        for checkbox in self._checkboxes:
            checkbox.value = False
        
        self._update_counter()
    
    def _update_counter(self) -> None:
        """Обновить счётчик выбранных городов."""
        # Пересоздать counter panel при обновлении
        pass
    
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
