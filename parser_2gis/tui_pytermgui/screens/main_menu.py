"""
Главное меню TUI Parser2GIS.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

if TYPE_CHECKING:
    from .app import TUIApp


class MainMenuScreen:
    """
    Класс главного меню.

    Отображает основные опции приложения.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация главного меню.

        Args:
            app: Главное приложение TUI
        """
        self._app = app

    def create_window(self) -> ptg.Window:
        """
        Создать окно главного меню.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Parser2GIS v2.1[/bold cyan]",
            justify="center",
        )

        subtitle = ptg.Label(
            "[italic]Современный парсер данных 2GIS[/italic]",
            justify="center",
        )

        # Кнопки меню - используем синтаксис [label, callback]
        button_start = ["🚀 Запустить парсинг", self._start_parsing]
        button_cities = ["📁 Выбрать города", self._select_cities]
        button_categories = ["📂 Выбрать категории", self._select_categories]
        button_browser = ["⚙️ Настройки браузера", self._browser_settings]
        button_parser = ["🔧 Настройки парсера", self._parser_settings]
        button_output = ["📊 Настройки вывода", self._output_settings]
        button_cache = ["📈 Просмотр кэша", self._view_cache]
        button_about = ["ℹ️ О программе", self._show_about]
        button_exit = ["Выход", self._exit]

        # Создание окна
        window = ptg.Window(
            "",
            header,
            subtitle,
            "",
            ptg.Label("[bold]Основное меню:[/bold]"),
            "",
            button_start,
            button_cities,
            button_categories,
            "",
            ptg.Label("[bold]Настройки:[/bold]"),
            "",
            button_browser,
            button_parser,
            button_output,
            "",
            ptg.Label("[bold]Дополнительно:[/bold]"),
            "",
            button_cache,
            button_about,
            "",
            ptg.Label("[dim]Навигация: Tab/Shift+Tab - переключение, Enter - выбор, Esc - назад[/dim]"),
            "",
            button_exit,
            width=70,
            box="DOUBLE",
        ).set_title("[bold green]Parser2GIS - Главное меню[/bold green]")

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
