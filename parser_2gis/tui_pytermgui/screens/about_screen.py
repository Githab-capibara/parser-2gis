"""
Экран "О программе".
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

if TYPE_CHECKING:
    from .app import TUIApp


class AboutScreen:
    """
    Экран с информацией о программе.

    Отображает версию, возможности и ссылки на документацию.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана "О программе".

        Args:
            app: Главное приложение TUI
        """
        self._app = app

    def create_window(self) -> ptg.Window:
        """
        Создать окно "О программе".

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]О программе Parser2GIS[/bold cyan]",
            justify="center",
        )

        # Версия
        version_label = ptg.Label(
            "[bold green]Версия: 2.1[/bold green]",
            justify="center",
        )

        # Описание
        description = ptg.Label(
            "[italic]Современный парсер данных 2GIS с поддержкой многопоточности,[/italic]\n"
            "[italic]кэширования и интеллектуальной системы повторных попыток.[/italic]",
            justify="center",
        )

        # Возможности
        features_title = ptg.Label(
            "\n[bold]Возможности:[/bold]",
        )

        features_list = ptg.Label(
            "• 204 города в 18 странах\n"
            "• 93 категории для парсинга\n"
            "• 1786 рубрик для точного поиска\n"
            "• Параллельный парсинг (до 20 потоков)\n"
            "• Кэширование результатов (ускорение в 10-100 раз)\n"
            "• Валидация данных (телефоны, email, URL)\n"
            "• Экспорт статистики (JSON, CSV, HTML, TXT)\n"
            "• Адаптивные лимиты\n"
            "• Интеллектуальный retry\n"
            "• Монитор здоровья браузера",
        )

        # Форматы вывода
        formats_title = ptg.Label(
            "\n[bold]Форматы вывода:[/bold]",
        )

        formats_list = ptg.Label(
            "• CSV - таблица с разделителями\n"
            "• XLSX - файлы Microsoft Excel с форматированием\n"
            "• JSON - структурированные данные",
        )

        # Ссылки
        links_title = ptg.Label(
            "\n[bold]Ссылки:[/bold]",
        )

        links_list = ptg.Label(
            "[cyan]GitHub:[/cyan] https://github.com/Githab-capibara/parser-2gis.git\n"
            "[cyan]Документация:[/cyan] https://github.com/Githab-capibara/parser-2gis/wiki",
        )

        # Копирайт
        copyright_label = ptg.Label(
            "\n[dim]© 2026 Parser2GIS. Все права защищены.[/dim]",
            justify="center",
        )

        # Кнопка назад
        button_back = ptg.Button(
            "Назад",
            onclick=self._go_back,
            style="primary",
        )

        # Создание окна
        window = ptg.Window(
            "",
            header,
            "",
            version_label,
            description,
            "",
            ptg.Splitter(
                features_title,
                formats_title,
            ),
            "",
            ptg.Container(
                ptg.ScrollArea(
                    features_list,
                    height=8,
                ),
                ptg.ScrollArea(
                    formats_list,
                    height=3,
                ),
                box="EMPTY_HORIZONTAL",
            ),
            "",
            links_title,
            links_list,
            "",
            copyright_label,
            "",
            ptg.Container(
                button_back,
                box="EMPTY_HORIZONTAL",
            ),
            width=80,
            box="DOUBLE",
        ).set_title("[bold green]Информация о программе[/bold green]")

        return window.center()

    def _go_back(self, *args) -> None:
        """Вернуться назад."""
        self._app.go_back()
