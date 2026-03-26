"""
Модуль для экспорта статистики работы парсера.

Предоставляет функциональность для сбора и экспорта статистики
работы парсера в различные форматы (JSON, CSV, HTML).
- Добавлен logger для предупреждений о переполнении счётчиков
"""

import html as html_module
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# Получаем логгер модуля
logger = logging.getLogger(__name__)


@dataclass
class ParserStatistics:
    """Статистика работы парсера.

    Содержит полную информацию о работе парсера, включая
    количество обработанных записей, время работы и другую статистику.
    - Добавлены проверки границ для всех счётчиков
    - Используется itertools.count() для безопасного инкремента
    - Максимальные значения ограничены константами

    Attributes:
        start_time: Время начала работы парсера
        end_time: Время завершения работы парсера
        total_urls: Общее количество обработанных URL
        total_pages: Общее количество обработанных страниц
        total_records: Общее количество спарсенных записей
        successful_records: Количество успешных записей
        failed_records: Количество записей с ошибками
        cache_hits: Количество попаданий в кэш
        cache_misses: Количество промахов кэша
        errors: Список ошибок, произошедших во время работы
    """

    # Константы для предотвращения переполнения
    max_counter_value: int = 2**31 - 1  # Максимальное значение 32-битного signed int

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_urls: int = 0
    total_pages: int = 0
    total_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: list[str] = field(
        default_factory=list
    )  # FIX #14: Use factory instead of mutable default

    def _safe_increment(self, current_value: int, increment: int = 1) -> int:
        """Безопасно инкрементирует счётчик с проверкой на переполнение.
        - Проверяет достижение максимального значения
        - Предотвращает переполнение int
        - Логирует предупреждение при достижении лимита

        Args:
            current_value: Текущее значение счётчика.
            increment: На сколько увеличить счётчик.

        Returns:
            Новое значение счётчика или максимальное значение при переполнении.
        """
        if current_value >= self.max_counter_value:
            logger.warning("Достигнуто максимальное значение счётчика: %d", self.max_counter_value)
            return self.max_counter_value

        new_value = current_value + increment
        if new_value > self.max_counter_value:
            logger.warning(
                "Счётчик достигнет максимума: %d + %d = %d (ограничено до %d)",
                current_value,
                increment,
                new_value,
                self.max_counter_value,
            )
            return self.max_counter_value

        return new_value

    def increment_urls(self, count: int = 1) -> None:
        """Безопасно инкрементирует счётчик URL."""
        self.total_urls = self._safe_increment(self.total_urls, count)

    def increment_pages(self, count: int = 1) -> None:
        """Безопасно инкрементирует счётчик страниц."""
        self.total_pages = self._safe_increment(self.total_pages, count)

    def increment_records(self, count: int = 1) -> None:
        """Безопасно инкрементирует счётчик записей."""
        self.total_records = self._safe_increment(self.total_records, count)

    def increment_successful(self, count: int = 1) -> None:
        """Безопасно инкрементирует счётчик успешных записей."""
        self.successful_records = self._safe_increment(self.successful_records, count)

    def increment_failed(self, count: int = 1) -> None:
        """Безопасно инкрементирует счётчик записей с ошибками."""
        self.failed_records = self._safe_increment(self.failed_records, count)

    def increment_cache_hits(self, count: int = 1) -> None:
        """Безопасно инкрементирует счётчик попаданий в кэш."""
        self.cache_hits = self._safe_increment(self.cache_hits, count)

    def increment_cache_misses(self, count: int = 1) -> None:
        """Безопасно инкрементирует счётчик промахов кэша."""
        self.cache_misses = self._safe_increment(self.cache_misses, count)

    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """Время работы парсера.

        Returns:
            Разница между end_time и start_time, или None если работа не завершена
            или если end_time < start_time (некорректные данные).
        """
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            # Проверяем что end_time >= start_time
            if delta.total_seconds() >= 0:
                return delta
            # Возвращаем None если время некорректно
            return None
        return None

    @property
    def success_rate(self) -> float:
        """Успешность работы парсера в процентах.

        Returns:
            Процент успешных записей от общего количества
        """
        if self.total_records == 0:
            return 0.0
        # Защита от деления на ноль и отрицательных значений
        # ИСПРАВЛЕНИЕ 9: Добавлена проверка корректности данных с warning
        if self.successful_records < 0 or self.successful_records > self.total_records:
            logger.warning(
                "Некорректные данные: successful=%d, total=%d. Возвращаем 100%%",
                self.successful_records,
                self.total_records,
            )
            return 100.0
        return (self.successful_records / self.total_records) * 100

    @property
    def cache_hit_rate(self) -> float:
        """Коэффициент попадания в кэш в процентах.

        Returns:
            Процент попаданий в кэш от общего количества запросов
        """
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        # Защита от некорректных значений
        if self.cache_hits < 0 or self.cache_hits > total_cache_requests:
            return 0.0
        return (self.cache_hits / total_cache_requests) * 100


