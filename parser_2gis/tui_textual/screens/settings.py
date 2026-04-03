"""Экраны настроек для TUI на Textual."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Label, Static, Switch

# =============================================================================
# КОНСТАНТЫ ЗНАЧЕНИЙ ПО УМОЛЧАНИЮ (P0-10: устранение дублирования)
# =============================================================================

# Настройки браузера по умолчанию
BROWSER_DEFAULTS_HEADLESS: bool = True
BROWSER_DEFAULTS_DISABLE_IMAGES: bool = True
BROWSER_DEFAULTS_SILENT: bool = True
BROWSER_DEFAULTS_MEMORY_LIMIT: int = 512
BROWSER_DEFAULTS_STARTUP_DELAY: int = 0

# Настройки парсера по умолчанию
PARSER_DEFAULTS_MAX_RECORDS: int = 1000
PARSER_DEFAULTS_DELAY_BETWEEN_CLICKS: int = 500
PARSER_DEFAULTS_MAX_RETRIES: int = 3
PARSER_DEFAULTS_TIMEOUT: int = 300
PARSER_DEFAULTS_WORKERS: int = 10

# Настройки вывода по умолчанию
OUTPUT_DEFAULTS_ENCODING: str = "utf-8"
OUTPUT_DEFAULTS_ADD_RUBRICS: bool = True
OUTPUT_DEFAULTS_ADD_COMMENTS: bool = False
OUTPUT_DEFAULTS_REMOVE_DUPLICATES: bool = True


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
        """Создать интерфейс настроек браузера.

        Генерирует виджеты для переключателей Headless, изображений,
        тихого режима, полей ввода памяти и задержки, а также кнопок.

        Returns:
            ComposeResult: Результат композиции виджетов.

        """
        with Container(id="browser-settings-container"):
            yield Static("🌐 Настройки браузера", classes="header")

            with Vertical(classes="setting-row"):
                yield Label("Headless режим:", classes="setting-label")
                yield Switch(id="headless-switch", value=BROWSER_DEFAULTS_HEADLESS)

            with Vertical(classes="setting-row"):
                yield Label("Отключить изображения:", classes="setting-label")
                yield Switch(id="disable-images-switch", value=BROWSER_DEFAULTS_DISABLE_IMAGES)

            with Vertical(classes="setting-row"):
                yield Label("Тихий режим:", classes="setting-label")
                yield Switch(id="silent-switch", value=BROWSER_DEFAULTS_SILENT)

            with Vertical(classes="setting-row"):
                yield Label("Лимит памяти (МБ):", classes="setting-label")
                yield Input(id="memory-limit-input", value=str(BROWSER_DEFAULTS_MEMORY_LIMIT), type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Задержка запуска (сек):", classes="setting-label")
                yield Input(id="startup-delay-input", value=str(BROWSER_DEFAULTS_STARTUP_DELAY), type="integer")

            with Horizontal(classes="button-row"):
                yield Button("💾 Сохранить", id="save", variant="primary")
                yield Button("🔄 Сброс", id="reset", variant="warning")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки на экране настроек браузера.

        Обрабатывает кнопки: "Сохранить", "Сброс", "Назад".
        При сохранении записывает значения из виджетов в конфигурацию.

        Args:
            event: Событие нажатия кнопки.

        """
        button_id = event.button.id

        if button_id == "save":
            config = self.app.get_config()  # type: ignore
            config.chrome.headless = self.query_one("#headless-switch", Switch).value
            config.chrome.disable_images = self.query_one("#disable-images-switch", Switch).value
            config.chrome.silent_browser = self.query_one("#silent-switch", Switch).value

            memory_limit = self.query_one("#memory-limit-input", Input).value
            config.chrome.memory_limit = int(memory_limit) if memory_limit.isdigit() else BROWSER_DEFAULTS_MEMORY_LIMIT

            startup_delay = self.query_one("#startup-delay-input", Input).value
            config.chrome.startup_delay = int(startup_delay) if startup_delay.isdigit() else BROWSER_DEFAULTS_STARTUP_DELAY

            self.app.save_config()  # type: ignore
            self.app.notify("Настройки сохранены", title="Успех")  # type: ignore

        elif button_id == "reset":
            self.action_reset()

        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_reset(self) -> None:
        """Сбросить настройки браузера к значениям по умолчанию.

        Устанавливает переключатели в True и поля ввода в значения по умолчанию.
        """
        self.query_one("#headless-switch", Switch).value = BROWSER_DEFAULTS_HEADLESS
        self.query_one("#disable-images-switch", Switch).value = BROWSER_DEFAULTS_DISABLE_IMAGES
        self.query_one("#silent-switch", Switch).value = BROWSER_DEFAULTS_SILENT
        self.query_one("#memory-limit-input", Input).value = str(BROWSER_DEFAULTS_MEMORY_LIMIT)
        self.query_one("#startup-delay-input", Input).value = str(BROWSER_DEFAULTS_STARTUP_DELAY)


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
        """Создать интерфейс настроек парсера.

        Генерирует виджеты для полей ввода лимита записей, задержки,
        попыток, таймаута, количества потоков и кнопок.

        Returns:
            ComposeResult: Результат композиции виджетов.

        """
        with Container(id="parser-settings-container"):
            yield Static("⚙️ Настройки парсера", classes="header")

            with Vertical(classes="setting-row"):
                yield Label("Максимум записей:", classes="setting-label")
                yield Input(id="max-records-input", value=str(PARSER_DEFAULTS_MAX_RECORDS), type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Задержка между кликами (мс):", classes="setting-label")
                yield Input(id="delay-input", value=str(PARSER_DEFAULTS_DELAY_BETWEEN_CLICKS), type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Максимум попыток:", classes="setting-label")
                yield Input(id="max-retries-input", value=str(PARSER_DEFAULTS_MAX_RETRIES), type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Таймаут (сек):", classes="setting-label")
                yield Input(id="timeout-input", value=str(PARSER_DEFAULTS_TIMEOUT), type="integer")

            with Vertical(classes="setting-row"):
                yield Label("Потоков:", classes="setting-label")
                yield Input(id="workers-input", value=str(PARSER_DEFAULTS_WORKERS), type="integer")

            with Horizontal(classes="button-row"):
                yield Button("💾 Сохранить", id="save", variant="primary")
                yield Button("🔄 Сброс", id="reset", variant="warning")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки на экране настроек парсера.

        Обрабатывает кнопки: "Сохранить", "Сброс", "Назад".
        При сохранении записывает значения из виджетов в конфигурацию.

        Args:
            event: Событие нажатия кнопки.

        """
        button_id = event.button.id

        if button_id == "save":
            config = self.app.get_config()  # type: ignore

            max_records = self.query_one("#max-records-input", Input).value
            config.parser.max_records = int(max_records) if max_records.isdigit() else PARSER_DEFAULTS_MAX_RECORDS

            delay = self.query_one("#delay-input", Input).value
            config.parser.delay_between_clicks = int(delay) if delay.isdigit() else PARSER_DEFAULTS_DELAY_BETWEEN_CLICKS

            max_retries = self.query_one("#max-retries-input", Input).value
            config.parser.max_retries = int(max_retries) if max_retries.isdigit() else PARSER_DEFAULTS_MAX_RETRIES

            timeout = self.query_one("#timeout-input", Input).value
            config.parser.timeout = int(timeout) if timeout.isdigit() else PARSER_DEFAULTS_TIMEOUT

            workers = self.query_one("#workers-input", Input).value
            config.parallel.max_workers = int(workers) if workers.isdigit() else PARSER_DEFAULTS_WORKERS

            self.app.save_config()  # type: ignore
            self.app.notify("Настройки сохранены", title="Успех")  # type: ignore

        elif button_id == "reset":
            self.action_reset()

        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_reset(self) -> None:
        """Сбросить настройки парсера к значениям по умолчанию.

        Устанавливает поля ввода в значения по умолчанию для всех параметров.
        """
        self.query_one("#max-records-input", Input).value = str(PARSER_DEFAULTS_MAX_RECORDS)
        self.query_one("#delay-input", Input).value = str(PARSER_DEFAULTS_DELAY_BETWEEN_CLICKS)
        self.query_one("#max-retries-input", Input).value = str(PARSER_DEFAULTS_MAX_RETRIES)
        self.query_one("#timeout-input", Input).value = str(PARSER_DEFAULTS_TIMEOUT)
        self.query_one("#workers-input", Input).value = str(PARSER_DEFAULTS_WORKERS)


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
        """Создать интерфейс настроек вывода.

        Генерирует виджеты для поля ввода кодировки, переключателей
        рубрик, комментариев, удаления дубликатов и кнопок.

        Returns:
            ComposeResult: Результат композиции виджетов.

        """
        with Container(id="output-settings-container"):
            yield Static("📤 Настройки вывода", classes="header")

            with Vertical(classes="setting-row"):
                yield Label("Кодировка:", classes="setting-label")
                yield Input(id="encoding-input", value=OUTPUT_DEFAULTS_ENCODING)

            with Vertical(classes="setting-row"):
                yield Label("Добавить рубрики:", classes="setting-label")
                yield Switch(id="add-rubrics-switch", value=OUTPUT_DEFAULTS_ADD_RUBRICS)

            with Vertical(classes="setting-row"):
                yield Label("Добавить комментарии:", classes="setting-label")
                yield Switch(id="add-comments-switch", value=OUTPUT_DEFAULTS_ADD_COMMENTS)

            with Vertical(classes="setting-row"):
                yield Label("Удалить дубликаты:", classes="setting-label")
                yield Switch(id="remove-duplicates-switch", value=OUTPUT_DEFAULTS_REMOVE_DUPLICATES)

            with Horizontal(classes="button-row"):
                yield Button("💾 Сохранить", id="save", variant="primary")
                yield Button("🔄 Сброс", id="reset", variant="warning")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки на экране настроек вывода.

        Обрабатывает кнопки: "Сохранить", "Сброс", "Назад".
        При сохранении записывает значения из виджетов в конфигурацию.

        Args:
            event: Событие нажатия кнопки.

        """
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
        """Сбросить настройки вывода к значениям по умолчанию.

        Устанавливает кодировку в "utf-8" и переключатели в значения по умолчанию.
        """
        self.query_one("#encoding-input", Input).value = OUTPUT_DEFAULTS_ENCODING
        self.query_one("#add-rubrics-switch", Switch).value = OUTPUT_DEFAULTS_ADD_RUBRICS
        self.query_one("#add-comments-switch", Switch).value = OUTPUT_DEFAULTS_ADD_COMMENTS
        self.query_one("#remove-duplicates-switch", Switch).value = OUTPUT_DEFAULTS_REMOVE_DUPLICATES
