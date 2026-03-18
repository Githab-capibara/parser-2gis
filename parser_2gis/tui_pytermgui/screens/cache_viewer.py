"""
Экран просмотра кэша.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytermgui as ptg

from ..widgets import ScrollArea

if TYPE_CHECKING:
    from .app import TUIApp


class CacheViewerScreen:
    """
    Экран просмотра кэша.

    Отображает статистику кэша и позволяет управлять им.
    """

    def __init__(self, app: TUIApp) -> None:
        """
        Инициализация экрана просмотра кэша.

        Args:
            app: Главное приложение TUI
        """
        self._app = app
        self._cache_stats: dict[str, Any] = {}
        self._cache_entries: list[dict[str, Any]] = []

        self._load_cache_info()

    def _load_cache_info(self) -> None:
        """Загрузить информацию о кэше."""
        # Получить путь к кэшу
        cache_dir = Path.home() / ".cache" / "parser-2gis"

        if not cache_dir.exists():
            self._cache_stats = {
                "size": 0,
                "count": 0,
                "oldest": "N/A",
                "newest": "N/A",
            }
            self._cache_entries = []
            return

        # Подсчитать размер и количество файлов
        total_size = 0
        file_count = 0
        oldest_time = None
        newest_time = None

        for cache_file in cache_dir.glob("*.json"):
            try:
                stat = cache_file.stat()
                total_size += stat.st_size
                file_count += 1

                mtime = stat.st_mtime
                if oldest_time is None or mtime < oldest_time:
                    oldest_time = mtime
                if newest_time is None or mtime > newest_time:
                    newest_time = mtime

                # Загрузить информацию о записи
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
                    self._cache_entries.append(
                        {
                            "file": cache_file.name,
                            "url": cache_data.get("url", "N/A"),
                            "size": stat.st_size,
                            "modified": str(stat.st_mtime),
                        }
                    )
            except (OSError, json.JSONDecodeError):
                continue

        from datetime import datetime

        self._cache_stats = {
            "size": total_size,
            "count": file_count,
            "oldest": (datetime.fromtimestamp(oldest_time).strftime("%Y-%m-%d %H:%M:%S") if oldest_time else "N/A"),
            "newest": (datetime.fromtimestamp(newest_time).strftime("%Y-%m-%d %H:%M:%S") if newest_time else "N/A"),
        }

    def create_window(self) -> ptg.Window:
        """
        Создать окно просмотра кэша.

        Returns:
            Окно pytermgui
        """
        # Заголовок
        header = ptg.Label(
            "[bold cyan]Просмотр кэша[/]",
            justify="center",
        )

        # Статистика кэша
        stats_text = (
            f"[bold]Размер кэша:[/] {self._format_size(self._cache_stats['size'])}\n"
            f"[bold]Количество записей:[/] {self._cache_stats['count']}\n"
            f"[bold]Старейшая запись:[/] {self._cache_stats['oldest']}\n"
            f"[bold]Новейшая запись:[/] {self._cache_stats['newest']}"
        )

        stats_label = ptg.Label(stats_text)

        # Таблица записей кэша
        if self._cache_entries:
            # Ограничить количество отображаемых записей
            display_entries = self._cache_entries[:20]

            table_data = [["Файл", "URL", "Размер"]]
            for entry in display_entries:
                table_data.append(
                    [
                        entry["file"],
                        entry["url"][:40] + "..." if len(entry["url"]) > 40 else entry["url"],
                        self._format_size(entry["size"]),
                    ]
                )

            cache_table = ptg.Table(
                *table_data,
                headers=1,
                column_widths=[20, 40, 10],
            )
        else:
            cache_table = ptg.Label("[dim]Кэш пуст[/]")

        # Кнопки управления - используем синтаксис [label, callback]
        button_clear_all = ["Очистить весь кэш", self._clear_all]
        button_clear_expired = ["Очистить истёкшее", self._clear_expired]
        button_back = ["Назад", self._go_back]

        # Создание окна
        window = ptg.Window(
            "",
            header,
            "",
            ptg.Container(
                ptg.Label("[bold]Статистика кэша:[/]"),
                box="EMPTY_VERTICAL",
            ),
            "",
            stats_label,
            "",
            ptg.Container(
                ptg.Label("[bold]Записи кэша (первые 20):[/]"),
                box="EMPTY_VERTICAL",
            ),
            "",
            ScrollArea(
                cache_table,
                height=10,
            ),
            "",
            ptg.Container(
                button_clear_all,
                button_clear_expired,
                button_back,
                box="EMPTY_HORIZONTAL",
            ),
            width=80,
            box="DOUBLE",
            title="[bold green]Управление кэшем[/]",
        )

        return window.center()

    def _format_size(self, size: int) -> str:
        """
        Форматировать размер в человекочитаемый вид.

        Args:
            size: Размер в байтах

        Returns:
            Отформатированная строка
        """
        for unit in ["Б", "КБ", "МБ", "ГБ"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size = size / 1024
        return f"{size:.1f} ТБ"

    def _clear_all(self, *args) -> None:
        """Очистить весь кэш."""
        cache_dir = Path.home() / ".cache" / "parser-2gis"

        if cache_dir.exists():
            for cache_file in cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                except OSError as e:
                    # Не прерываем очистку всего кэша из-за одного файла
                    self._app.notify(f"Не удалось удалить {cache_file.name}: {e}", "warning")

        # Перезагрузить информацию
        self._load_cache_info()

        # Показать сообщение
        self._show_message("Кэш очищен!", "success")

    def _clear_expired(self, *args) -> None:
        """Очистить истёкшие записи кэша.

        Примечание:
            Экран работает с файловым JSON-кэшем в директории
            ~/.cache/parser-2gis/*.json. Поскольку формат файлов не хранит TTL
            явно, используем время изменения файла (mtime) как критерий.
        """
        from datetime import datetime, timedelta

        cache_dir = Path.home() / ".cache" / "parser-2gis"
        ttl = timedelta(hours=24)
        threshold = datetime.now().timestamp() - ttl.total_seconds()

        deleted = 0
        errors = 0

        if cache_dir.exists():
            for cache_file in cache_dir.glob("*.json"):
                try:
                    if cache_file.stat().st_mtime < threshold:
                        cache_file.unlink()
                        deleted += 1
                except OSError:
                    errors += 1

        self._load_cache_info()

        if errors:
            self._show_message(
                f"Очищено {deleted} записей, но {errors} файлов удалить не удалось",
                "warning",
            )
        else:
            self._show_message(f"Очищено истёкших записей: {deleted}", "success")

    def _go_back(self, *args) -> None:
        """Вернуться назад."""
        self._app.go_back()

    def _show_message(self, message: str, level: str = "info") -> None:
        """Показать сообщение пользователю.

        Args:
            message: Текст сообщения
            level: Уровень (info, success, warning, error)
        """
        # Единый механизм уведомлений приложения (безопасен для тестов)
        self._app.notify(message, level)