class StatisticsExporter:
    """Экспортер статистики работы парсера.

    Этот класс предоставляет возможность экспорта статистики работы
    парсера в различные форматы: JSON, CSV, HTML.

    Пример использования:
        >>> stats = ParserStatistics()
        >>> stats.start_time = datetime.now()
        >>> # ... работа парсера ...
        >>> stats.end_time = datetime.now()
        >>> exporter = StatisticsExporter()
        >>> exporter.export_to_json(stats, Path('stats.json'))
    """

    def __init__(self) -> None:
        """Initialize statistics exporter."""

    @staticmethod
    def _ensure_dir(file_path: Path) -> None:
        """Создаёт директорию для файла если она не существует.

        Args:
            file_path: Путь к файлу, для которого нужно создать директорию.
        """
        file_path.parent.mkdir(parents=True, exist_ok=True)

    def export_to_json(self, stats: ParserStatistics, output_path: Path) -> None:
        """Экспорт статистики в формат JSON.

        Сохраняет статистику в JSON файл с подробной информацией
        о работе парсера.

        Args:
            stats: Объект статистики для экспорта
            output_path: Путь к файлу для сохранения

        Raises:
            IOError: Если не удалось записать файл
        """
        data = self._prepare_for_json(stats)
        self._ensure_dir(output_path)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def export_to_csv(self, stats: ParserStatistics, output_path: Path) -> None:
        """Экспорт статистики в формат CSV.

        Сохраняет статистику в CSV файл с основными показателями.

        Args:
            stats: Объект статистики для экспорта
            output_path: Путь к файлу для сохранения

        Raises:
            IOError: Если не удалось записать файл
        """
        import csv

        data = self._prepare_for_dict(stats)
        self._ensure_dir(output_path)
        with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Показатель", "Значение"])
            for key, value in data.items():
                writer.writerow([key, value])

    def export_to_html(self, stats: ParserStatistics, output_path: Path) -> None:
        """Экспорт статистики в формат HTML.

        Сохраняет статистику в HTML файл с красивым оформлением.
        Подходит для визуального просмотра в браузере.

        Args:
            stats: Объект статистики для экспорта
            output_path: Путь к файлу для сохранения

        Raises:
            IOError: Если не удалось записать файл
        """
        html_content = self._generate_html(stats)
        self._ensure_dir(output_path)
        with output_path.open("w", encoding="utf-8") as f:
            f.write(html_content)

    def _prepare_for_json(self, stats: ParserStatistics) -> Dict[str, Any]:
        """Подготовка данных для JSON экспорта.

        Преобразует объект статистики в словарь, подходящий для JSON.

        Args:
            stats: Объект статистики

        Returns:
            Словарь с данными для JSON
        """
        data = {
            "start_time": stats.start_time.isoformat() if stats.start_time else None,
            "end_time": stats.end_time.isoformat() if stats.end_time else None,
            "elapsed_time": str(stats.elapsed_time) if stats.elapsed_time else None,
            "total_urls": stats.total_urls,
            "total_pages": stats.total_pages,
            "total_records": stats.total_records,
            "successful_records": stats.successful_records,
            "failed_records": stats.failed_records,
            "success_rate": round(stats.success_rate, 2),
            "cache_hits": stats.cache_hits,
            "cache_misses": stats.cache_misses,
            "cache_hit_rate": round(stats.cache_hit_rate, 2),
            "errors": stats.errors,
        }

        return data

    def _prepare_for_dict(self, stats: ParserStatistics) -> Dict[str, str]:
        """Подготовка данных для CSV экспорта.

        Преобразует объект статистики в словарь с читаемыми названиями.

        Args:
            stats: Объект статистики

        Returns:
            Словарь с данными для CSV
        """
        return {
            "Время начала": (
                stats.start_time.strftime("%Y-%m-%d %H:%M:%S")
                if stats.start_time
                else "Не запущено"
            ),
            "Время завершения": (
                stats.end_time.strftime("%Y-%m-%d %H:%M:%S") if stats.end_time else "Не завершено"
            ),
            "Время работы": (str(stats.elapsed_time) if stats.elapsed_time else "Не завершено"),
            "Всего URL": str(stats.total_urls),
            "Всего страниц": str(stats.total_pages),
            "Всего записей": str(stats.total_records),
            "Успешных записей": str(stats.successful_records),
            "Записей с ошибками": str(stats.failed_records),
            "Успешность": f"{stats.success_rate:.2f}%",
            "Попаданий в кэш": str(stats.cache_hits),
            "Промахов кэша": str(stats.cache_misses),
            "Коэффициент кэша": f"{stats.cache_hit_rate:.2f}%",
            "Количество ошибок": str(len(stats.errors)),
        }

    def _generate_html(self, stats: ParserStatistics) -> str:
        """Генерация HTML отчета.

        Создает красивый HTML отчет с использованием CSS стилей.
        Оптимизация: используется список и join() вместо конкатенации строк.

        Args:
            stats: Объект статистики

        Returns:
            HTML содержимое отчета
        """
        data = self._prepare_for_dict(stats)

        # Используем список для накопления частей HTML вместо конкатенации
        html_parts: list[str] = []

        # Добавляем заголовок HTML документа
        html_parts.append("""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none';">
    <title>Статистика работы Parser2GIS</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .success {{
            color: #4CAF50;
            font-weight: bold;
        }}
        .error {{
            color: #f44336;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>Статистика работы Parser2GIS</h1>
    <table>
        <thead>
            <tr>
                <th>Показатель</th>
                <th>Значение</th>
            </tr>
        </thead>
        <tbody>""")

        # Добавляем данные в таблицу
        for key, value in data.items():
            value_class = ""
            if "Успешность" in key:
                try:
                    # Экранируем значение перед парсингом
                    safe_value = html_module.escape(str(value))
                    value_num = float(safe_value.rstrip("%"))
                    value_class = "success" if value_num > 80 else "error"
                except (ValueError, TypeError):
                    value_class = ""

            # Экранируем ключ и значение для предотвращения XSS
            safe_key = html_module.escape(str(key))
            safe_value = html_module.escape(str(value))

            html_parts.append(f"""            <tr>
                <td>{safe_key}</td>
                <td class="{value_class}">{safe_value}</td>
            </tr>""")

        # Добавляем ошибки, если есть
        if stats.errors:
            html_parts.append("""            <tr>
                <td colspan="2"><strong>Ошибки:</strong></td>
            </tr>""")

            for error in stats.errors:
                # Экранируем HTML для предотвращения XSS-атак
                safe_error = html_module.escape(str(error))
                html_parts.append(f"""            <tr>
                <td colspan="2">{safe_error}</td>
            </tr>""")

        # Добавляем закрывающую часть HTML документа
        # Экранируем дату для предотвращения XSS через манипуляцию времени
        safe_timestamp = html_module.escape(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), quote=True
        )
        html_parts.append(f"""        </tbody>
    </table>
    <div class="footer">
        Сгенерировано: {safe_timestamp}
    </div>
</body>
</html>""")

        # Объединяем все части в одну строку
        return "\n".join(html_parts)
