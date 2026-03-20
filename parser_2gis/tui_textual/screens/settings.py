"""
Экраны настроек для TUI на Textual.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static, Switch


class BrowserSettingsScreen(Screen):
    """Настройки браузера."""

    BINDINGS = [Binding("escape", "go_back", "Назад"), Binding("r", "reset", "Сброс")]

    CSS = """
    /* Центрирование экрана настроек браузера */
    BrowserSettingsScreen {
        align: center middle;
    }

    /* Главный контейнер */
    #browser-settings-container {
        width: 100%;
        max-width: 80;
        min-width: 50;
        height: auto;
        background: $surface-darken-2;
        border: solid $primary;
        padding: 1 2;
        align: center middle;
    }

    /* Заголовок */
    .header {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    /* Ряд настроек */
    .setting-row {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Метка настройки */
    .setting-label {
        width: 100%;
        margin-bottom: 1;
    }

    /* Ряд кнопок */
    .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    /* Кнопки в ряду */
    .button-row Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def compose(self) -> ComposeResult:
        """Создать интерфейс."""
        with Container(id="browser-settings-container"):
            yield Static("🌐 Настройки браузера", classes="header")

            with Vertical(classes="setting-row"):
                yield Label("Headless режим:", classes="setting-label")
                yield Switch(id="headless-switch", value=True)

            with Vertical(classes="setting-row"):
                yield Label("Отключить изображения:", classes="setting-label")
                yield Switch(id="disable-images-switch", value=True)

            with Vertical(classes="setting-row"):
                yield Label("Тихий режим:", classes="setting-label")
                yield Switch(id="silent-switch", value=True)

            with Vertical(classes="setting-row"):
                yield Label("Лимит памяти (МБ):", classes="setting-label")
                yield Input(id="memory-limit-input", value="512", type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Задержка запуска (сек):", classes="setting-label")
                yield Input(id="startup-delay-input", value="0", type="integer")

            with Horizontal(classes="button-row"):
                yield Button("💾 Сохранить", id="save", variant="primary")
                yield Button("🔄 Сброс", id="reset", variant="warning")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработка кнопок."""
        button_id = event.button.id

        if button_id == "save":
            config = self.app.get_config()  # type: ignore
            config.chrome.headless = self.query_one("#headless-switch", Switch).value
            config.chrome.disable_images = self.query_one("#disable-images-switch", Switch).value
            config.chrome.silent_browser = self.query_one("#silent-switch", Switch).value

            memory_limit = self.query_one("#memory-limit-input", Input).value
            config.chrome.memory_limit = int(memory_limit) if memory_limit.isdigit() else 512

            startup_delay = self.query_one("#startup-delay-input", Input).value
            config.chrome.startup_delay = int(startup_delay) if startup_delay.isdigit() else 0

            self.app.save_config()  # type: ignore
            self.app.notify("Настройки сохранены", title="Успех")  # type: ignore

        elif button_id == "reset":
            self.action_reset()

        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_reset(self) -> None:
        """Сброс настроек."""
        self.query_one("#headless-switch", Switch).value = True
        self.query_one("#disable-images-switch", Switch).value = True
        self.query_one("#silent-switch", Switch).value = True
        self.query_one("#memory-limit-input", Input).value = "512"
        self.query_one("#startup-delay-input", Input).value = "0"


class ParserSettingsScreen(Screen):
    """Настройки парсера."""

    BINDINGS = [Binding("escape", "go_back", "Назад"), Binding("r", "reset", "Сброс")]

    CSS = """
    /* Центрирование экрана настроек парсера */
    ParserSettingsScreen {
        align: center middle;
    }

    /* Главный контейнер */
    #parser-settings-container {
        width: 100%;
        max-width: 80;
        min-width: 50;
        height: auto;
        background: $surface-darken-2;
        border: solid $primary;
        padding: 1 2;
        align: center middle;
    }

    /* Заголовок */
    .header {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    /* Ряд настроек */
    .setting-row {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Метка настройки */
    .setting-label {
        width: 100%;
        margin-bottom: 1;
    }

    /* Ряд кнопок */
    .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    /* Кнопки в ряду */
    .button-row Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def compose(self) -> ComposeResult:
        """Создать интерфейс."""
        with Container(id="parser-settings-container"):
            yield Static("⚙️ Настройки парсера", classes="header")

            with Vertical(classes="setting-row"):
                yield Label("Максимум записей:", classes="setting-label")
                yield Input(id="max-records-input", value="1000", type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Задержка между кликами (мс):", classes="setting-label")
                yield Input(id="delay-input", value="500", type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Максимум попыток:", classes="setting-label")
                yield Input(id="max-retries-input", value="3", type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Таймаут (сек):", classes="setting-label")
                yield Input(id="timeout-input", value="300", type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Потоков:", classes="setting-label")
                yield Input(id="workers-input", value="10", type="integer")

            with Horizontal(classes="button-row"):
                yield Button("💾 Сохранить", id="save", variant="primary")
                yield Button("🔄 Сброс", id="reset", variant="warning")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработка кнопок."""
        button_id = event.button.id

        if button_id == "save":
            config = self.app.get_config()  # type: ignore

            max_records = self.query_one("#max-records-input", Input).value
            config.parser.max_records = int(max_records) if max_records.isdigit() else 1000

            delay = self.query_one("#delay-input", Input).value
            config.parser.delay_between_clicks = int(delay) if delay.isdigit() else 500

            max_retries = self.query_one("#max-retries-input", Input).value
            config.parser.max_retries = int(max_retries) if max_retries.isdigit() else 3

            timeout = self.query_one("#timeout-input", Input).value
            config.parser.timeout = int(timeout) if timeout.isdigit() else 300

            workers = self.query_one("#workers-input", Input).value
            config.parser.max_workers = int(workers) if workers.isdigit() else 10

            self.app.save_config()  # type: ignore
            self.app.notify("Настройки сохранены", title="Успех")  # type: ignore

        elif button_id == "reset":
            self.action_reset()

        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_reset(self) -> None:
        """Сброс настроек."""
        self.query_one("#max-records-input", Input).value = "1000"
        self.query_one("#delay-input", Input).value = "500"
        self.query_one("#max-retries-input", Input).value = "3"
        self.query_one("#timeout-input", Input).value = "300"
        self.query_one("#workers-input", Input).value = "10"


class OutputSettingsScreen(Screen):
    """Настройки вывода."""

    BINDINGS = [Binding("escape", "go_back", "Назад"), Binding("r", "reset", "Сброс")]

    CSS = """
    /* Центрирование экрана настроек вывода */
    OutputSettingsScreen {
        align: center middle;
    }

    /* Главный контейнер */
    #output-settings-container {
        width: 100%;
        max-width: 80;
        min-width: 50;
        height: auto;
        background: $surface-darken-2;
        border: solid $primary;
        padding: 1 2;
        align: center middle;
    }

    /* Заголовок */
    .header {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    /* Ряд настроек */
    .setting-row {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Метка настройки */
    .setting-label {
        width: 100%;
        margin-bottom: 1;
    }

    /* Ряд кнопок */
    .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 2;
    }

    /* Кнопки в ряду */
    .button-row Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def compose(self) -> ComposeResult:
        """Создать интерфейс."""
        with Container(id="output-settings-container"):
            yield Static("📤 Настройки вывода", classes="header")

            with Vertical(classes="setting-row"):
                yield Label("Кодировка:", classes="setting-label")
                yield Input(id="encoding-input", value="utf-8")

            with Vertical(classes="setting-row"):
                yield Label("Добавить рубрики:", classes="setting-label")
                yield Switch(id="add-rubrics-switch", value=True)

            with Vertical(classes="setting-row"):
                yield Label("Добавить комментарии:", classes="setting-label")
                yield Switch(id="add-comments-switch", value=False)

            with Vertical(classes="setting-row"):
                yield Label("Удалить дубликаты:", classes="setting-label")
                yield Switch(id="remove-duplicates-switch", value=True)

            with Horizontal(classes="button-row"):
                yield Button("💾 Сохранить", id="save", variant="primary")
                yield Button("🔄 Сброс", id="reset", variant="warning")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработка кнопок."""
        button_id = event.button.id

        if button_id == "save":
            config = self.app.get_config()  # type: ignore

            encoding = self.query_one("#encoding-input", Input).value
            config.writer.encoding = encoding

            config.writer.csv.add_rubrics = self.query_one("#add-rubrics-switch", Switch).value
            config.writer.csv.add_comments = self.query_one("#add-comments-switch", Switch).value
            config.writer.csv.remove_duplicates = self.query_one(
                "#remove-duplicates-switch", Switch
            ).value

            self.app.save_config()  # type: ignore
            self.app.notify("Настройки сохранены", title="Успех")  # type: ignore

        elif button_id == "reset":
            self.action_reset()

        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_reset(self) -> None:
        """Сброс настроек."""
        self.query_one("#encoding-input", Input).value = "utf-8"
        self.query_one("#add-rubrics-switch", Switch).value = True
        self.query_one("#add-comments-switch", Switch).value = False
        self.query_one("#remove-duplicates-switch", Switch).value = True
