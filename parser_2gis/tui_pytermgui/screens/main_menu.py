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

        # Кнопки меню
        button_start = ptg.Button(
            "🚀 Запустить парсинг",
            callback=self._start_parsing,
            style="primary",
        )

        button_cities = ptg.Button(
            "📁 Выбрать города",
            callback=self._select_cities,
            style="primary",
        )

        button_categories = ptg.Button(
            "📂 Выбрать категории",
            callback=self._select_categories,
            style="primary",
        )

        button_browser = ptg.Button(
            "⚙️ Настройки браузера",
            callback=self._browser_settings,
            style="primary",
        )

        button_parser = ptg.Button(
            "🔧 Настройки парсера",
            callback=self._parser_settings,
            style="primary",
        )

        button_output = ptg.Button(
            "📊 Настройки вывода",
            callback=self._output_settings,
            style="primary",
        )

        button_cache = ptg.Button(
            "📈 Просмотр кэша",
            callback=self._view_cache,
            style="primary",
        )

        button_about = ptg.Button(
            "ℹ️ О программе",
            callback=self._show_about,
            style="primary",
        )

        button_exit = ptg.Button(
            "Выход",
            callback=self._exit,
            style="error",
        )

        # Создание окна
        window = ptg.Window(
            "",
            header,
            subtitle,
            "",
            ptg.BoxLayout(
                ptg.Label("[bold]Основное меню:[/bold]"),
                direction="vertical",
            ),
            "",
            ptg.BoxLayout(button_start, direction="vertical"),
            ptg.BoxLayout(button_cities, direction="vertical"),
            ptg.BoxLayout(button_categories, direction="vertical"),
            "",
            ptg.BoxLayout(
                ptg.Label("[bold]Настройки:[/bold]"),
                direction="vertical",
            ),
            "",
            ptg.BoxLayout(button_browser, direction="vertical"),
            ptg.BoxLayout(button_parser, direction="vertical"),
            ptg.BoxLayout(button_output, direction="vertical"),
            "",
            ptg.BoxLayout(
                ptg.Label("[bold]Дополнительно:[/bold]"),
                direction="vertical",
            ),
            "",
            ptg.BoxLayout(button_cache, direction="vertical"),
            ptg.BoxLayout(button_about, direction="vertical"),
            "",
            ptg.BoxLayout(
                ptg.Label("[dim]Навигация: Tab/Shift+Tab - переключение, Enter - выбор, Esc - назад[/dim]"),
                justify="center",
            ),
            "",
            ptg.BoxLayout(button_exit, direction="vertical"),
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
