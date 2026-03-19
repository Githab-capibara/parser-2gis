"""
Главное меню TUI Parser2GIS на Textual.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Static


class MainMenuScreen(Screen):
    """Главное меню приложения."""

    BINDINGS = [
        Binding("q", "quit", "Выход"),
    ]

    CSS = """
    MainMenuScreen {
        align: center middle;
    }

    .logo-container {
        width: 60;
        height: auto;
        content-align: center middle;
        margin-bottom: 1;
    }

    .logo {
        color: $accent;
        text-style: bold;
        width: 100%;
        content-align: center top;
    }

    .title {
        text-style: bold;
        color: $text;
        width: 100%;
        content-align: center top;
        margin: 1 0;
    }

    .subtitle {
        color: $text-muted;
        width: 100%;
        content-align: center top;
    }

    .menu-container {
        width: 50;
        height: auto;
        background: $surface-darken-2;
        border: solid $primary;
        padding: 1 2;
    }

    .menu-button {
        width: 100%;
        margin: 1 0;
    }

    .divider {
        height: 1;
        background: $primary;
        margin: 1 0;
    }

    .version {
        color: $text-muted;
        width: 100%;
        content-align: center top;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Создать интерфейс меню."""
        with Container(id="main-menu"):
            # Логотип
            with Container(classes="logo-container"):
                yield Static(
                    "╔═╗┌─┐┌─┐┌┬┐\n"
                    "╠╣ ├─┤└─┐ │ \n"
                    "╚  ┴ ┴└─┘ ┴ \n"
                    "   ┌─┐┌─┐┌─┐\n"
                    "   │ ┬├┤ └─┐\n"
                    "   └─┘└─┘└─┘",
                    classes="logo",
                )

            # Заголовок
            yield Static("Parser2GIS", classes="title")
            yield Static("Современный парсер данных 2GIS", classes="subtitle")
            yield Static("Версия 2.1", classes="version")

            # Разделитель
            yield Static("", classes="divider")

            # Кнопки меню
            with Container(classes="menu-container"):
                yield Button(
                    "🚀 Запустить парсинг", id="start-parsing", classes="menu-button"
                )
                yield Button(
                    "📁 Выбрать города", id="select-cities", classes="menu-button"
                )
                yield Button(
                    "📂 Выбрать категории",
                    id="select-categories",
                    classes="menu-button",
                )

                yield Static("", classes="divider")

                yield Button(
                    "🌐 Настройки браузера",
                    id="browser-settings",
                    classes="menu-button",
                )
                yield Button(
                    "⚙️ Настройки парсера", id="parser-settings", classes="menu-button"
                )
                yield Button(
                    "📊 Настройки вывода", id="output-settings", classes="menu-button"
                )

                yield Static("", classes="divider")

                yield Button("💾 Просмотр кэша", id="view-cache", classes="menu-button")
                yield Button("👤 О программе", id="about", classes="menu-button")

                yield Static("", classes="divider")

                yield Button(
                    "🚪 Выход", id="exit", classes="menu-button", variant="error"
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработка нажатия кнопок."""
        button_id = event.button.id

        if button_id == "start-parsing":
            self.app.push_screen("parsing")
        elif button_id == "select-cities":
            self.app.push_screen("city_selector")
        elif button_id == "select-categories":
            self.app.push_screen("category_selector")
        elif button_id == "browser-settings":
            self.app.push_screen("browser_settings")
        elif button_id == "parser-settings":
            self.app.push_screen("parser_settings")
        elif button_id == "output-settings":
            self.app.push_screen("output_settings")
        elif button_id == "view-cache":
            self.app.push_screen("cache_viewer")
        elif button_id == "about":
            self.app.push_screen("about")
        elif button_id == "exit":
            self.app.exit()
