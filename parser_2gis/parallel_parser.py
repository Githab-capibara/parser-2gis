"""
Модуль для параллельного парсинга городов.

Этот модуль предоставляет возможность одновременного парсинга нескольких URL
с использованием нескольких экземпляров браузера Chrome.
"""

from __future__ import annotations

import shutil
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

from .common import url_query_encode
from .logger import logger, log_parser_finish, print_progress
from .parser import get_parser
from .writer import get_writer

if TYPE_CHECKING:
    from .config import Configuration


class ParallelCityParser:
    """
    Параллельный парсер для парсинга городов по категориям.

    Запускает несколько браузеров одновременно для парсинга разных URL.
    Результаты сохраняются в отдельную папку output/, затем объединяются.

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
        # Валидация входных данных: проверка списка городов
        if not cities:
            raise ValueError("Список городов не может быть пустым")

        # Валидация входных данных: проверка списка категорий
        if not categories:
            raise ValueError("Список категорий не может быть пустым")

        # Валидация входных данных: ограничение max_workers (1-20)
        if not 1 <= max_workers <= 20:
            raise ValueError("max_workers должен быть от 1 до 20")

        self.cities = cities
        self.categories = categories
        self.output_dir = Path(output_dir)
        self.config = config
        self.max_workers = max_workers

        # Проверка существования output_dir и прав на запись
        if self.output_dir.exists():
            if not self.output_dir.is_dir():
                raise ValueError(
                    f"output_dir существует, но не является директорией: {output_dir}"
                )
            # EAFP подход: проверяем права попыткой записи тестового файла
            # Это защищает от race condition между проверкой и фактической записью
            try:
                test_file = self.output_dir / ".write_test"
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError) as e:
                raise ValueError(f"Нет прав на запись в директорию: {output_dir}. Ошибка: {e}")
        else:
            # Попытка создать директорию
            try:
                self.output_dir.mkdir(parents=True, exist_ok=True)
                # EAFP проверка прав после создания
                test_file = self.output_dir / ".write_test"
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError) as e:
                raise ValueError(
                    f"Не удалось создать директорию output_dir: {output_dir}. Ошибка: {e}"
                )

        # Статистика (все операции защищены _lock)
        self._stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
        }
        # Блокировка для потокобезопасного доступа к _stats и логгирования
        self._lock = threading.Lock()

        # Флаг отмены
        self._cancel_event = threading.Event()

        # Логирование успешной инициализации
        self.log(
            f"Инициализирован парсер: {len(cities)} городов, {len(categories)} категорий, max_workers={max_workers}",
            "info",
        )

    def log(self, message: str, level: str = "info") -> None:
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
                # Получаем query категории с проверкой наличия ключа
                category_query = category.get("query", category.get("name", ""))
                # Оставляем кириллицу нетронутой, кодируем только пробелы и спецсимволы
                rest_url = f'/search/{url_query_encode(category_query)}'

                if category.get("rubric_code"):
                    rest_url += f'/rubricId/{category["rubric_code"]}'

                rest_url += "/filters/sort=name"
                url = base_url + rest_url

                all_urls.append((url, category["name"], city["name"]))

        with self._lock:
            self._stats["total"] = len(all_urls)

        self.log(f"Сгенерировано {len(all_urls)} URL для парсинга", "info")

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

        Использует временный файл для защиты от race condition:
        - Запись происходит во временный файл с уникальным именем
        - После успешного завершения файл переименовывается в целевое имя
        - При ошибке временный файл удаляется

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
            return False, "Отменено пользователем"

        # Формируем целевое имя файла
        safe_city = city_name.replace(" ", "_").replace("/", "_")
        safe_category = category_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_city}_{safe_category}.csv"
        filepath = self.output_dir / filename

        # Создаём уникальное временное имя файла
        # uuid.uuid4() гарантирует уникальность, поэтому проверка на коллизии не требуется
        temp_filename = f"{safe_city}_{safe_category}_{uuid.uuid4().hex}.tmp"
        temp_filepath = self.output_dir / temp_filename

        try:
            self.log(
                f"Начало парсинга: {city_name} - {category_name} (временный файл: {temp_filename})",
                "info",
            )

            # Создаем парсер
            with get_parser(
                url,
                chrome_options=self.config.chrome,
                parser_options=self.config.parser,
            ) as parser:
                # Создаем writer для этого URL (запись во временный файл)
                with get_writer(
                    str(temp_filepath), "csv", self.config.writer
                ) as writer:
                    # Парсим с гарантированной очисткой ресурсов
                    try:
                        parser.parse(writer)
                    finally:
                        # Гарантируем очистку даже при исключении
                        # контекстные менеджеры вызовут __exit__, но явно указываем на важность
                        pass

            # После успешного парсинга переименовываем временный файл в целевой
            # Это атомарная операция на большинстве файловых систем
            # Используем shutil.move как fallback для cross-device перемещения
            try:
                temp_filepath.replace(filepath)
            except OSError:
                # Fallback для перемещения между разными файловыми системами
                shutil.move(str(temp_filepath), str(filepath))
            self.log(
                f"Временный файл переименован: {temp_filename} → {filename}", "debug"
            )

            self.log(
                f"Завершён парсинг: {city_name} - {category_name} → {filepath}", "info"
            )

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats["success"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, filepath.name)

            return True, str(filepath)

        except Exception as e:
            self.log(f"Ошибка парсинга {city_name} - {category_name}: {e}", "error")

            # Удаляем временный файл при ошибке
            try:
                if temp_filepath.exists():
                    temp_filepath.unlink()
                    self.log(
                        f"Временный файл удалён после ошибки: {temp_filename}", "debug"
                    )
            except Exception as cleanup_error:
                self.log(
                    f"Не удалось удалить временный файл {temp_filename}: {cleanup_error}",
                    "warning",
                )

            # Потокобезопасное обновление статистики
            with self._lock:
                self._stats["failed"] += 1
                success_count = self._stats["success"]
                failed_count = self._stats["failed"]

            if progress_callback:
                progress_callback(success_count, failed_count, "N/A")

            return False, str(e)

    def merge_csv_files(
        self,
        output_file: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Объединяет все CSV файлы в один с добавлением колонки "Категория".

        Важно: Сначала объединяются ВСЕ файлы, и ТОЛЬКО ПОСЛЕ успешного
        объединения удаляются все исходные файлы. Это предотвращает потерю
        данных при ошибке в середине процесса.

        Args:
            output_file: Путь к итоговому файлу.
            progress_callback: Функция обратного вызова для обновления прогресса.

        Returns:
            True если успешно.
        """
        import csv

        self.log("Начало объединения CSV файлов...", "info")

        # Находим все CSV файлы в output_dir
        csv_files = list(self.output_dir.glob("*.csv"))

        # Исключаем объединенный файл если он уже существует (повторный запуск)
        output_file_path = Path(output_file)
        if output_file_path.exists():
            csv_files = [f for f in csv_files if f != output_file_path]
            self.log(
                f"Исключен объединенный файл из списка: {output_file_path.name}",
                "debug",
            )

        if not csv_files:
            self.log("Не найдено CSV файлов для объединения", "warning")
            return False

        self.log(f"Найдено {len(csv_files)} CSV файлов для объединения", "info")

        # Сортируем файлы по имени
        csv_files.sort(key=lambda x: x.name)

        # Список файлов для удаления (заполняется после успешного объединения)
        files_to_delete: list[Path] = []

        # Создаём временный файл для результата объединения
        # Это защищает от частичных данных при ошибке в середине процесса
        temp_output = self.output_dir / f"merged_temp_{uuid.uuid4().hex}.csv"

        # Открываем временный выходной файл
        try:
            with open(temp_output, "w", encoding="utf-8-sig", newline="") as outfile:
                writer = None
                total_rows = 0

                for csv_file in csv_files:
                    if self._cancel_event.is_set():
                        self.log("Объединение отменено пользователем", "warning")
                        # Удаляем временный файл при отмене
                        try:
                            temp_output.unlink()
                        except Exception:
                            pass
                        return False

                    if progress_callback:
                        progress_callback(f"Обработка: {csv_file.name}")

                    # Извлекаем название категории из имени файла
                    # Формат: Город_Категория.csv (город может содержать подчёркивания)
                    # Поэтому берём всё после первого подчёркивания
                    parts = csv_file.stem.split("_", 1)
                    if len(parts) > 1:
                        # Восстанавливаем категорию с возможными подчёркиваниями
                        category_name = parts[1].replace("_", " ")
                    else:
                        # Файл без категории (некорректное имя)
                        category_name = parts[0].replace("_", " ")
                        self.log(
                            f"Предупреждение: файл {csv_file.name} не содержит категорию в имени",
                            "warning",
                        )

                    # Логируем извлечение категории для отладки
                    self.log(
                        f"Файл: {csv_file.name} -> Категория: {category_name}", "debug"
                    )

                    # Читаем исходный файл
                    with open(
                        csv_file, "r", encoding="utf-8-sig", newline=""
                    ) as infile:
                        reader = csv.DictReader(infile)

                        # Проверяем наличие заголовков
                        if not reader.fieldnames:
                            self.log(
                                f"Файл {csv_file} пуст или не имеет заголовков",
                                "warning",
                            )
                            continue

                        # Добавляем колонку "Категория" если её нет
                        fieldnames = list(reader.fieldnames)
                        if "Категория" not in fieldnames:
                            fieldnames.insert(0, "Категория")

                        # Создаем writer если ещё не создан
                        if writer is None:
                            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                            writer.writeheader()

                        # Записываем строки с добавлением категории
                        for row in reader:
                            if "Категория" not in row:
                                row["Категория"] = category_name
                            writer.writerow(row)
                            total_rows += 1

                    # Добавляем файл в список на удаление (не удаляем сразу!)
                    files_to_delete.append(csv_file)

                self.log(f"Объединение завершено. Всего записей: {total_rows}", "info")

            # После успешной записи во временный файл переименовываем его в целевой
            # Используем shutil.move как fallback для cross-device перемещения
            try:
                temp_output.replace(output_file_path)
            except OSError:
                shutil.move(str(temp_output), str(output_file_path))

            # Удаляем исходные файлы после успешного переименования
            for csv_file in files_to_delete:
                try:
                    csv_file.unlink()
                    self.log(f"Исходный файл удалён: {csv_file.name}", "debug")
                except Exception as e:
                    self.log(f"Не удалось удалить файл {csv_file}: {e}", "warning")

            self.log(
                f"Объединение завершено. Файлы удалены ({len(files_to_delete)} шт.)",
                "info",
            )
            return True

        except Exception as e:
            self.log(f"Ошибка при объединении CSV: {e}", "error")
            # Удаляем временный файл при ошибке
            try:
                if temp_output.exists():
                    temp_output.unlink()
                    self.log("Временный файл удалён после ошибки", "debug")
            except Exception:
                pass
            self.log(
                "Исходные файлы НЕ были удалены (ошибка до завершения объединения)",
                "warning",
            )
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
        start_time = time.time()
        total_tasks = len(self.cities) * len(self.categories)

        self.log(f"🚀 Запуск параллельного парсинга ({self.max_workers} потока)", "info")
        self.log(f'📍 Города: {[c["name"] for c in self.cities]}', "info")
        self.log(f"📑 Категории: {len(self.categories)}", "info")
        self.log(f"📊 Всего задач: {total_tasks}", "info")

        # Генерируем все URL
        all_urls = self.generate_all_urls()

        if not all_urls:
            self.log("❌ Нет URL для парсинга", "error")
            return False

        # Запускаем параллельный парсинг
        success_count = 0
        failed_count = 0
        last_progress_time = time.time()

        # Получаем таймаут из конфигурации (если есть) или используем значение по умолчанию
        timeout_per_url = 300  # Значение по умолчанию: 5 минут на URL
        # Примечание: ParserOptions не имеет атрибута timeout, используем фиксированное значение
        self.log(f"⏱️ Таймаут на один URL: {timeout_per_url} секунд", "info")

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
            for idx, future in enumerate(as_completed(futures), 1):
                url, category_name, city_name = futures[future]

                try:
                    # Получаем результат с таймаутом
                    success, result = future.result(timeout=timeout_per_url)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        self.log(
                            f"❌ Не удалось: {city_name} - {category_name}: {result}",
                            "error",
                        )

                    # Выводим прогресс каждые 3 секунды
                    current_time = time.time()
                    if current_time - last_progress_time >= 3 or idx == len(futures):
                        progress_bar = print_progress(
                            success_count + failed_count,
                            len(futures),
                            prefix="   Прогресс"
                        )
                        self.log(progress_bar, "info")
                        last_progress_time = current_time

                except FuturesTimeoutError:
                    failed_count += 1
                    self.log(
                        f"❌ Таймаут при парсинге {city_name} - {category_name} ({timeout_per_url} сек)",
                        "error",
                    )

                except Exception as e:
                    failed_count += 1
                    self.log(
                        f"❌ Исключение при парсинге {city_name} - {category_name}: {e}",
                        "error",
                    )

        # Вычисляем длительность
        duration = time.time() - start_time
        duration_str = f"{duration:.2f} сек."

        self.log(
            f"🏁 Парсинг завершён. Успешно: {success_count}, Ошибок: {failed_count}",
            "info",
        )

        # Объединяем CSV файлы
        if success_count > 0:
            self.log("📁 Начало объединения результатов...", "info")
            merge_success = self.merge_csv_files(output_file, merge_callback)

            if not merge_success:
                self.log("❌ Не удалось объединить CSV файлы", "error")
                log_parser_finish(
                    success=False,
                    stats={
                        "Городов": len(self.cities),
                        "Категорий": len(self.categories),
                        "Успешно": success_count,
                        "Ошибки": failed_count,
                    },
                    duration=duration_str,
                )
                return False
        else:
            self.log("⚠️ Нет успешных результатов для объединения", "warning")
            log_parser_finish(
                success=False,
                stats={
                    "Городов": len(self.cities),
                    "Категорий": len(self.categories),
                    "Успешно": 0,
                    "Ошибки": failed_count,
                },
                duration=duration_str,
            )
            return False

        # Финальный отчёт
        stats = {
            "Городов": len(self.cities),
            "Категорий": len(self.categories),
            "Всего URL": total_tasks,
            "Успешно": success_count,
            "Ошибки": failed_count,
        }
        log_parser_finish(success=True, stats=stats, duration=duration_str)

        return True

    def stop(self) -> None:
        """Останавливает парсинг."""
        self._cancel_event.set()
        self.log("Получена команда остановки парсинга", "warning")


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

    def run(self) -> None:  # type: ignore[override]
        """Точка входа потока."""
        try:
            # Используем переданный output_file или путь по умолчанию
            output_file = self._output_file or str(
                self.output_dir / "merged_result.csv"
            )
            # Вызываем метод родительского класса ParallelCityParser.run
            self._result = ParallelCityParser.run(self, output_file=output_file)
        except Exception as e:
            logger.error("Ошибка в потоке параллельного парсинга: %s", e, exc_info=True)
            self._result = False

    def get_result(self) -> Optional[bool]:
        """Возвращает результат парсинга."""
        return self._result
