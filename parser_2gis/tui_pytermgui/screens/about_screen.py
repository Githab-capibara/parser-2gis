"""
Экран "О программе" для TUI Parser2GIS.

Красивое отображение информации о приложении,
версии, разработчиках и лицензии.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

from ..utils import UnicodeIcons, GradientText, BoxDrawing

if TYPE_CHECKING:
    from .app import TUIApp


class AboutScreen:
    """
    Экран "О программе".

    Особенности:
    - Красивый заголовок с градиентом
    - Информация о версии с иконками
    - Ссылки на репозиторий и документацию
    - Информация о лицензии
    - Команда разработчиков
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана.

        Args:
            app: Главное приложение TUI
        """
        self._app = app

        # Информация о приложении
        self._app_info = {
            "name": "Parser2GIS",
            "version": "2.1.0",
            "description": "Современный парсер данных 2GIS",
            "author": "Andy Trofimov",
            "license": "LGPLv3+",
            "python": "3.10+",
        }

        # Ссылки
        self._links = {
            "repository": "https://github.com/Githab-capibara/parser-2gis",
            "documentation": "https://github.com/Githab-capibara/parser-2gis/wiki",
            "changelog": "https://github.com/Githab-capibara/parser-2gis/blob/main/CHANGELOG.md",
            "issues": "https://github.com/Githab-capibara/parser-2gis/issues",
        }

        # Технологии
        self._technologies = [
            "Python 3.10+",
            "pytermgui (TUI)",
            "Rich (форматирование)",
            "Pydantic (валидация)",
            "Pychrome (browser automation)",
        ]

        # Функции
        self._features = [
            "Параллельный парсинг",
            "Мультигородской режим",
            "Гибкая настройка категорий",
            "Автоматические повторные попытки",
            "Кэширование данных",
            "Экспорт в CSV/XLSX",
            "Современный TUI интерфейс",
            "Детальное логирование",
        ]

    def _create_header(self) -> ptg.Container:
        """
        Создать заголовок экрана.

        Returns:
            Container с заголовком
        """
        # Название с градиентом
        title_text = GradientText.cyberpunk("Parser2GIS")

        # Версия
        version = self._app_info["version"]
        version_badge = f"[bold #00FF88]v{version}[/]"

        # Описание
        description = self._app_info["description"]

        header_lines = [
            ptg.tim.parse(title_text),
            ptg.tim.parse(f"[dim]{version_badge}[/]"),
            "",
            ptg.tim.parse(f"[italic #B0B0B0]{description}[/]"),
        ]

        return ptg.Window(
            *[ptg.Label(line, justify="center") for line in header_lines],
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FFFF]{UnicodeIcons.EMOJI_INFO} О программе[/]"),
        )

    def _create_info_panel(self) -> ptg.Container:
        """
        Создать панель информации.

        Returns:
            Container с информацией
        """
        info_lines = [
            f"[bold #00FFFF]{UnicodeIcons.EMOJI_FILE} Название:[/] [white]{self._app_info['name']}[/]",
            f"[bold #FFD700]{UnicodeIcons.STAR} Версия:[/] [white]{self._app_info['version']}[/]",
            f"[bold #00FF88]{UnicodeIcons.CHECK} Python:[/] [white]{self._app_info['python']}[/]",
            f"[bold #FFAA00]{UnicodeIcons.EMOJI_USER} Автор:[/] [white]{self._app_info['author']}[/]",
            f"[bold #9400D3]{UnicodeIcons.EMOJI_FILE} Лицензия:[/] [white]{self._app_info['license']}[/]",
        ]

        return ptg.Window(
            *[ptg.Label(ptg.tim.parse(line)) for line in info_lines],
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FF88]{UnicodeIcons.EMOJI_CHART} Информация[/]"),
        )

    def _create_links_panel(self) -> ptg.Container:
        """
        Создать панель ссылок.

        Returns:
            Container со ссылками
        """

        # Обрезать длинные URL для отображения
        def shorten_url(url: str, max_len: int = 45) -> str:
            if len(url) > max_len:
                return url[: max_len - 3] + "..."
            return url

        links_lines = [
            f"[bold #00FFFF]{UnicodeIcons.EMOJI_FOLDER} Репозиторий:[/]",
            f"  [underline #00BFFF]{shorten_url(self._links['repository'])}[/]",
            "",
            f"[bold #FFD700]{UnicodeIcons.EMOJI_FILE} Документация:[/]",
            f"  [underline #00BFFF]{shorten_url(self._links['documentation'])}[/]",
            "",
            f"[bold #00FF88]{UnicodeIcons.EMOJI_FILE} Changelog:[/]",
            f"  [underline #00BFFF]{shorten_url(self._links['changelog'])}[/]",
            "",
            f"[bold #FFAA00]{UnicodeIcons.EMOJI_HELP} Issues:[/]",
            f"  [underline #00BFFF]{shorten_url(self._links['issues'])}[/]",
        ]

        return ptg.Window(
            *[ptg.Label(ptg.tim.parse(line)) for line in links_lines],
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #FFD700]{UnicodeIcons.EMOJI_LINK} Ссылки[/]"),
        )

    def _create_features_panel(self) -> ptg.Container:
        """
        Создать панель функций.

        Returns:
            Container с функциями
        """
        features_lines = []
        for feature in self._features:
            features_lines.append(
                ptg.tim.parse(f"[green]{UnicodeIcons.CHECK}[/] [white]{feature}[/]")
            )

        return ptg.Window(
            *features_lines,
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FF88]{UnicodeIcons.EMOJI_STAR} Возможности[/]"),
        )

    def _create_technologies_panel(self) -> ptg.Container:
        """
        Создать панель технологий.

        Returns:
            Container с технологиями
        """
        tech_lines = []
        for tech in self._technologies:
            tech_lines.append(ptg.tim.parse(f"[cyan]{UnicodeIcons.BULLET}[/] [white]{tech}[/]"))

        return ptg.Window(
            *tech_lines,
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FFFF]{UnicodeIcons.EMOJI_TOOLS} Технологии[/]"),
        )

    def _create_footer(self) -> ptg.Container:
        """
        Создать подвал с информацией о лицензии.

        Returns:
            Container с подвалом
        """
        footer_lines = [
            ptg.tim.parse(f"[dim]{UnicodeIcons.LINE_HORIZONTAL * 60}[/]"),
            ptg.tim.parse(
                f"[dim]Распространяется под лицензией {UnicodeIcons.EMOJI_FILE} LGPLv3+[/]"
            ),
            ptg.tim.parse("[dim]© 2024 Andy Trofimov. Все права защищены.[/]"),
            "",
            ptg.tim.parse(f"[dim]Нажмите {UnicodeIcons.CROSS_CIRCLE} Esc для возврата в меню[/]"),
        ]

        return ptg.Container(
            *[ptg.Label(line, justify="center") for line in footer_lines],
            box="EMPTY",
        )

    def create_window(self) -> ptg.Window:
        """
        Создать окно экрана.

        Returns:
            Окно pytermgui
        """
        # Создать панели
        header = self._create_header()
        info_panel = self._create_info_panel()
        links_panel = self._create_links_panel()
        features_panel = self._create_features_panel()
        tech_panel = self._create_technologies_panel()
        footer = self._create_footer()

        # Создать основное окно
        window = ptg.Window(
            "",
            header,
            "",
            ptg.Container(
                info_panel,
                links_panel,
                box="EMPTY_VERTICAL",
            ),
            "",
            ptg.Container(
                features_panel,
                tech_panel,
                box="EMPTY_HORIZONTAL",
            ),
            "",
            footer,
            width=90,
            box="DOUBLE",
            title=ptg.tim.parse(f"[bold #FFD700]{UnicodeIcons.EMOJI_USER} О программе[/]"),
        )

        return window.center()
