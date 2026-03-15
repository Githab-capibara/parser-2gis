"""
Главное меню TUI Parser2GIS.

Современный дизайн с ASCII-артом, улучшенными кнопками
и навигацией с клавиатуры.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytermgui as ptg

from ..utils import UnicodeIcons, GradientText, BoxDrawing, center_text
from ..widgets import NavigableContainer, ButtonWidget

if TYPE_CHECKING:
    from .app import TUIApp


class MainMenuScreen:
    """
    Главное меню приложения.
    
    Особенности:
    - Красивый ASCII-арт логотип
    - Градиентные заголовки
    - Интерактивные кнопки с иконками
    - Разделители между секциями
    - Информативный подвал с горячими клавишами
    """
    
    # ASCII-арт логотипы
    LOGOS = {
        "block": [
            "██████╗  ██████╗ ██╗    ",
            "██╔══██╗██╔═══██╗██║    ",
            "██████╔╝██║   ██║██║    ",
            "██╔══██╗██║   ██║██║    ",
            "██████╔╝╚██████╔╝██████╗",
            "╚═════╝  ╚═════╝ ╚═════╝",
        ],
        "slant": [
            "  ____              _              ____ ___  ____  ",
            " |  _ \\ _   _ _ __ | | __ _ _   _ / ___/ _ \\/ ___| ",
            " | |_) | | | | '_ \\| |/ _` | | | | |  | | | \\___ \\ ",
            " |  __/| |_| | | | | | (_| | |_| | |__| |_| |___) |",
            " |_|    \\__,_|_| |_|_|\\__,_|\\__, |\\____\\___/|____/ ",
            "                            |___/                  ",
        ],
        "simple": [
            "╔═╗┌─┐┌─┐┌┬┐",
            "╠╣ ├─┤└─┐ │ ",
            "╚  ┴ ┴└─┘ ┴ ",
            "   ┌─┐┌─┐┌─┐",
            "   │ ┬├┤ └─┐",
            "   └─┘└─┘└─┘",
        ],
        "minimal": [
            "P2G PARSER",
            "2GIS DATA",
        ],
    }
    
    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация главного меню.
        
        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._menu_container: NavigableContainer | None = None
        self._logo_style = "simple"
    
    def _get_logo(self) -> list[str]:
        """
        Получить ASCII-арт логотип.
        
        Returns:
            Список строк с логотипом
        """
        return self.LOGOS.get(self._logo_style, self.LOGOS["simple"])
    
    def _render_logo(self, color: str = "#00FFFF") -> str:
        """
        Отрендерить логотип с цветом.
        
        Args:
            color: Цвет логотипа
            
        Returns:
            Строка с цветным логотипом
        """
        logo_lines = self._get_logo()
        colored_lines = []
        
        for line in logo_lines:
            # Применить цвет к каждой строке
            colored_line = f"[{color}]{line}[/]"
            colored_lines.append(colored_line)
        
        return "\n".join(colored_lines)
    
    def _create_menu_buttons(self) -> list[tuple[str, str, callable]]:
        """
        Создать конфигурацию кнопок меню.
        
        Returns:
            Список кортежей (иконка, текст, callback)
        """
        return [
            # Основная секция
            (UnicodeIcons.EMOJI_START, "Запустить парсинг", self._start_parsing),
            (UnicodeIcons.EMOJI_FOLDER, "Выбрать города", self._select_cities),
            (UnicodeIcons.EMOJI_FILE, "Выбрать категории", self._select_categories),
            
            # Разделитель
            ("separator", "", None),
            
            # Настройки
            (UnicodeIcons.EMOJI_BROWSER, "Настройки браузера", self._browser_settings),
            (UnicodeIcons.EMOJI_TOOLS, "Настройки парсера", self._parser_settings),
            (UnicodeIcons.EMOJI_CHART, "Настройки вывода", self._output_settings),
            
            # Разделитель
            ("separator", "", None),
            
            # Дополнительно
            (UnicodeIcons.EMOJI_DATABASE, "Просмотр кэша", self._view_cache),
            (UnicodeIcons.EMOJI_USER, "О программе", self._show_about),
            
            # Разделитель
            ("separator", "", None),
            
            # Выход
            (UnicodeIcons.EMOJI_EXIT, "Выход", self._exit),
        ]
    
    def create_window(self) -> ptg.Window:
        """
        Создать окно главного меню.
        
        Returns:
            Окно pytermgui
        """
        # Создать контейнер для кнопок
        self._menu_container = NavigableContainer(
            box="EMPTY",
        )
        self._menu_container.set_app(self._app)
        
        # Получить конфигурацию кнопок
        button_configs = self._create_menu_buttons()
        
        # Создать кнопки
        for icon, text, callback in button_configs:
            if icon == "separator":
                # Добавить разделитель
                divider = ptg.Label(
                    ptg.tim.parse("[dim]" + UnicodeIcons.LINE_HORIZONTAL * 50 + "[/]"),
                    justify="center",
                )
                self._menu_container.add_widget(divider)
            else:
                # Создать кнопку с иконкой
                button_text = f"{icon} {text}"
                button = ButtonWidget(button_text, onclick=callback)
                self._menu_container.add_widget(button)
        
        # Создать заголовок с градиентом
        title_text = GradientText.neon("Parser2GIS")
        subtitle = ptg.Label(
            ptg.tim.parse("[italic #B0B0B0]Современный парсер данных 2GIS[/]"),
            justify="center",
        )
        
        # Версия приложения
        version_label = ptg.Label(
            ptg.tim.parse("[dim]Версия 2.1[/]"),
            justify="center",
        )
        
        # Создать окно
        window = ptg.Window(
            "",  # Отступ сверху
            self._render_logo(color="#00FFFF"),
            "",
            ptg.Label(
                ptg.tim.parse(title_text),
                justify="center",
            ),
            subtitle,
            version_label,
            "",
            ptg.Label(
                ptg.tim.parse(
                    f"[bold #00FF88]{UnicodeIcons.LINE_T_DOWN} Основное меню {UnicodeIcons.LINE_T_DOWN}[/]"
                ),
                justify="center",
            ),
            "",
            self._menu_container,
            "",
            # Подвал с подсказками
            self._create_footer(),
            width=75,
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FFFF]{UnicodeIcons.EMOJI_HOME} Parser2GIS - Главное меню[/]"),
        )

        # Установить фокус на первую кнопку
        self._menu_container.focus_first()

        return window.center()
    
    def _create_footer(self) -> ptg.Container:
        """
        Создать подвал с подсказками по навигации.
        
        Returns:
            Container с подсказками
        """
        footer_text = ptg.tim.parse(
            f"[dim]"
            f"{UnicodeIcons.ARROW_CIRCLE_RIGHT} Tab/Shift+Tab - переключение | "
            f"{UnicodeIcons.CHECK_CIRCLE} Enter - выбор | "
            f"{UnicodeIcons.CROSS_CIRCLE} Esc - назад | "
            f"{UnicodeIcons.ARROW_CIRCLE_UP}/{UnicodeIcons.ARROW_CIRCLE_DOWN} - навигация"
            f"[/]"
        )
        
        return ptg.Container(
            ptg.Label(footer_text, justify="center"),
            box="EMPTY",
        )
    
    # Callback методы
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
            # Подтверждение выхода
            confirm_window = ptg.Window(
                "",
                ptg.Label(
                    ptg.tim.parse("[bold yellow]Вы действительно хотите выйти?[/]"),
                    justify="center",
                ),
                "",
                ptg.Label(
                    ptg.tim.parse("[dim]Нажмите Enter для подтверждения, Esc для отмены[/]"),
                    justify="center",
                ),
                "",
                # Поле для обработки Enter/Esc
                ptg.InputField(
                    placeholder="Enter - выход, Esc - отмена",
                    on_change=self._confirm_exit,
                ),
                width=50,
                box="ROUNDED",
                title="[bold red]Подтверждение выхода[/]",
            )

            # Обработка подтверждения
            self._app._manager.add(confirm_window)

    def _confirm_exit(self, field: ptg.InputField) -> None:
        """
        Обработать подтверждение выхода.

        Args:
            field: Поле ввода
        """
        # При вводе любого символа подтверждаем выход
        if self._app._manager:
            self._app._manager.stop()
