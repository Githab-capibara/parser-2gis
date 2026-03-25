"""
Экран парсинга на Textual.
"""

from datetime import datetime

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Button, ProgressBar, RichLog, Static


class ParsingScreen(Screen):
    """Экран парсинга."""

    BINDINGS = [Binding("escape", "stop_parsing", "Стоп"), Binding("p", "toggle_pause", "Пауза")]

    CSS = """
    /* Центрирование экрана парсинга */
    ParsingScreen {
        align: center middle;
    }

    /* Главный контейнер */
    #parsing-container {
        width: 100%;
        max-width: 100;
        min-width: 70;
        height: 85%;
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

    /* Секция прогресса */
    .progress-section {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Метка прогресса */
    .progress-label {
        width: 100%;
        margin-bottom: 1;
    }

    /* Контейнер статистики */
    .stats-container {
        width: 100%;
        height: auto;
        margin: 1 0;
    }

    /* Ряд статистики */
    .stat-row {
        width: 100%;
        height: auto;
    }

    /* Метка статистики */
    .stat-label {
        width: 50%;
    }

    /* Контейнер лога */
    .log-container {
        width: 100%;
        height: 1fr;
        border: solid $secondary;
        padding: 1;
        margin: 1 0;
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

    def __init__(self) -> None:
        """Инициализация экрана."""
        super().__init__()
        self._paused = False
        self._stopping = False  # Флаг предотвращения повторной остановки
        self._parsing_started = False  # Флаг запуска парсинга
        self._start_time: datetime | None = None
        self._success_count = 0
        self._error_count = 0
        self._total_records = 0
        self._current_city = ""
        self._current_category = ""

    def compose(self) -> ComposeResult:
        """Создать интерфейс экрана парсинга.

        Генерирует виджеты для заголовка, прогресс-баров, статистики,
        лога и кнопок управления.

        Returns:
            ComposeResult: Результат композиции виджетов.
        """
        with Container(id="parsing-container"):
            # Заголовок
            yield Static("🚀 Парсинг данных", classes="header")

            # Прогресс-бары
            with Container(classes="progress-section"):
                yield Static("URL:", classes="progress-label")
                yield ProgressBar(id="url-progress", show_eta=False)

                yield Static("Страницы:", classes="progress-label")
                yield ProgressBar(id="page-progress", show_eta=False)

                yield Static("Записи:", classes="progress-label")
                yield ProgressBar(id="record-progress", show_eta=False)

            # Статистика
            with Container(classes="stats-container"):
                yield Static("", id="stats-display")

            # Логи
            with Container(classes="log-container"):
                yield RichLog(id="log-viewer", highlight=True, markup=True)

            # Кнопки
            with Horizontal(classes="button-row"):
                yield Button("⏸️ Пауза", id="pause", variant="warning")
                yield Button("🛑 Стоп", id="stop", variant="error")
                yield Button("🏠 В меню", id="home", variant="default")

    def on_mount(self) -> None:
        """Запустить парсинг при монтировании экрана.

        Инициализирует время начала, записывает сообщение о запуске в лог,
        получает выбранные города и категории из приложения и запускает
        процесс парсинга.
        """
        self._start_time = datetime.now()
        self._add_log("[bold green]Запуск парсинга...[/]")

        # Получить выбранные города и категории
        selected_city_names = self.app.selected_cities  # type: ignore
        selected_categories = self.app.selected_categories  # type: ignore

        # Отладочное логирование для диагностики
        self._add_log(f"[dim]Выбрано городов: {len(selected_city_names)}[/]")
        self._add_log(f"[dim]Выбрано категорий: {len(selected_categories)}[/]")

        cities = self.app.get_cities()  # type: ignore
        selected_cities = [city for city in cities if city.get("name") in selected_city_names]

        all_categories = self.app.get_categories()  # type: ignore
        selected_cats = [cat for cat in all_categories if cat.get("name") in selected_categories]

        # Проверка с информативным сообщением об ошибке
        if not selected_cities:
            self._add_log("[bold red]Ошибка: не выбраны города для парсинга![/]")
            self._add_log("[yellow]Выберите города в меню и попробуйте снова.[/]")
            self.call_later(self._return_to_menu)
            return

        if not selected_cats:
            self._add_log("[bold red]Ошибка: не выбраны категории для парсинга![/]")
            self._add_log("[yellow]Выберите категории в меню и попробуйте снова.[/]")
            self.call_later(self._return_to_menu)
            return

        # Запустить парсинг
        self._parsing_started = True
        self.app.start_parsing(selected_cities, selected_cats)  # type: ignore

    def _add_log(self, message: str) -> None:
        """Добавить запись в лог парсинга.

        Args:
            message: Сообщение для записи в лог с поддержкой markup.
        """
        log_viewer = self.query_one("#log-viewer", RichLog)
        log_viewer.write(message)

    def _return_to_menu(self) -> None:
        """Вернуться в предыдущее меню.

        Безопасный возврат через pop_screen() после остановки парсинга
        или при ошибке запуска.
        """
        self.app.pop_screen()  # type: ignore

    def update_progress(
        self,
        url_completed: int = 0,
        url_total: int | None = None,
        page_completed: int = 0,
        page_total: int | None = None,
        record_completed: int = 0,
        record_total: int | None = None,
    ) -> None:
        """Обновить прогресс-бары парсинга.

        Обновляет состояние прогресс-баров для URL, страниц и записей.

        Args:
            url_completed: Количество обработанных URL.
            url_total: Общее количество URL.
            page_completed: Количество обработанных страниц.
            page_total: Общее количество страниц.
            record_completed: Количество обработанных записей.
            record_total: Общее количество записей.
        """
        if url_total is not None:
            url_progress = self.query_one("#url-progress", ProgressBar)
            url_progress.update(progress=url_completed, total=url_total)

        if page_total is not None:
            page_progress = self.query_one("#page-progress", ProgressBar)
            page_progress.update(progress=page_completed, total=page_total)

        if record_total is not None:
            record_progress = self.query_one("#record-progress", ProgressBar)
            record_progress.update(progress=record_completed, total=record_total)

    def update_stats(
        self,
        current_city: str | None = None,
        current_category: str | None = None,
        success_count: int | None = None,
        error_count: int | None = None,
    ) -> None:
        """Обновить статистику парсинга.

        Обновляет текущий город, категорию, количество успешных и ошибочных
        операций, а также отображает прошедшее время.

        Args:
            current_city: Текущий обрабатываемый город.
            current_category: Текущая обрабатываемая категория.
            success_count: Количество успешных операций.
            error_count: Количество ошибок.
        """
        if current_city is not None:
            self._current_city = current_city
        if current_category is not None:
            self._current_category = current_category
        if success_count is not None:
            self._success_count = success_count
        if error_count is not None:
            self._error_count = error_count

        # Обновить отображение
        stats_display = self.query_one("#stats-display", Static)

        elapsed = "00:00:00"
        if self._start_time:
            delta = datetime.now() - self._start_time
            elapsed = str(delta).split(".")[0]

        stats_display.update(
            f"Город: {self._current_city or '-'}\n"
            f"Категория: {self._current_category or '-'}\n"
            f"Успешно: [green]{self._success_count}[/]\n"
            f"Ошибок: [red]{self._error_count}[/]\n"
            f"Время: {elapsed}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Обработать нажатие кнопки на экране парсинга.

        Обрабатывает кнопки: "Пауза", "Стоп", "В меню".

        Args:
            event: Событие нажатия кнопки.
        """
        button_id = event.button.id

        if button_id == "pause":
            self.action_toggle_pause()
        elif button_id == "stop":
            self.action_stop_parsing()
        elif button_id == "home":
            # Безопасный возврат в меню
            if self._parsing_started and not self._stopping:
                self._add_log("[yellow]Сначала остановите парсинг кнопкой 'Стоп'[/]")
            else:
                self.call_later(self._return_to_menu)

    def action_toggle_pause(self) -> None:
        """Переключить состояние паузы парсинга.

        Изменяет флаг паузы и обновляет label кнопки.
        При паузе запись в лог о приостановке, при продолжении - о возобновлении.
        """
        self._paused = not self._paused

        pause_button = self.query_one("#pause", Button)
        if self._paused:
            pause_button.label = "▶️ Продолжить"
            self._add_log("[yellow]Парсинг приостановлен[/]")
        else:
            pause_button.label = "⏸️ Пауза"
            self._add_log("[green]Парсинг продолжен[/]")

    def action_stop_parsing(self) -> None:
        """Остановить парсинг по команде пользователя.

        Корректная остановка с защитой от повторного вызова.
        Использует call_later() для безопасного переключения экранов.
        """
        # Защита от повторного вызова
        if self._stopping:
            return

        # Проверка что парсинг действительно запущен
        if not self._parsing_started:
            # Если парсинг ещё не начался - просто вернуться в меню без установки флага остановки
            self._add_log("[dim]Парсинг ещё не запущен, возврат в меню[/]")
            self.call_later(self._return_to_menu)
            return

        self._stopping = True
        self._add_log("[bold red]Остановка парсинга пользователем...[/]")

        # Установить флаг остановки приложения
        self.app.running = False  # type: ignore

        # Безопасный возврат в меню после остановки
        # call_later() гарантирует что UI обновится корректно
        self.call_later(self._return_to_menu)

    def on_parsing_complete(self, success: bool) -> None:
        """Обработать завершение парсинга.

        Args:
            success: True если парсинг завершён успешно, False если с ошибками.
        """
        if success:
            self._add_log("[bold green]Парсинг успешно завершён![/]")
        else:
            self._add_log("[bold red]Парсинг завершён с ошибками[/]")

    def on_parsing_error(self, error: str) -> None:
        """Обработать ошибку парсинга.

        Args:
            error: Текст ошибки для отображения в логе.
        """
        self._add_log(f"[bold red]Ошибка: {error}[/]")
