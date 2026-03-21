"""
Экраны просмотра кэша и информации о программе на Textual.
"""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Static


class CacheViewerScreen(Screen):
    """Просмотр кэша."""

    BINDINGS = [Binding("escape", "go_back", "Назад"), Binding("c", "clear_cache", "Очистить кэш")]

    CSS = """
    /* Центрирование экрана просмотра кэша */
    CacheViewerScreen {
        align: center middle;
    }

    /* Главный контейнер */
    #cache-viewer-container {
        width: 100%;
        max-width: 90;
        min-width: 60;
        height: 80%;
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

    /* Панель статистики */
    .stats-panel {
        width: 100%;
        height: auto;
        margin: 1 0;
        background: $surface-darken-3;
    }

    /* Таблица кэша */
    .cache-table {
        width: 100%;
        height: 1fr;
    }

    /* Ряд кнопок */
    .button-row {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    /* Кнопки в ряду */
    .button-row Button {
        margin: 0 1;
        min-width: 12;
    }
    """

    def compose(self) -> ComposeResult:
        """Создать интерфейс просмотра кэша.

        Генерирует виджеты для заголовка, статистики, таблицы кэша и кнопок.

        Returns:
            ComposeResult: Результат композиции виджетов.
        """
        with Container(id="cache-viewer-container"):
            yield Static("💾 Просмотр кэша", classes="header")

            # Статистика кэша
            yield Static("Загрузка статистики...", id="cache-stats", classes="stats-panel")

            # Таблица кэша
            with ScrollableContainer():
                table = DataTable(id="cache-table", classes="cache-table")
                table.add_column("URL", width=50)
                table.add_column("Размер", width=10)
                table.add_column("Дата", width=20)
                yield table

            # Кнопки
            with Horizontal(classes="button-row"):
                yield Button("🗑️ Очистить кэш", id="clear", variant="error")
                yield Button("🔄 Обновить", id="refresh", variant="primary")
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_mount(self) -> None:
        """Загрузить данные кэша при монтировании экрана.

        Вызывает методы загрузки статистики и данных кэша.
        """
        self._load_cache_stats()
        self._load_cache_data()

    def _load_cache_stats(self) -> None:
        """Загрузить статистику кэша.

        Получает размер файла кэша и отображает информацию о нём.
        Если файл кэша не существует, отображает сообщение "Кэш пуст".
        """
        from parser_2gis.paths import cache_path

        cache_dir = cache_path()
        cache_file = cache_dir / "cache.db"

        if cache_file.exists():
            size_mb = cache_file.stat().st_size / (1024 * 1024)
            stats_text = f"Размер кэша: {size_mb:.2f} МБ | Файл: {cache_file}"
        else:
            stats_text = "Кэш пуст"

        stats_label = self.query_one("#cache-stats", Static)
        stats_label.update(stats_text)

    def _load_cache_data(self) -> None:
        """Загрузить данные кэша в таблицу.

        Очищает таблицу и заполняет её данными из кэша.
        В текущей реализации отображает заглушку "Нет данных".
        """
        table = self.query_one("#cache-table", DataTable)
        table.clear()

        # Здесь должна быть логика загрузки данных из кэша
        # Для демонстрации добавим пустые строки
        table.add_row("Нет данных", "-", "-")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки на экране просмотра кэша.

        Обрабатывает кнопки: "Очистить", "Обновить", "Назад".

        Args:
            event: Событие нажатия кнопки.
        """
        button_id = event.button.id

        if button_id == "clear":
            self.action_clear_cache()
        elif button_id == "refresh":
            self._load_cache_stats()
            self._load_cache_data()
            self.app.notify("Кэш обновлён", title="Инфо")  # type: ignore
        elif button_id == "back":
            self.app.pop_screen()  # type: ignore

    def action_clear_cache(self) -> None:
        """Очистить кэш.

        Создаёт экземпляр CacheManager и вызывает метод clear()
        для удаления всех данных из кэша. После очистки обновляет
        отображение статистики и данных.
        """

        from parser_2gis.cache import CacheManager
        from parser_2gis.paths import cache_path

        cache_dir = cache_path()
        cache_manager = CacheManager(cache_dir=cache_dir)
        cache_manager.clear()

        self._load_cache_stats()
        self._load_cache_data()
        self.app.notify("Кэш очищен", title="Успех")  # type: ignore


class AboutScreen(Screen):
    """Информация о программе."""

    BINDINGS = [Binding("escape", "go_back", "Назад")]

    CSS = """
    /* Центрирование экрана информации */
    AboutScreen {
        align: center middle;
    }

    /* Главный контейнер */
    #about-container {
        width: 100%;
        max-width: 80;
        min-width: 50;
        height: auto;
        background: $surface-darken-2;
        border: solid $primary;
        padding: 2 3;
        align: center middle;
    }

    /* Заголовок */
    .title {
        width: 100%;
        height: 3;
        content-align: center middle;
        text-style: bold;
        color: $accent;
    }

    /* Информационная секция */
    .info-section {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Метка информации */
    .info-label {
        width: 100%;
        margin: 1 0;
    }

    /* Разделитель */
    .divider {
        height: 1;
        background: $primary;
        margin: 1 0;
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
        """Создать интерфейс экрана информации о программе.

        Генерирует виджеты для заголовка, информационной секции,
        списка возможностей и кнопок.

        Returns:
            ComposeResult: Результат композиции виджетов.
        """
        with Container(id="about-container"):
            yield Static("👤 О программе", classes="title")

            with Vertical(classes="info-section"):
                yield Static(
                    "[bold]Parser2GIS[/] - профессиональное решение для\n"
                    "автоматизированного сбора данных с портала 2GIS.",
                    classes="info-label",
                )

            yield Static("", classes="divider")

            with Vertical(classes="info-section"):
                yield Static("[bold]Версия:[/] 2.1.0", classes="info-label")
                yield Static("[bold]Python:[/] 3.10+", classes="info-label")
                yield Static("[bold]TUI Framework:[/] Textual", classes="info-label")
                yield Static("[bold]Лицензия:[/] LGPLv3+", classes="info-label")

            yield Static("", classes="divider")

            with Vertical(classes="info-section"):
                yield Static(
                    "[bold]Возможности:[/]\n"
                    "• Парсинг 204 городов в 18 странах\n"
                    "• 93 основных категории\n"
                    "• 1786 точных рубрик\n"
                    "• До 20 параллельных потоков\n"
                    "• Форматы: CSV, XLSX, JSON\n"
                    "• Кэширование на SQLite\n"
                    "• 1000+ автоматических тестов",
                    classes="info-label",
                )

            yield Static("", classes="divider")

            with Vertical(classes="info-section"):
                yield Static(
                    "[bold]GitHub:[/] https://github.com/Githab-capibara/parser-2gis",
                    classes="info-label",
                )

            # Кнопки
            with Horizontal(classes="button-row"):
                yield Button("⬅️ Назад", id="back", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки на экране информации.

        Обрабатывает кнопку "Назад" для возврата на предыдущий экран.

        Args:
            event: Событие нажатия кнопки.
        """
        if event.button.id == "back":
            self.app.pop_screen()  # type: ignore
