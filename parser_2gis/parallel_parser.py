"""
Модуль для параллельного парсинга городов.

Этот модуль предоставляет возможность одновременного парсинга нескольких URL
с использованием нескольких экземпляров браузера Chrome.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from parser_2gis.common import url_query_encode
from parser_2gis.logger import logger
from parser_2gis.parser import get_parser
from parser_2gis.writer import get_writer

if TYPE_CHECKING:
    from parser_2gis.config import Configuration


class ParallelCityParser:
    """
    Параллельный парсер для парсинга городов по категориям.

    Запускает несколько браузеров одновременно для парсинга разных URL.
    Результаты сохраняются в отдельные файлы в папке output/, затем объединяются.

    Args:
        cities: Список городов для парсинга.
        categories: Список категорий для парсинга.
        output_dir: Папка для сохранения результатов.
        config: Конфигурация.
        max_workers: Максимальное количество одновременных браузеров.
    """

    def __init__(
        self,
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
    ) -> None:
        self.cities = cities
        self.categories = categories
        self.output_dir = Path(output_dir)
        self.config = config
        self.max_workers = max_workers

        # Создаём папку output
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Блокировка для потокобезопасного логгирования
        self._lock = threading.Lock()

        # Флаг отмены
        self._cancel_event = threading.Event()

        # Статистика
        self._stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
        }

    def log(self, message: str, level: str = 'info') -> None:
        """Потокобезопасное логгирование."""
        with self._lock:
            log_func = getattr(logger, level)
            log_func(message)

    def generate_all_urls(self) -> list[tuple[str, str, str]]:
        """
        Генерирует все URL для парсинга.

        Returns:
            Список кортежей (url, category_name, city_name).
        """
        all_urls = []

        for city in self.cities:
            for category in self.categories:
                # Формируем URL для категории с кодированием
                base_url = f'https://2gis.{city["domain"]}/{city["code"]}'
                rest_url = f'/search/{url_query_encode(category["query"])}'

                if category.get("rubric_code"):
                    rest_url += f'/rubricId/{category["rubric_code"]}'

                rest_url += '/filters/sort=name'
                url = base_url + rest_url

                all_urls.append((url, category["name"], city["name"]))

        with self._lock:
            self._stats['total'] = len(all_urls)

        self.log(f'Сгенерировано {len(all_urls)} URL для парсинга', 'info')

        return all_urls

    def parse_single_url(
        self,
        url: str,
        category_name: str,
        city_name: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> tuple[bool, str]:
        """
        Парсит один URL и сохраняет результат в отдельный файл.

        Args:
            url: URL для парсинга.
            category_name: Название категории.
            city_name: Название города.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            Кортеж (успех, сообщение).
        """
        # Проверяем флаг отмены
        if self._cancel_event.is_set():
            return False, 'Отменено пользователем'

        # Формируем имя файла
        safe_city = city_name.replace(' ', '_').replace('/', '_')
        safe_category = category_name.replace(' ', '_').replace('/', '_')
        filename = f'{safe_city}_{safe_category}.csv'
        filepath = self.output_dir / filename

        try:
            self.log(f'Начало парсинга: {city_name} - {category_name}', 'info')

            # Создаем парсер
            with get_parser(
                url,
                chrome_options=self.config.chrome,
                parser_options=self.config.parser,
            ) as parser:
                # Создаем writer для этого URL
                with get_writer(str(filepath), 'csv', self.config.writer) as writer:
                    # Парсим
                    parser.parse(writer)

            self.log(f'Завершён парсинг: {city_name} - {category_name} → {filepath}', 'success')

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats['success'] += 1
                success_count = self._stats['success']
                failed_count = self._stats['failed']

            if progress_callback:
                progress_callback(success_count, failed_count, filepath.name)

            return True, str(filepath)

        except Exception as e:
            self.log(f'Ошибка парсинга {city_name} - {category_name}: {e}', 'error')

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats['failed'] += 1
                success_count = self._stats['success']
                failed_count = self._stats['failed']

            if progress_callback:
                progress_callback(success_count, failed_count, 'N/A')

            return False, str(e)

    def merge_csv_files(
        self,
        output_file: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Объединяет все CSV файлы в один с добавлением колонки "Категория".

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            True если успешно.
        """
        import csv

        self.log('Начало объединения CSV файлов...', 'info')

        # Находим все CSV файлы в output_dir
        csv_files = list(self.output_dir.glob('*.csv'))

        if not csv_files:
            self.log('Не найдено CSV файлов для объединения', 'warning')
            return False

        self.log(f'Найдено {len(csv_files)} CSV файлов для объединения', 'info')

        # Сортируем файлы по имени
        csv_files.sort(key=lambda x: x.name)

        # Открываем выходной файл
        try:
            with open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
                writer = None
                total_rows = 0

                for csv_file in csv_files:
                    if self._cancel_event.is_set():
                        self.log('Объединение отменено пользователем', 'warning')
                        return False

                    if progress_callback:
                        progress_callback(f'Обработка: {csv_file.name}')

                    # Извлекаем название категории из имени файла
                    # Формат: Город_Категория.csv
                    parts = csv_file.stem.split('_', 1)
                    category_name = parts[1] if len(parts) > 1 else parts[0]

                    # Читаем исходный файл
                    with open(csv_file, 'r', encoding='utf-8-sig', newline='') as infile:
                        reader = csv.DictReader(infile)

                        # Проверяем наличие заголовков
                        if not reader.fieldnames:
                            self.log(f'Файл {csv_file} пуст или не имеет заголовков', 'warning')
                            continue

                        # Добавляем колонку "Категория" если её нет
                        fieldnames = list(reader.fieldnames)
                        if 'Категория' not in fieldnames:
                            fieldnames.insert(0, 'Категория')

                        # Создаем writer если ещё не создан
                        if writer is None:
                            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                            writer.writeheader()

                        # Записываем строки с добавлением категории
                        for row in reader:
                            if 'Категория' not in row:
                                row['Категория'] = category_name
                            writer.writerow(row)
                            total_rows += 1

                    # Удаляем исходный файл после объединения
                    try:
                        csv_file.unlink()
                    except Exception as e:
                        self.log(f'Не удалось удалить файл {csv_file}: {e}', 'warning')

                self.log(f'Объединение завершено. Всего записей: {total_rows}', 'success')
                return True

        except Exception as e:
            self.log(f'Ошибка при объединении CSV: {e}', 'error')
            return False

    def run(
        self,
        output_file: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        merge_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Запускает параллельный парсинг всех городов и категорий.

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса парсинга.
            merge_callback: Функция обратного вызова для обновления прогресса объединения.

        Returns:
            True если успешно.
        """
        self.log(f'Запуск параллельного парсинга ({self.max_workers} потока)', 'info')
        self.log(f'Города: {[c["name"] for c in self.cities]}', 'info')
        self.log(f'Категории: {len(self.categories)}', 'info')

        # Генерируем все URL
        all_urls = self.generate_all_urls()

        if not all_urls:
            self.log('Нет URL для парсинга', 'error')
            return False

        # Запускаем параллельный парсинг
        success_count = 0
        failed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Создаём futures
            futures = {
                executor.submit(
                    self.parse_single_url,
                    url,
                    category_name,
                    city_name,
                    progress_callback,
                ): (url, category_name, city_name)
                for url, category_name, city_name in all_urls
            }

            # Обрабатываем результаты
            for future in as_completed(futures):
                url, category_name, city_name = futures[future]

                try:
                    success, result = future.result()
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        self.log(f'Не удалось: {city_name} - {category_name}', 'error')

                except Exception as e:
                    failed_count += 1
                    self.log(f'Исключение при парсинге {city_name} - {category_name}: {e}', 'error')

        self.log(
            f'Парсинг завершён. Успешно: {success_count}, Ошибок: {failed_count}',
            'info',
        )

        # Объединяем CSV файлы
        if success_count > 0:
            self.log('Начало объединения результатов...', 'info')
            merge_success = self.merge_csv_files(output_file, merge_callback)

            if not merge_success:
                self.log('Не удалось объединить CSV файлы', 'error')
                return False
        else:
            self.log('Нет успешных результатов для объединения', 'warning')
            return False

        return True

    def stop(self) -> None:
        """Останавливает парсинг."""
        self._cancel_event.set()
        self.log('Получена команда остановки парсинга', 'warning')


class ParallelCityParserThread(ParallelCityParser, threading.Thread):
    """
    Поток для параллельного парсинга городов.

    Наследуется от ParallelCityParser и threading.Thread для запуска в отдельном потоке.
    """

    def __init__(
        self,
        cities: list[dict],
        categories: list[dict],
        output_dir: str,
        config: Configuration,
        max_workers: int = 3,
        output_file: Optional[str] = None,
    ) -> None:
        ParallelCityParser.__init__(
            self,
            cities,
            categories,
            output_dir,
            config,
            max_workers,
        )
        threading.Thread.__init__(self)

        self._result: Optional[bool] = None
        self._output_file = output_file

    def run(self) -> None:
        """Точка входа потока."""
        try:
            # Используем переданный output_file или путь по умолчанию
            output_file = self._output_file or str(self.output_dir / 'merged_result.csv')
            self._result = self.run(output_file=output_file)
        except Exception as e:
            logger.error(f'Ошибка в потоке параллельного парсинга: {e}', exc_info=True)
            self._result = False

    def get_result(self) -> Optional[bool]:
        """Возвращает результат парсинга."""
        return self._result
