"""
Главное меню TUI Parser2GIS.

Поддерживает навигацию с клавиатуры:
- Tab/Shift+Tab - переключение между кнопками
- Enter - активация кнопки
- Esc - возврат назад
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

from ..widgets import NavigableContainer, ButtonWidget

if TYPE_CHECKING:
    from .app import TUIApp


class MainMenuScreen:
    """
    Класс главного меню.

    Отображает основные опции приложения с поддержкой навигации.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация главного меню.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._menu_container: NavigableContainer | None = None

    def create_window(self) -> ptg.Window:
        """
        Создать окно главного меню.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Parser2GIS v2.1[/]",
            justify="center",
        )

        subtitle = ptg.Label(
            "[italic]Современный парсер данных 2GIS[/]",
            justify="center",
        )

        # Создаём кнопки с поддержкой навигации
        self._menu_container = NavigableContainer(
            box="EMPTY",
        )
        self._menu_container.set_app(self._app)

        # Кнопки меню
        self._menu_container.add_widget(ButtonWidget("🚀 Запустить парсинг", onclick=self._start_parsing))
        self._menu_container.add_widget(ButtonWidget("📁 Выбрать города", onclick=self._select_cities))
        self._menu_container.add_widget(ButtonWidget("📂 Выбрать категории", onclick=self._select_categories))

        self._menu_container.add_widget(ptg.Label(""))
        self._menu_container.add_widget(ptg.Label("[bold]Настройки:[/]"))

        self._menu_container.add_widget(ButtonWidget("⚙️ Настройки браузера", onclick=self._browser_settings))
        self._menu_container.add_widget(ButtonWidget("🔧 Настройки парсера", onclick=self._parser_settings))
        self._menu_container.add_widget(ButtonWidget("📊 Настройки вывода", onclick=self._output_settings))

        self._menu_container.add_widget(ptg.Label(""))
        self._menu_container.add_widget(ptg.Label("[bold]Дополнительно:[/]"))

        self._menu_container.add_widget(ButtonWidget("📈 Просмотр кэша", onclick=self._view_cache))
        self._menu_container.add_widget(ButtonWidget("ℹ️ О программе", onclick=self._show_about))
        self._menu_container.add_widget(ptg.Label(""))
        self._menu_container.add_widget(ButtonWidget("Выход", onclick=self._exit))

        # Создание окна
        window = ptg.Window(
            "",
            header,
            subtitle,
            "",
            ptg.Label("[bold]Основное меню:[/]"),
            "",
            self._menu_container,
            "",
            ptg.Label("[dim]Навигация: Tab/Shift+Tab - переключение, Enter - выбор, Esc - назад[/]"),
            width=70,
            box="DOUBLE",
        ).set_title("[bold green]Parser2GIS - Главное меню[/]")

        # Установить фокус на первую кнопку
        self._menu_container.focus_first()

        return window.center()

    def _start_parsing(self, *args) -> None:
        """Запустить парсинг."""
        self._app._show_parsing_screen()

    def _select_cities(self, *args) -> None:
        """Открыть экран выбора городов."""
        self._app._show_city_selector()

    def _select_categories(self, *args) -> None:
        """Открыть экран выбора категорий."""
        self._app._show_category_selector()

    def _browser_settings(self, *args) -> None:
        """Открыть настройки браузера."""
        self._app._show_browser_settings()

    def _parser_settings(self, *args) -> None:
        """Открыть настройки парсера."""
        self._app._show_parser_settings()

    def _output_settings(self, *args) -> None:
        """Открыть настройки вывода."""
        self._app._show_output_settings()

    def _view_cache(self, *args) -> None:
        """Просмотр кэша."""
        self._app._show_cache_viewer()

    def _show_about(self, *args) -> None:
        """Показать информацию о программе."""
        self._app._show_about()

    def _exit(self, *args) -> None:
        """Выйти из приложения."""
        if self._app._manager:
            self._app._manager.stop()
