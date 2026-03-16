"""
Современный экран парсинга с прогресс-барами и логами.

Отображает множественные прогресс-бары, детальную статистику
и логи в реальном времени с красивым оформлением.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import pytermgui as ptg

from ..utils import (
    UnicodeIcons,
    GradientText,
    format_number,
    format_time,
    BoxDrawing,
)
from ..widgets import LogViewer, ProgressBar, MultiProgressBar

if TYPE_CHECKING:
    from .app import TUIApp
    from ..parallel_parser import ParallelParser


class ParsingScreen:
    """
    Современный экран парсинга.

    Особенности:
    - Множественные прогресс-бары с разными стилями
    - Статистика в виде карточек
    - Логи с цветными иконками
    - Кнопки управления с иконками
    - Анимация спиннера для активных операций
    - ETA (расчётное время завершения)
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана парсинга.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._parser: ParallelParser | None = None
        self._log_viewer = LogViewer(
            max_lines=100,
            show_timestamp=True,
            show_level=True,
            show_icons=True,
            truncate_length=100,
        )

        # Прогресс-бары с разными стилями
        self._url_progress = ProgressBar(
            label=f"{UnicodeIcons.EMOJI_FOLDER} URL",
            total=100,
            bar_width=35,
            fill_style="classic",
            color_scheme="neon",
            show_spinner=True,
            spinner_type="dots",
        )

        self._page_progress = ProgressBar(
            label=f"{UnicodeIcons.EMOJI_FILE} Страницы",
            total=100,
            bar_width=35,
            fill_style="smooth",
            color_scheme="ocean",
            show_spinner=False,
        )

        self._record_progress = ProgressBar(
            label=f"{UnicodeIcons.EMOJI_DATABASE} Записи",
            total=1000,
            bar_width=35,
            fill_style="braille",
            color_scheme="fire",
            show_spinner=False,
        )

        # Статистика
        self._stats: dict[str, Any] = {
            "current_city": "",
            "current_category": "",
            "success_count": 0,
            "error_count": 0,
            "speed": "0 записей/сек",
            "elapsed": "00:00:00",
            "eta": "N/A",
        }

        # Таймер обновления
        self._start_time: datetime | None = None
        self._last_update = datetime.now()

        # Кнопки управления
        self._button_pause: list | None = None
        self._button_stop: list | None = None
        self._button_minimize: list | None = None

        self._paused = False

        # Флаги для обновления UI
        self._window: ptg.Window | None = None
        self._stats_container: ptg.Container | None = None

        # Спиннер для активных операций
        self._spinner_active = False

        # Monitor для автоматического обновления
        self._monitor: Optional[ptg.Monitor] = None

    def _create_stats_cards(self) -> ptg.Container:
        """
        Создать карточки статистики.

        Returns:
            Container с карточками статистики
        """
        # Форматировать значения
        city = self._stats["current_city"] or UnicodeIcons.BULLET_SMALL
        category = self._stats["current_category"] or UnicodeIcons.BULLET_SMALL
        success = format_number(self._stats["success_count"])
        errors = format_number(self._stats["error_count"])
        speed = self._stats["speed"]
        elapsed = self._stats["elapsed"]
        eta = self._stats["eta"]

        # Создать строки статистики с иконками
        stats_lines = [
            f"[bold #00FFFF]{UnicodeIcons.EMOJI_HOME} Город:[/] [white]{city}[/]",
            f"[bold #FFD700]{UnicodeIcons.EMOJI_FILE} Категория:[/] [white]{category}[/]",
            "",
            f"[bold #00FF88]{UnicodeIcons.CHECK_CIRCLE} Успешно:[/] [green]{success}[/]",
            f"[bold #FF4444]{UnicodeIcons.CROSS_CIRCLE} Ошибок:[/] [red]{errors}[/]",
            "",
            f"[bold #FFAA00]{UnicodeIcons.EMOJI_SPEED} Скорость:[/] [yellow]{speed}[/]",
            f"[bold #00BFFF]{UnicodeIcons.EMOJI_TIME} Время:[/] [cyan]{elapsed}[/]",
            f"[bold #9400D3]{UnicodeIcons.EMOJI_TARGET} ETA:[/] [magenta]{eta}[/]",
        ]

        labels = [ptg.Label(ptg.tim.parse(line)) for line in stats_lines]

        return ptg.Window(
            *labels,
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FF88]{UnicodeIcons.EMOJI_CHART} Статистика[/]"),
        )

    def _create_control_buttons(self) -> ptg.Container:
        """
        Создать кнопки управления.

        Returns:
            Container с кнопками
        """
        # Кнопки с иконками
        pause_icon = UnicodeIcons.EMOJI_PAUSE if not self._paused else UnicodeIcons.EMOJI_PLAY
        pause_text = "Пауза" if not self._paused else "Продолжить"

        self._button_pause = [f"{pause_icon} {pause_text}", self._toggle_pause]
        self._button_stop = [f"{UnicodeIcons.EMOJI_STOP} Стоп", self._stop_parsing]
        self._button_minimize = [f"{UnicodeIcons.EMOJI_FOLDER} Свернуть", self._minimize]

        return ptg.Container(
            ptg.Label(ptg.tim.parse("[dim]Управление:[/]")),
            ptg.Container(
                self._button_pause,
                self._button_stop,
                self._button_minimize,
                box="EMPTY_HORIZONTAL",
            ),
            box="EMPTY",
        )

    def create_window(self) -> ptg.Window:
        """
        Создать окно экрана парсинга.

        Returns:
            Окно pytermgui
        """
        # Заголовок с градиентом
        header_text = GradientText.fire("Парсинг данных")
        header = ptg.Label(
            ptg.tim.parse(header_text),
            justify="center",
        )

        # Прогресс-бары
        progress_container = ptg.Window(
            ptg.Label(ptg.tim.parse("[bold]Прогресс выполнения:[/]")),
            self._url_progress.render(),
            self._page_progress.render(),
            self._record_progress.render(),
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #00FFFF]{UnicodeIcons.EMOJI_START} Прогресс[/]"),
        )

        # Статистика
        stats_container = self._create_stats_cards()

        # Логи
        log_container = ptg.Window(
            ptg.Label(ptg.tim.parse("[bold]Логи в реальном времени:[/]")),
            box="ROUNDED",
            title=ptg.tim.parse(f"[bold #FFD700]{UnicodeIcons.EMOJI_FILE} Логи[/]"),
        )

        # Добавить начальный лог
        self._log_viewer.add_log("Запуск парсинга...", "INFO")

        # Кнопки управления
        control_container = self._create_control_buttons()

        # Создать основное окно
        self._window = ptg.Window(
            "",
            header,
            "",
            progress_container,
            "",
            ptg.Container(
                stats_container,
                log_container,
                box="EMPTY_HORIZONTAL",
            ),
            "",
            control_container,
            "",
            ptg.Label(
                ptg.tim.parse(
                    f"[dim]Навигация: {UnicodeIcons.ARROW_CIRCLE_UP}{UnicodeIcons.ARROW_CIRCLE_DOWN} - скролл | "
                    f"{UnicodeIcons.CROSS_CIRCLE} Esc - назад[/]"
                ),
                justify="center",
            ),
            width=95,
            box="DOUBLE",
            title=ptg.tim.parse(
                f"[bold #00FF88]{UnicodeIcons.EMOJI_ROCKET} Parser2GIS - Парсинг[/]"
            ),
        )

        # Запустить обновление
        self._start_time = datetime.now()
        self._start_auto_update()

        return self._window.center()

    def _start_auto_update(self) -> None:
        """Запустить автоматическое обновление отображения."""
        # Используем Monitor из pytermgui для периодического обновления
        # Проверяем наличие класса Monitor и обрабатываем ImportError
        try:
            if hasattr(ptg, "Monitor"):
                self._monitor = ptg.Monitor()
                # Attach с периодом 0.5 секунды (2 раза в секунду)
                if hasattr(self._monitor, 'attach'):
                    self._monitor.attach(self._update_display, period=0.5)
                if hasattr(self._monitor, 'start'):
                    self._monitor.start()
        except (ImportError, AttributeError) as e:
            # Если Monitor недоступен, логируем ошибку и продолжаем работу
            self.add_log(f"Monitor недоступен: {e}", "WARNING")

    def update_progress(
        self,
        url_completed: int = 0,
        url_total: int | None = None,
        page_completed: int = 0,
        page_total: int | None = None,
        record_completed: int = 0,
        record_total: int | None = None,
    ) -> None:
        """
        Обновить прогресс.

        Args:
            url_completed: Количество завершённых URL
            url_total: Общее количество URL
            page_completed: Количество завершённых страниц
            page_total: Общее количество страниц
            record_completed: Количество завершённых записей
            record_total: Общее количество записей
        """
        if url_total is not None:
            self._url_progress.set_total(url_total)
        if url_completed > 0:
            self._url_progress.advance(url_completed)

        if page_total is not None:
            self._page_progress.set_total(page_total)
        if page_completed > 0:
            self._page_progress.advance(page_completed)

        if record_total is not None:
            self._record_progress.set_total(record_total)
        if record_completed > 0:
            self._record_progress.advance(record_completed)

        # Обновить UI
        self._update_progress_labels()

    def add_log(self, message: str, level: str = "INFO") -> None:
        """
        Добавить лог.

        Args:
            message: Сообщение лога
            level: Уровень лога
        """
        self._log_viewer.add_log(message, level)  # type: ignore
        # Обновить UI
        self._update_log_display()

    def update_stats(
        self,
        current_city: str | None = None,
        current_category: str | None = None,
        success_count: int | None = None,
        error_count: int | None = None,
    ) -> None:
        """
        Обновить статистику.

        Args:
            current_city: Текущий город
            current_category: Текущая категория
            success_count: Количество успешных записей
            error_count: Количество ошибок
        """
        if current_city is not None:
            self._stats["current_city"] = current_city
        if current_category is not None:
            self._stats["current_category"] = current_category
        if success_count is not None:
            self._stats["success_count"] = success_count
        if error_count is not None:
            self._stats["error_count"] = error_count

    def _update_stats_display(self) -> None:
        """Обновить отображение статистики."""
        # Вычислить прошедшее время
        if self._start_time:
            delta = datetime.now() - self._start_time
            self._stats["elapsed"] = str(delta).split(".")[0]

            # Вычислить скорость
            if self._stats["success_count"] > 0:
                elapsed_seconds = delta.total_seconds()
                if elapsed_seconds > 0:
                    records_per_sec = self._stats["success_count"] / elapsed_seconds
                    self._stats["speed"] = f"{records_per_sec:.1f} записей/сек"

        # Вычислить ETA
        total_records = self._record_progress.total
        current_record = self._record_progress.completed

        if current_record > 0 and total_records > 0:
            elapsed_seconds = (
                (datetime.now() - self._start_time).total_seconds() if self._start_time else 1
            )
            records_per_sec = current_record / elapsed_seconds if elapsed_seconds > 0 else 1
            remaining = total_records - current_record
            eta_seconds = remaining / records_per_sec if records_per_sec > 0 else 0

            self._stats["eta"] = format_time(eta_seconds)

    def _update_progress_labels(self) -> None:
        """Обновить отображение прогресс-баров."""
        # Прогресс-бары обновляются через их метод render()
        # Принудительно обновляем каждый прогресс-бар
        if self._window:
            # Обновляем отображение каждого прогресс-бара
            for progress_bar in [self._url_progress, self._page_progress, self._record_progress]:
                if hasattr(progress_bar, 'refresh'):
                    progress_bar.refresh()
                # Альтернативно можно вызвать перерисовку через manager
                if self._app and hasattr(self._app, '_manager'):
                    manager = getattr(self._app, '_manager', None)
                    if manager:
                        manager.force_full_redraw = True

    def _update_log_display(self) -> None:
        """Обновить отображение логов."""
        # Логи обновляются автоматически
        pass

    def _update_display(self) -> None:
        """Обновить отображение."""
        self._update_stats_display()
        self._update_progress_labels()
        self._update_log_display()

    def _toggle_pause(self, *args) -> None:
        """Переключить паузу."""
        self._paused = not self._paused

        if self._paused:
            self._button_pause[0] = f"{UnicodeIcons.EMOJI_PLAY} Продолжить"  # type: ignore
            self.add_log("Парсинг приостановлен", "WARNING")
        else:
            self._button_pause[0] = f"{UnicodeIcons.EMOJI_PAUSE} Пауза"  # type: ignore
            self.add_log("Парсинг продолжен", "INFO")

    def _stop_parsing(self, *args) -> None:
        """Остановить парсинг."""
        self.add_log("Остановка парсинга пользователем...", "WARNING")

        # Остановить Monitor если запущен
        if self._monitor is not None:
            try:
                if hasattr(self._monitor, 'detach'):
                    self._monitor.detach(self._update_display)
                if hasattr(self._monitor, 'stop'):
                    self._monitor.stop()
            except Exception:
                pass
            finally:
                self._monitor = None

        # Остановить парсер через приложение
        self._app._stop_parsing(success=False)
        
        # Вернуться назад только если парсинг действительно остановлен
        self._app.go_back()

    def _minimize(self, *args) -> None:
        """Свернуть окно."""
        self.add_log("Функция сворачивания в разработке", "INFO")

    def _start_parsing(self) -> None:
        """Запустить парсинг."""
        self._start_time = datetime.now()
        self._app._start_parsing()

        # TODO: Интеграция с ParallelParser
        # Здесь будет запуск реального парсера
