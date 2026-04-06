"""Главное меню TUI Parser2GIS на Textual."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import Button, Static

from ..protocols import ITuiApp


class MainMenuScreen(Screen):
    """Главное меню приложения."""

    app: ITuiApp  # type: ignore[assignment]

    BINDINGS = [Binding("q", "quit", "Выход")]

    CSS = """
    /* Центрирование главного экрана меню */
    MainMenuScreen {
        align: center middle;
    }

    /* Контейнер логотипа */
    .logo-container {
        width: 100%;
        max-width: 60;
        min-width: 40;
        height: auto;
        content-align: center middle;
        margin-bottom: 1;
        align: center middle;
    }

    /* Логотип */
    .logo {
        color: $accent;
        text-style: bold;
        width: 100%;
        content-align: center top;
    }

    /* Заголовок */
    .title {
        text-style: bold;
        color: $text;
        width: 100%;
        content-align: center top;
        margin: 1 0;
    }

    /* Подзаголовок */
    .subtitle {
        color: $text-muted;
        width: 100%;
        content-align: center top;
    }

    /* Контейнер меню */
    .menu-container {
        width: 100%;
        max-width: 50;
        min-width: 40;
        height: auto;
        background: $surface-darken-2;
        border: solid $primary;
        padding: 1 2;
        align: center middle;
    }

    /* Кнопка меню */
    .menu-button {
        width: 100%;
        margin: 1 0;
        align: center middle;
    }

    /* Разделитель */
    .divider {
        height: 1;
        background: $primary;
        margin: 1 0;
    }

    /* Версия */
    .version {
        color: $text-muted;
        width: 100%;
        content-align: center top;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Создать интерфейс главного меню.

        Генерирует виджеты для логотипа, заголовка, кнопок меню и разделителей.

        Returns:
            ComposeResult: Результат композиции виджетов.

        """
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
                yield Button("🚀 Запустить парсинг", id="start-parsing", classes="menu-button")
                yield Button("📁 Выбрать города", id="select-cities", classes="menu-button")
                yield Button("📂 Выбрать категории", id="select-categories", classes="menu-button")

                yield Static("", classes="divider")

                yield Button("🌐 Настройки браузера", id="browser-settings", classes="menu-button")
                yield Button("⚙️ Настройки парсера", id="parser-settings", classes="menu-button")
                yield Button("📊 Настройки вывода", id="output-settings", classes="menu-button")

                yield Static("", classes="divider")

                yield Button("💾 Просмотр кэша", id="view-cache", classes="menu-button")
                yield Button("👤 О программе", id="about", classes="menu-button")

                yield Static("", classes="divider")

                yield Button("🚪 Выход", id="exit", classes="menu-button", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки в главном меню.

        Перенаправляет пользователя на соответствующий экран в зависимости
        от нажатой кнопки или завершает работу приложения.

        Args:
            event: Событие нажатия кнопки.

        """
        button_id = event.button.id

        if button_id == "start-parsing":
            # Проверка что выбраны города и категории
            selected_cities = self.app.selected_cities
            selected_categories = self.app.selected_categories

            if not selected_cities:
                self.app.notify("❌ Сначала выберите города в меню '📁 Выбрать города'", timeout=5)
                return
            if not selected_categories:
                self.app.notify(
                    "❌ Сначала выберите категории в меню '📂 Выбрать категории'", timeout=5
                )
                return
            # Только если оба списка не пустые - открывать экран парсинга
            # Используем switch_screen для замены текущего экрана вместо push_screen
            # Это предотвращает накопление экранов в стеке и циклические вызовы
            self.app.switch_screen("parsing")
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
