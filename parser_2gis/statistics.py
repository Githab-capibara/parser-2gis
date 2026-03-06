"""
Модуль для экспорта статистики работы парсера.

Предоставляет функциональность для сбора и экспорта статистики
работы парсера в различные форматы (JSON, CSV, HTML).
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class ParserStatistics:
    """Статистика работы парсера.
    
    Содержит полную информацию о работе парсера, включая
    количество обработанных записей, время работы и другую статистику.
    
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
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_urls: int = 0
    total_pages: int = 0
    total_records: int = 0
    successful_records: int = 0
    failed_records: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    errors: list[str] = None
    
    def __post_init__(self):
        """Инициализация списка ошибок, если он не был задан."""
        if self.errors is None:
            self.errors = []
    
    @property
    def elapsed_time(self) -> Optional[timedelta]:
        """Время работы парсера.
        
        Returns:
            Разница между end_time и start_time, или None если работа не завершена
        """
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def success_rate(self) -> float:
        """Успешность работы парсера в процентах.
        
        Returns:
            Процент успешных записей от общего количества
        """
        if self.total_records == 0:
            return 0.0
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
    
    def __init__(self):
        """Инициализация экспортера статистики."""
        pass
    
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
        # Подготавливаем данные для JSON
        data = self._prepare_for_json(stats)
        
        # Записываем в файл
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
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
        
        # Подготавливаем данные
        data = self._prepare_for_dict(stats)
        
        # Записываем в файл
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            
            # Заголовок
            writer.writerow(['Показатель', 'Значение'])
            
            # Данные
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
        
        # Записываем в файл
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
            f.write(html_content)
    
    def export_to_text(self, stats: ParserStatistics, output_path: Path) -> None:
        """Экспорт статистики в формат текста.
        
        Сохраняет статистику в текстовый файл с читаемым форматом.
        
        Args:
            stats: Объект статистики для экспорта
            output_path: Путь к файлу для сохранения
            
        Raises:
            IOError: Если не удалось записать файл
        """
        text_content = self._generate_text(stats)
        
        # Записываем в файл
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
            f.write(text_content)
    
    def _prepare_for_json(self, stats: ParserStatistics) -> Dict[str, Any]:
        """Подготовка данных для JSON экспорта.
        
        Преобразует объект статистики в словарь, подходящий для JSON.
        
        Args:
            stats: Объект статистики
            
        Returns:
            Словарь с данными для JSON
        """
        data = {
            'start_time': stats.start_time.isoformat() if stats.start_time else None,
            'end_time': stats.end_time.isoformat() if stats.end_time else None,
            'elapsed_time': str(stats.elapsed_time) if stats.elapsed_time else None,
            'total_urls': stats.total_urls,
            'total_pages': stats.total_pages,
            'total_records': stats.total_records,
            'successful_records': stats.successful_records,
            'failed_records': stats.failed_records,
            'success_rate': round(stats.success_rate, 2),
            'cache_hits': stats.cache_hits,
            'cache_misses': stats.cache_misses,
            'cache_hit_rate': round(stats.cache_hit_rate, 2),
            'errors': stats.errors
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
            'Время начала': stats.start_time.strftime('%Y-%m-%d %H:%M:%S') if stats.start_time else 'Не запущено',
            'Время завершения': stats.end_time.strftime('%Y-%m-%d %H:%M:%S') if stats.end_time else 'Не завершено',
            'Время работы': str(stats.elapsed_time) if stats.elapsed_time else 'Не завершено',
            'Всего URL': str(stats.total_urls),
            'Всего страниц': str(stats.total_pages),
            'Всего записей': str(stats.total_records),
            'Успешных записей': str(stats.successful_records),
            'Записей с ошибками': str(stats.failed_records),
            'Успешность': f'{stats.success_rate:.2f}%',
            'Попаданий в кэш': str(stats.cache_hits),
            'Промахов кэша': str(stats.cache_misses),
            'Коэффициент кэша': f'{stats.cache_hit_rate:.2f}%',
            'Количество ошибок': str(len(stats.errors))
        }
    
    def _generate_html(self, stats: ParserStatistics) -> str:
        """Генерация HTML отчета.
        
        Создает красивый HTML отчет с использованием CSS стилей.
        
        Args:
            stats: Объект статистики
            
        Returns:
            HTML содержимое отчета
        """
        data = self._prepare_for_dict(stats)
        
        html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
        <tbody>
"""
        
        # Добавляем данные в таблицу
        for key, value in data.items():
            value_class = ''
            if 'Успешность' in key:
                value_class = 'success' if float(value.rstrip('%')) > 80 else 'error'
            
            html += f"            <tr>\n"
            html += f"                <td>{key}</td>\n"
            html += f'                <td class="{value_class}">{value}</td>\n'
            html += f"            </tr>\n"
        
        # Добавляем ошибки, если есть
        if stats.errors:
            html += """            <tr>
                <td colspan="2"><strong>Ошибки:</strong></td>
            </tr>
"""
            for error in stats.errors:
                html += f"""            <tr>
                <td colspan="2">{error}</td>
            </tr>
"""
        
        html += f"""        </tbody>
    </table>
    <div class="footer">
        Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>
"""
        
        return html
    
    def _generate_text(self, stats: ParserStatistics) -> str:
        """Генерация текстового отчета.
        
        Создает читаемый текстовый отчет с отступами.
        
        Args:
            stats: Объект статистики
            
        Returns:
            Текстовое содержимое отчета
        """
        data = self._prepare_for_dict(stats)
        
        text = "=" * 60 + "\n"
        text += "СТАТИСТИКА РАБОТЫ PARSER2GIS\n"
        text += "=" * 60 + "\n\n"
        
        # Добавляем данные
        for key, value in data.items():
            text += f"{key}: {value}\n"
        
        # Добавляем ошибки, если есть
        if stats.errors:
            text += "\nОШИБКИ:\n"
            text += "-" * 60 + "\n"
            for error in stats.errors:
                text += f"  - {error}\n"
        
        text += "\n" + "=" * 60 + "\n"
        text += f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return text