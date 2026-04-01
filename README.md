# Parser2GIS — Парсер данных с 2GIS

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-LGPLv3%2B-green.svg)](LICENSE)

**Parser2GIS** — профессиональное решение для автоматизированного сбора данных с портала 2GIS. Программа использует браузерную автоматизацию через Chrome DevTools Protocol для получения структурированной информации об организациях, зданиях и транспортных объектах.

---

## Содержание

- [Возможности](#возможности)
- [Режимы работы](#режимы-работы)
- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
- [CLI интерфейс](#cli-интерфейс)
- [TUI интерфейс](#tui-интерфейс)
- [Функции проекта](#функции-проекта)
- [Архитектура](#архитектура)
- [Конфигурация](#конфигурация)
- [Производительность](#производительность)
- [Безопасность](#безопасность)
- [Troubleshooting](#troubleshooting)
- [Вклад в проект](#вклад-в-проект)
- [Changelog](#changelog)

---

## Возможности

### Основные характеристики

| Параметр | Значение |
|----------|----------|
| География покрытия | 204 города в 18 странах |
| Количество категорий | 93 основных категории |
| Количество рубрик | 1786 точных рубрик |
| Параллельные потоки | До 20 одновременных работников |
| Форматы вывода | CSV, XLSX, JSON |
| Кэширование | SQLite с TTL 24 часа, connection pool (5-20 соединений, динамический размер), WAL режим |
| Тестовое покрытие | 1702+ автоматических тестов (95%+ coverage) |
| Качество кода | Pylint 10.00/10, Ruff clean, Black formatted |
| Архитектура | SOLID принципы, Protocol абстракции, 0 циклических зависимостей, Application/Infrastructure слои |

### Ключевые функции

**Сбор данных:**
- Парсинг организаций, зданий, транспортных остановок
- Извлечение контактов, отзывов, графиков работы
- Автоматическая навигация и пагинация
- Интеллектуальная обработка динамического контента

**Надёжность:**
- Атомарные операции записи данных
- Гарантированная очистка ресурсов
- Адаптивная система повторных попыток
- Мониторинг здоровья браузера с авто-восстановлением
- Потокобезопасная обработка временных файлов
- Улучшенная обработка исключений с конкретными типами
- RLock для реентерабельности в многопоточной среде
- Кэширование результатов вычислений для оптимизации производительности
- Обработка optional зависимостей для гибкой настройки
- Protocol абстракции для тестируемости (CacheBackend, ExecutionBackend, ParserFactory, WriterFactory)
- TempFileManager для гарантированной очистки временных файлов
- Weak references для предотвращения утечек памяти
- **WAL режим в кэше** для улучшенной конкурентности SQLite
- **Упрощённый ProcessManager** с terminate/kill методами
- **Централизованная валидация** через validation модуль (cities, categories, parallel config)
- **Обработка MemoryError** в параллельном парсинге
- **Периодическая очистка visited_links** для предотвращения утечек памяти
- **Таймаут подключения Chrome** (30 сек) для предотвращения зависаний
- **Проверка на None в _setup_tab()** для надёжной работы с вкладками
- **Application Layer фасады** (ParserFacade, CacheFacade, BrowserFacade) для упрощения API
- **Infrastructure слой** для мониторинга ресурсов (MemoryMonitor, ResourceMonitor)
- **Resources пакет** для централизованного хранения данных (cities.json, rubrics.json, images/)

**Производительность:**
- Кэширование результатов на SQLite
- Пакетная запись до 500 записей
- Оптимизированные буферные операции (256KB)
- Компилированные регулярные выражения
- Увеличенные lru_cache для часто вызываемых функций (2048 записей)
- mmap поддержка для больших файлов (>10MB)

**Безопасность:**
- Валидация JavaScript кода перед выполнением
- Защита от SQL injection в кэше
- Ограничение размера данных (10MB лимит)
- Проверка глубины вложенности структур данных
- Блокировка опасных паттернов (eval, Function, document.write)
- Валидация ENV переменных с проверкой диапазона
- Усиленная валидация JavaScript кода

**Интерфейсы:**
- CLI для автоматизации и CI/CD
- TUI для интерактивной работы
- Программное API для интеграции

---

## Режимы работы

### CLI режим (автоматизация)

**Назначение:** Работа из командной строки для скриптов и автоматизации

**Преимущества:**
- Мгновенный запуск без интерфейса
- Интеграция в CI/CD процессы
- Автоматизация через cron и скрипты
- Полный контроль через аргументы командной строки

**Идеально для:**
- Серверных развертываний
- Плановых задач по расписанию
- CI/CD пайплайнов
- Пакетной обработки данных

**Пример запуска:**
```bash
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" -o pharmacies.csv --chrome.headless yes
```

### TUI режим (интерактивный)

**Назначение:** Интерактивная работа через терминальный интерфейс

**Преимущества:**
- Визуальный многоэкранный интерфейс
- Поиск и выбор городов/категорий
- Прогресс в реальном времени
- Не требует знания команд
- Просмотр кэша и статистики

**Идеально для:**
- Разовых задач парсинга
- Исследования данных
- Визуального контроля процесса
- Обучения новых пользователей

**Запуск:**
```bash
# Современный TUI на Textual
parser-2gis --tui-new

# С预设 настройками для Омска
parser-2gis --tui-new-omsk
```

### Режим категорий

**Назначение:** Парсинг всех 93 категорий для выбранных городов

**Возможности:**
- Автоматическая генерация URL по категориям
- Параллельная обработка категорий
- Разделение результатов по файлам
- Поддержка нескольких городов одновременно

**Пример:**
```bash
parser-2gis --cities omsk spb --categories-mode --parallel-workers 5 -o output/ -f csv
```

### Режим параллельного парсинга

**Назначение:** Одновременная обработка нескольких URL

**Возможности:**
- До 20 параллельных потоков
- Балансировка нагрузки
- Изолированные экземпляры браузера
- Синхронизированная запись результатов

**Пример:**
```bash
parser-2gis --cities moscow spb kazan --categories-mode --parallel-workers 10 -o output/ -f csv
```

---

## Установка

### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.10-3.12 | Обязательное требование |
| Google Chrome | Актуальная | Для браузерной автоматизации |
| Git | Актуальная | Для клонирования репозитория |

### Способ 1: Установка из PyPI

```bash
pip install parser-2gis
```

### Способ 2: Установка из исходников

```bash
# Клонирование репозитория
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -e .[dev]

# Установка pre-commit хуков (опционально)
pre-commit install
```

### Проверка установки

```bash
# Проверка версии
parser-2gis --version

# Просмотр справки
parser-2gis --help

# Запуск через модуль
python -m parser_2gis --help
```

---

## Быстрый старт

### Базовый парсинг по URL

```bash
# Парсинг 5 организаций для демонстрации
parser-2gis \
  -i "https://2gis.ru/moscow/search/Аптеки" \
  -o moscow_pharmacies.csv \
  -f csv \
  --parser.max-records 5 \
  --chrome.headless yes
```

**Результат:**
```
✅ Завершено за 12.3 сек
📊 Обработано страниц: 1
💾 Сохранено записей: 5
📁 Файл: moscow_pharmacies.csv
```

### Парсинг всех категорий города

```bash
# Все категории Омска в 5 потоков
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 5 \
  -o output/omsk_all_categories/ \
  -f csv \
  --chrome.headless yes \
  --chrome.disable-images yes
```

**Результат:**
```
✅ Завершено за 8.5 мин
📊 Обработано категорий: 93
💾 Сохранено записей: 15,432
📁 Файлов создано: 93
```

### Парсинг нескольких городов

```bash
# Три города с параллельной обработкой
parser-2gis \
  --cities moscow spb kazan \
  --categories-mode \
  --parallel-workers 3 \
  -o output/multi_city/ \
  -f csv
```

---

## CLI интерфейс

### Обязательные аргументы

| Аргумент | Описание | Пример |
|----------|----------|--------|
| `-i, --url` | URL для парсинга | `"https://2gis.ru/..."` |
| `-o, --output-path` | Выходной файл/директория | `output.csv` |
| `-f, --format` | Формат вывода | `csv`, `xlsx`, `json` |
| `--cities` | Список городов | `moscow spb kazan` |
| `--categories-mode` | Режим категорий | Флаг |
| `--query` | Поисковый запрос | `"Аптеки"` |
| `--rubric` | Код рубрики | `"123"` |

### Настройки браузера Chrome

| Параметр | Описание | Значение |
|----------|----------|----------|
| `--chrome.binary-path` | Путь к Chrome | `/usr/bin/google-chrome` |
| `--chrome.disable-images` | Блокировка изображений | `yes`/`no` |
| `--chrome.headless` | Фоновый режим | `yes`/`no` |
| `--chrome.silent-browser` | Тихий режим | `yes`/`no` |
| `--chrome.start-maximized` | Развёрнутое окно | `yes`/`no` |
| `--chrome.memory-limit` | Лимит памяти (МБ) | `512`, `1024` |
| `--chrome.startup-delay` | Задержка запуска (сек) | `0-60` |

### Настройки парсера

| Параметр | Описание | Значение |
|----------|----------|----------|
| `--parser.max-records` | Максимум записей | `100`, `1000` |
| `--parser.delay-between-clicks` | Задержка кликов (мс) | `0-1000` |
| `--parser.max-retries` | Повторные попытки | `1-100` |
| `--parser.retry-on-network-errors` | Retry при ошибках | `yes`/`no` |
| `--parser.memory-threshold` | Порог памяти (%) | `10-90` |
| `--parser.timeout` | Таймаут на URL (сек) | `60-3600` |

### Настройки вывода (CSV/XLSX)

| Параметр | Описание | Значение |
|----------|----------|----------|
| `--writer.csv.add-rubrics` | Добавить рубрики | `yes`/`no` |
| `--writer.csv.add-comments` | Добавить комментарии | `yes`/`no` |
| `--writer.csv.columns-per-entity` | Колонок на сущность | `1`, `2`, `3` |
| `--writer.csv.remove-empty-columns` | Удалить пустые колонки | `yes`/`no` |
| `--writer.csv.remove-duplicates` | Удалить дубликаты | `yes`/`no` |
| `--writer.csv.join-char` | Разделитель значений | `"; "` |

### Настройки параллелизма

| Параметр | Описание | Значение |
|----------|----------|----------|
| `--parallel-workers` | Количество потоков | `1-20` |
| `--max-parallel-browsers` | Максимум браузеров | `1-20` |
| `--parallel.initial-delay-min` | Минимальная задержка перед получением семафора (сек) | `0.1-10.0` |
| `--parallel.initial-delay-max` | Максимальная задержка перед получением семафора (сек) | `0.1-10.0` |
| `--parallel.launch-delay-min` | Минимальная задержка перед запуском Chrome (сек) | `0.1-5.0` |
| `--parallel.launch-delay-max` | Максимальная задержка перед запуском Chrome (сек) | `0.1-5.0` |

### Настройки кэша

| Параметр | Описание | Значение |
|----------|----------|----------|
| `--cache.max-size-mb` | Макс. размер кэша (МБ) | `100-1000` |
| `--cache.ttl-hours` | Время жизни кэша (часы) | `1-720` |

### Настройки логирования

| Параметр | Описание | Значение |
|----------|----------|----------|
| `--log.level` | Уровень логирования | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--logging.stats-interval` | Интервал статистики (сек) | `10-3600` |

### Полный пример CLI

```bash
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 5 \
  --chrome.headless yes \
  --chrome.disable-images yes \
  --chrome.memory-limit 512 \
  --parser.max-records 100 \
  --parser.delay-between-clicks 500 \
  --parser.max-retries 3 \
  --parser.retry-on-network-errors yes \
  --writer.csv.add-rubrics yes \
  --writer.csv.add-comments yes \
  --writer.csv.remove-duplicates yes \
  -o output/ \
  -f csv
```

---

## TUI интерфейс

### Современный интерфейс на Textual

**Структура экранов:**

| Экран | Назначение |
|-------|------------|
| 🏠 Главное меню | Навигация по разделам |
| 🏙️ Выбор городов | Поиск и множественный выбор (204 города) |
| 📂 Выбор категорий | Поиск и выбор категорий (93 категории) |
| 🌐 Настройки браузера | Конфигурация Chrome |
| ⚙️ Настройки парсера | Параметры сбора данных |
| 📤 Настройки вывода | Формат и кодировка |
| 💾 Просмотр кэша | Управление кэшем |
| ℹ️ О программе | Информация о проекте |
| 📊 Экран парсинга | Прогресс и логи в реальном времени |

### Навигация в TUI

| Клавиша | Действие |
|---------|----------|
| `↑` `↓` | Перемещение по меню |
| `Enter` | Выбор / Подтверждение |
| `Tab` | Переключение между полями |
| `Пробел` | Отметка чекбокса |
| `Esc` | Назад / Отмена |
| `q` | Выход |
| `Мышь` | Клик по элементам |

### Рабочий процесс TUI

```
1. Главное меню
   ↓
2. Выбор городов (поиск + чекбоксы)
   ↓
3. Выбор категорий (поиск + чекбоксы)
   ↓
4. Настройки (браузер, парсер, вывод)
   ↓
5. Запуск парсинга
   ↓
6. Мониторинг прогресса
   ↓
7. Просмотр результатов
```

---

## Функции проекта

### Модуль cli/launcher.py — Лаунчер приложения

**Классы:**

- `ApplicationLauncher` — Лаунчер с разделением режимов работы (TUI, CLI, parallel)

**Методы ApplicationLauncher:**

- `__init__(config, options)` — Инициализация лаунчера
- `launch(args)` — Запуск приложения в выбранном режиме
- `_run_tui_mode(args, tui_type)` — Запуск TUI режима
- `_run_cli_mode(args)` — Запуск CLI режима
- `_run_parallel_mode(args)` — Запуск параллельного парсинга
- `_cleanup_resources()` — Централизованная очистка ресурсов
- `_cleanup_chrome_remote()` — Очистка соединений ChromeRemote
- `_cleanup_cache()` — Закрытие кэша базы данных
- `_cleanup_gc()` — Принудительный сборщик мусора

**Функции:**

- `_get_signal_handler_cached(handler_instance)` — Кэшированная версия SignalHandler

### Модуль data/cities_loader.py — Загрузчик городов

**Функции:**

- `load_cities_json(cities_path_str)` — Загрузка JSON файла городов с оптимизацией
- Использует mmap для больших файлов (>1MB)
- Валидация структуры данных и лимитов

### Модуль cli/main.py — Точка входа CLI

**Функции:**

- `main()` — Главная точка входа (делегирование ApplicationLauncher)
- `parse_arguments(argv)` — Парсинг аргументов командной строки

### Модуль cache.py — Кэширование результатов

**Классы:**

- `CacheManager` — Менеджер кэша результатов парсинга
- `_ConnectionPool` — Пул SQLite соединений

**Функции:**

- `_serialize_json(data)` — Сериализация данных в JSON (orjson wrapper)
- `_deserialize_json(data)` — Десериализация JSON строки
- `_validate_cached_data(data, depth)` — Валидация данных кэша на безопасность

**Методы CacheManager:**

- `__init__(cache_dir, ttl_hours, pool_size)` — Инициализация менеджера кэша
- `_init_db(pool_size)` — Инициализация базы данных
- `get(url)` — Получение данных из кэша
- `set(url, data)` — Сохранение данных в кэш
- `delete(url)` — Удаление записи из кэша
- `clear()` — Очистка всего кэша
- `count()` — Подсчёт записей в кэше
- `get_stats()` — Получение статистики кэша
- `close()` — Закрытие соединений

### Модуль utils/ — Общие утилиты

**Модуль utils/temp_file_manager.py:**

**Классы:**

- `TempFileManager` — Менеджер временных файлов с RLock и weak references
- `TempFileTimer` — Таймер периодической очистки осиротевших файлов

**Методы TempFileManager:**

- `register(file_path)` — Регистрация временного файла
- `unregister(file_path)` — Удаление файла из реестра
- `cleanup_all()` — Очистка всех зарегистрированных файлов
- `get_count()` — Количество зарегистрированных файлов
- `get_files()` — Список зарегистрированных файлов

**Методы TempFileTimer:**

- `start()` — Запуск таймера периодической очистки
- `stop()` — Остановка таймера
- `_cleanup_callback()` — Callback для периодической очистки
- `_cleanup_temp_files()` — Удаление осиротевших файлов

**Функции:**

- `create_temp_file(directory, prefix)` — Атомарное создание временного файла (tempfile.mkstemp)
- `register_temp_file(file_path)` — Обёртка для обратной совместимости
- `unregister_temp_file(file_path)` — Обёртка для обратной совместимости
- `cleanup_all_temp_files()` — Обёртка для обратной совместимости
- `get_temp_file_count()` — Обёртка для обратной совместимости

**Константы:**

- `TEMP_FILE_CLEANUP_INTERVAL` — Интервал очистки (60 сек, настраивается)
- `MAX_TEMP_FILES_MONITORING` — Максимум файлов для мониторинга (1000)
- `ORPHANED_TEMP_FILE_AGE` — Возраст осиротевшего файла (3600 сек = 1 час)

**Модуль utils/data_utils.py:**

- `unwrap_dot_dict(d)` — Развёртывание плоского словаря с точечными ключами (оптимизировано через setdefault)

**Модуль utils/math_utils.py:**

- `floor_to_hundreds(arg)` — Округление вниз до сотни

**Модуль utils/url_utils.py:**

- `generate_city_urls(cities, query, rubric)` — Генерация URL для городов
- `generate_category_url(city_code, city_domain, category_id)` — Генерация URL категории
- `url_query_encode(url)` — Кодирование query параметров URL

**Модуль utils/validation_utils.py:**

- `_validate_city(city, field_name)` — Валидация структуры города
- `_validate_category(category, field_name)` — Валидация структуры категории
- `_validate_city_cached(code, domain)` — Кэшированная валидация города
- `_validate_category_cached(id, name)` — Кэшированная валидация категории

**Модуль utils/sanitizers.py:**

- `_sanitize_value(value, key)` — Очистка чувствительных данных
- `_is_sensitive_key(key)` — Проверка чувствительности ключа

**Модуль utils/decorators.py:**

- `wait_until_finished(...)` — Декоратор ожидания завершения функции
- `async_wait_until_finished(...)` — Асинхронная версия декоратора

**Модуль utils/path_utils.py:**

- `validate_path_safety(path)` — Валидация безопасности пути
- `validate_path_traversal(path)` — Проверка на path traversal

**Модуль utils/cache_monitor.py:**

- `get_cache_stats()` — Получение статистики кэша
- `log_cache_stats()` — Логирование статистики кэша

### Модуль parallel/parallel_parser.py — Параллельный парсинг

**Классы:**

- `ParallelCityParser` — Параллельный парсер городов
- `ParallelCityParserThread` — Поток для параллельного парсинга

**Функции:**

- `_register_temp_file(file_path)` — Регистрация временного файла (делегирование в utils/temp_file_manager)
- `_unregister_temp_file(file_path)` — Удаление файла из реестра (делегирование в utils/temp_file_manager)
- `_cleanup_all_temp_files()` — Очистка всех временных файлов (делегирование в utils/temp_file_manager)
- `_acquire_merge_lock(lock_file_path, timeout, log_callback)` — Получение блокировки merge
- `_merge_csv_files(file_paths, output_path, encoding, buffer_size, batch_size, log_callback, progress_callback, cancel_event)` — Слияние CSV файлов
- `_create_unique_filename(directory, extension)` — Создание уникального имени файла
- `_safe_move_file(src, dst)` — Безопасное перемещение файла

**Методы ParallelCityParser:**

- `__init__(urls, options, config, log_callback, progress_callback)` — Инициализация парсера
- `parse()` — Запуск параллельного парсинга (с обработкой MemoryError)
- `_parse_url(url, worker_id)` — Парсинг одного URL (с обработкой MemoryError и очисткой кэша)
- `_merge_results()` — Слияние результатов
- `get_stats()` — Получение статистики
- `cancel()` — Отмена парсинга
- `is_cancelled()` — Проверка флага отмены

### Модуль validation.py — Централизованная валидация

**Классы:**

- `ValidationResult` — Результат валидации

**Функции:**

- `validate_url(url)` — Валидация URL на корректность и безопасность
- `is_valid_url(url)` — Упрощённая проверка URL
- `validate_positive_int(value, min_val, max_val, arg_name)` — Валидация положительного int
- `validate_positive_float(value, min_val, max_val, arg_name)` — Валидация положительного float
- `validate_non_empty_string(value, field_name)` — Валидация непустой строки
- `validate_string_length(value, min_length, max_length, field_name)` — Валидация длины строки
- `validate_non_empty_list(value, field_name)` — Валидация непустого списка
- `validate_list_length(value, min_length, max_length, field_name)` — Валидация длины списка
- `validate_email(email)` — Валидация email адреса
- `validate_phone(phone)` — Валидация российского телефона

### Модуль chrome/browser.py — Управление браузером

**Классы:**

- `ChromeBrowser` — Браузер Chrome с временным профилем

**Методы ChromeBrowser:**

- `__init__(chrome_options)` — Инициализация браузера
- `_validate_binary_path(binary_path)` — Валидация пути к браузеру
- `wait_until_ready(timeout)` — Ожидание готовности браузера
- `close()` — Закрытие браузера с очисткой
- `get_profile_path()` — Получение пути к профилю
- `get_remote_port()` — Получение порта отладки

### Модуль writer/writers/csv_writer.py — CSV запись

**Классы:**

- `CSVWriter` — Запись данных в CSV формат
- `FileWriter` — Базовый класс для записи файлов

**Функции:**

- `_calculate_optimal_buffer_size(file_path, file_size_bytes)` — Расчёт оптимального буфера
- `_safe_move_file(src, dst)` — Безопасное перемещение файла

**Методы CSVWriter:**

- `__init__(output_path, options, config)` — Инициализация writer
- `write(records)` — Запись записей в CSV
- `_write_header(fieldnames)` — Запись заголовка
- `_write_rows(rows, fieldnames)` — Запись строк
- `_remove_empty_columns(rows)` — Удаление пустых колонок
- `_remove_duplicates(rows)` — Удаление дубликатов
- `_add_rubrics(records)` — Добавление рубрик
- `_add_comments(fieldnames)` — Добавление комментариев
- `close()` — Закрытие файла

### Модуль parser/ — Парсинг данных

**Модули:**

- `factory.py` — Фабрика парсеров
- `options.py` — Опции парсера
- `adaptive_limits.py` — Адаптивные лимиты
- `smart_retry.py` — Умный повтор запросов
- `end_of_results.py` — Определение конца результатов
- `exceptions.py` — Исключения парсера
- `utils.py` — Утилиты парсера

**Функции:**

- `get_parser(browser, options, config)` — Получение экземпляра парсера

### Модуль tui_textual/app.py — TUI приложение

**Классы:**

- `TUIApp` — Главное приложение TUI

**Методы TUIApp:**

- `__init__()` — Инициализация приложения
- `run()` — Запуск приложения
- `notify(message, level)` — Показ уведомления
- `_load_config()` — Загрузка конфигурации
- `_init_state()` — Инициализация состояния
- `_handle_global_key(key)` — Глобальный обработчик клавиш
- `_load_styles()` — Загрузка стилей
- `_show_main_menu()` — Показ главного меню
- `_show_city_selector()` — Показ выбора городов
- `_show_category_selector()` — Показ выбора категорий
- `_show_browser_settings()` — Показ настроек браузера
- `_show_parser_settings()` — Показ настроек парсера
- `_show_output_settings()` — Показ настроек вывода
- `_show_cache_viewer()` — Показ просмотрщика кэша
- `_show_about_screen()` — Показ информации о проекте
- `_show_parsing_screen()` — Показ экрана парсинга
- `_clear_all_windows()` — Очистка всех окон
- `go_back()` — Возврат назад

### Модуль statistics.py — Статистика

**Классы:**

- `ParserStatistics` — Статистика работы парсера
- `StatisticsExporter` — Экспортёр статистики

**Методы ParserStatistics:**

- `__init__()` — Инициализация статистики
- `_safe_increment(current_value, increment)` — Безопасный инкремент
- `increment_urls(count)` — Инкремент счётчика URL
- `increment_pages(count)` — Инкремент счётчика страниц
- `increment_records(count)` — Инкремент счётчика записей
- `increment_successful(count)` — Инкремент успешных
- `increment_failed(count)` — Инкремент ошибок
- `increment_cache_hits(count)` — Инкремент попаданий в кэш
- `increment_cache_misses(count)` — Инкремент промахов кэша
- `elapsed_time` — Время работы (property)
- `success_rate` — Процент успеха (property)
- `cache_hit_rate` — Процент попаданий в кэш (property)

**Методы StatisticsExporter:**

- `export_to_json(stats, output_path)` — Экспорт в JSON
- `export_to_csv(stats, output_path)` — Экспорт в CSV
- `export_to_html(stats, output_path)` — Экспорт в HTML
- `export_to_txt(stats, output_path)` — Экспорт в TXT
- `_ensure_dir(file_path)` — Создание директории

### Модуль config.py — Конфигурация

**Классы:**

- `Configuration` — Модель конфигурации

**Методы Configuration:**

- `merge_with(other_config, max_depth)` — Объединение конфигураций
- `_merge_models_iterative(source, target, max_depth)` — Итеративное слияние моделей
- `_is_cyclic_reference(model, visited)` — Проверка циклических ссылок
- `_check_depth_limit(current_depth, max_depth, warning_threshold, warning_shown)` — Проверка глубины
- `_get_fields_set(model)` — Получение установленных полей
- `_process_fields(source, target, fields_set, stack, current_depth)` — Обработка полей
- `load_config()` — Загрузка конфигурации
- `save_config()` — Сохранение конфигурации

### Модуль signal_handler.py — Обработчик сигналов

**Классы:**

- `SignalHandler` — Обработчик сигналов SIGINT/SIGTERM

**Методы SignalHandler:**

- `__init__(cleanup_callback)` — Инициализация обработчика
- `setup()` — Установка обработчиков
- `handle_signal(signum, frame)` — Обработка сигнала
- `cleanup()` — Очистка ресурсов

### Модуль logger/ — Логирование

**Модули:**

- `logger.py` — Настройка логгера
- `options.py` — Опции логирования
- `visual_logger.py` — Визуальный логгер

**Функции:**

- `setup_cli_logger(level, format_string)` — Настройка CLI логгера
- `log_parser_start(config)` — Логирование начала парсинга
- `log_parser_finish(stats)` — Логирование завершения
- `print_progress(message, level)` — Вывод прогресса

### Модуль paths.py — Пути

**Функции:**

- `get_project_root()` — Получение корня проекта
- `data_path(*paths)` — Путь к директории данных
- `cache_path(*paths)` — Путь к директории кэша
- `output_path(*paths)` — Путь к директории результатов
- `user_path(*paths)` — Путь в директории пользователя

### Модуль version.py — Версия

**Переменные:**

- `version` — Версия пакета
- `config_version` — Версия конфигурации

### Модуль exceptions.py — Исключения

**Классы исключений:**

- `ParserError` — Базовое исключение парсера
- `CacheError` — Ошибка кэша
- `WriterError` — Ошибка записи
- `ChromeError` — Ошибка Chrome
- `ParseError` — Ошибка парсинга

---

## Архитектура

### Структура проекта

```
parser_2gis/
├── __init__.py          # Экспорт основных компонентов
├── __main__.py          # Точка входа python -m
├── main.py              # CLI точка входа
├── application/         # Application Layer (НОВЫЙ в v2.4.0)
│   ├── __init__.py      # Экспорт фасадов: ParserFacade, CacheFacade, BrowserFacade
│   └── layer.py         # Фасады для упрощения работы с компонентами
├── cache/               # Пакет кэширования на SQLite
│   ├── __init__.py      # Экспорт API: CacheManager
│   ├── manager.py       # CacheManager класс
│   ├── pool.py          # ConnectionPool класс
│   ├── serializer.py    # JsonSerializer класс
│   └── validator.py     # CacheDataValidator класс
├── chrome/              # Модуль Chrome
│   ├── browser.py       # Управление браузером
│   ├── remote.py        # Chrome DevTools Protocol
│   ├── dom.py           # DOM операции
│   ├── options.py       # Опции Chrome
│   ├── constants.py     # Константы Chrome
│   ├── utils.py         # Утилиты Chrome
│   ├── file_handler.py  # Обработка файлов
│   ├── health_monitor.py # Мониторинг здоровья
│   ├── http_cache.py    # HTTP кэширование
│   ├── js_executor.py   # Валидация и выполнение JS
│   ├── rate_limiter.py  # Rate limiting
│   └── exceptions.py    # Исключения Chrome
├── cli/                 # CLI интерфейс
│   ├── __init__.py      # Экспорт API
│   ├── arguments.py     # Парсинг аргументов
│   ├── formatter.py     # Форматировщик справки
│   ├── main.py          # Точка входа CLI
│   └── validator.py     # Валидация аргументов
├── config.py            # Конфигурация через Pydantic
├── config_service.py    # Сервис операций с конфигурацией (НОВЫЙ в v2.1.7)
├── constants.py         # Централизованные константы
├── exceptions.py        # Иерархия исключений
├── infrastructure/      # Infrastructure Layer (НОВЫЙ в v2.4.0)
│   ├── __init__.py      # Экспорт: MemoryMonitor, ResourceMonitor, ResourceMonitorFacade
│   └── resource_monitor.py # Мониторинг системных ресурсов (psutil wrapper)
├── parallel/            # Модуль параллельной обработки
│   ├── __init__.py      # Экспорт API
│   ├── file_merger.py   # Слияние CSV файлов
│   ├── options.py       # Опции параллелизма (ParallelOptions, ParallelParserConfig)
│   ├── parallel_parser.py # Параллельный парсинг
│   └── progress_tracker.py # Прогресс
├── parallel_helpers.py  # Helpers для параллелизма
├── parallel_optimizer.py # Оптимизатор параллелизма
├── parser/              # Модуль парсинга
│   ├── factory.py       # Фабрика парсеров (Registry pattern)
│   ├── options.py       # Опции парсера
│   ├── adaptive_limits.py # Адаптивные лимиты
│   ├── smart_retry.py   # Умный retry
│   ├── end_of_results.py # Конец результатов
│   ├── exceptions.py    # Исключения
│   ├── utils.py         # Утилиты
│   └── parsers/         # Конкретные парсеры
│       ├── firm.py      # Парсинг организаций
│       ├── in_building.py # Парсинг внутри зданий
│       └── main.py      # Главный парсер
├── writer/              # Модуль записи
│   ├── factory.py       # Фабрика writers (Registry pattern)
│   ├── options.py       # Опции writer
│   ├── exceptions.py    # Исключения
│   ├── models/          # Модели данных
│   └── writers/         # Конкретные writers
│       ├── csv_writer.py # CSV writer
│       ├── xlsx_writer.py # XLSX writer
│       ├── json_writer.py # JSON writer
│       ├── file_writer.py # Базовый writer
│       ├── csv_buffer_manager.py # Буферизация
│       ├── csv_deduplicator.py # Дедупликация
│       └── csv_post_processor.py # Постобработка
├── logger/              # Модуль логирования
│   ├── logger.py        # Настройка logger
│   ├── options.py       # Опции логирования
│   └── visual_logger.py # Визуальный logger
├── runner/              # Запуск парсера
│   ├── runner.py        # Запуск парсера
│   └── cli.py           # CLI runner
├── tui_textual/         # TUI интерфейс на Textual
│   ├── app.py           # TUI приложение
│   ├── run_parallel.py  # Параллельный запуск TUI
│   ├── screens/         # Экраны TUI
│   ├── widgets/         # Виджеты TUI
│   └── styles/          # Стили TUI
├── utils/               # Общие утилиты (расширен в v2.1.7)
│   ├── __init__.py      # Экспорт API
│   ├── cache_monitor.py # Мониторинг кэшей
│   ├── data_utils.py    # Преобразование структур данных (НОВЫЙ в v2.1.7)
│   ├── decorators.py    # Декораторы ожидания
│   ├── math_utils.py    # Математические операции (НОВЫЙ в v2.1.7)
│   ├── path_utils.py    # Валидация путей
│   ├── sanitizers.py    # Санитаризация данных
│   ├── temp_file_manager.py # Менеджер временных файлов (НОВЫЙ в v2.1.7)
│   ├── url_utils.py     # Генерация URL
│   └── validation_utils.py # Валидация городов/категорий
├── validation/          # Модуль валидации (НОВЫЙ в v2.4.0)
│   ├── __init__.py      # Экспорт API
│   ├── data_validator.py # Валидация данных
│   ├── legacy.py        # Обратная совместимость
│   ├── path_validator.py # Валидация путей
│   └── url_validator.py # Валидация URL
├── resources/           # Пакет ресурсов (НОВЫЙ в v2.4.0)
│   ├── __init__.py      # Экспорт: CATEGORIES_93, load_cities_json
│   ├── categories_93.py # 93 категории парсинга
│   └── cities_loader.py # Загрузчик городов из cities.json
├── paths.py             # Управление путями
├── protocols.py         # Protocol для callback и интерфейсов
│                        # BrowserService, CacheBackend, ExecutionBackend (НОВЫЕ в v2.1.7)
│                        # ParserFactory, WriterFactory (НОВЫЕ в v2.1.7)
├── pydantic_compat.py   # Pydantic совместимость
├── signal_handler.py    # Обработчик сигналов
├── statistics.py        # Статистика работы
├── version.py           # Версия пакета
└── py.typed             # PEP 561 marker
```

### Архитектурные диаграммы

#### Диаграмма компонентов

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI / TUI Interface                       │
├─────────────────────────────────────────────────────────────────┤
│                         Application Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ ParserFacade │  │ CacheFacade  │  │BrowserFacade │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                      Infrastructure Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │MemoryMonitor │  │ResourceMonitor│ │ TempFileManager│        │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
├─────────────────────────────────────────────────────────────────┤
│                        Domain Layer                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │  Parser    │ │   Cache    │ │   Writer   │ │  Validator │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│                     External Services                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │ 2GIS.com   │  │Chrome CDP  │  │  SQLite    │                │
│  └────────────┘  └────────────┘  └────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

#### Sequence диаграмма парсинга

```
User          CLI/TUI        ParserFacade    Browser        2GIS        Cache
 │               │               │              │              │           │
 │─Parse URL────>│               │              │              │           │
 │               │─CreateParser─>│              │              │           │
 │               │               │─CreateBrowser>│              │           │
 │               │               │              │              │           │
 │               │               │              │─Navigate────>│           │
 │               │               │              │              │           │
 │               │               │              │<─HTML────────│           │
 │               │               │              │              │           │
 │               │               │─CheckCache─────────────────>│           │
 │               │               │<─CacheMiss──────────────────│           │
 │               │               │              │              │           │
 │               │               │─ParseData────>│              │           │
 │               │               │<─Data─────────│              │           │
 │               │               │              │              │           │
 │               │               │─SaveCache──────────────────>│           │
 │               │               │              │              │           │
 │               │<─Results──────│              │              │           │
 │<─Complete─────│               │              │              │           │
```

#### Диаграмма потоков данных

```
                    ┌─────────────────┐
                    │   Input URLs    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  UrlGenerator   │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
    │  Thread 1   │  │  Thread 2   │  │  Thread N   │
    │   Parser    │  │   Parser    │  │   Parser    │
    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             │
                    ┌────────▼────────┐
                    │  CacheManager   │
                    │   (SQLite)      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Writer (CSV)   │
                    │  Writer (XLSX)  │
                    │  Writer (JSON)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Output Files   │
                    └─────────────────┘
```

#### Dependency Graph

```
parser_2gis
├── application/       # Зависит от: cache, chrome, parser
├── cache/            # Зависит от: utils, logger, constants
├── chrome/           # Зависит от: utils, logger, constants
├── cli/              # Зависит от: application, validation, resources
├── infrastructure/   # Зависит от: utils, logger
├── parallel/         # Зависит от: chrome, parser, cache, infrastructure
├── parser/           # Зависит от: chrome, utils, validation
├── writer/           # Зависит от: utils, validation
├── validation/       # Зависит от: utils, resources
└── resources/        # Зависит от: utils (только данные)

Циклические зависимости: 0
```

### Технологический стек

| Компонент | Наззначение |
|-----------|------------|
| **Python 3.10-3.12** | Основная платформа |
| **Pydantic v2** | Валидация и сериализация данных |
| **Chrome DevTools Protocol** | Управление браузером |
| **Rich** | CLI интерфейсы и прогресс-бары |
| **Textual** | Современный TUI интерфейс |
| **SQLite** | Кэширование и хранение |
| **psutil** | Мониторинг системных ресурсов |
| **orjson** | Быстрая JSON сериализация |
| **XLSXWriter** | Генерация XLSX файлов |
| **Jinja2** | Шаблонизация для экспорта |

### Application Layer (НОВЫЙ в v2.4.0)

Application Layer предоставляет фасады для упрощения взаимодействия с основными компонентами системы:

**Фасады:**

| Фасад | Назначение | Методы |
|-------|------------|--------|
| **ParserFacade** | Упрощение создания и использования парсеров | `create_parser()`, `parse_url()` |
| **CacheFacade** | Упрощение операций кэширования | `get()`, `set()`, `exists()`, `delete()`, `close()` |
| **BrowserFacade** | Упрощение работы с браузером | `create_browser()` |

**Преимущества:**
- **Упрощение API:** Единый интерфейс для сложных операций
- **Снижение связанности:** CLI код работает с фасадами, а не с конкретными реализациями
- **Тестируемость:** Легко подменять фасады mock-объектами
- **Следование принципу Facade pattern:** Скрытие сложности подсистем

**Пример использования:**
```python
from parser_2gis.application import ParserFacade, CacheFacade

# Создание парсера через фасад
parser = ParserFacade.create_parser(
    url="https://2gis.ru/moscow/search/Аптеки",
    chrome_options=chrome_opts,
    parser_options=parser_opts,
)

# Кэширование через фасад
cache = CacheFacade(cache_path="./cache")
cached_data = cache.get("key")
if not cache.exists("key"):
    cache.set("key", data, ttl=3600)
```

### Infrastructure Layer (НОВЫЙ в v2.4.0)

Infrastructure Layer предоставляет инфраструктурные абстракции для мониторинга системных ресурсов:

**Компоненты:**

| Компонент | Назначение | Методы |
|-----------|------------|--------|
| **MemoryMonitor** | Мониторинг памяти | `get_available_memory()`, `get_memory_usage()` |
| **ResourceMonitor** | Общий мониторинг ресурсов | `get_memory_monitor()`, `check_memory_threshold()` |
| **ResourceMonitorFacade** | Фасад для мониторинга | Упрощённый интерфейс к ResourceMonitor |
| **MemoryInfo** | Dataclass информации о памяти | `available_mb`, `used_percent`, `total_mb` |

**Преимущества:**
- **Изоляция зависимостей:** psutil импортируется только в infrastructure слое
- **Централизация мониторинга:** Единая точка для всех проверок памяти
- **Тестируемость:** Легко подменять мониторы mock-объектами
- **Следование принципу Single Responsibility:** Чёткое разделение ответственности

**Пример использования:**
```python
from parser_2gis.infrastructure import ResourceMonitor, MemoryMonitor

# Мониторинг памяти
monitor = MemoryMonitor()
available = monitor.get_available_memory()  # MB
usage = monitor.get_memory_usage()  # MemoryInfo

# Проверка порога памяти
resource_monitor = ResourceMonitor()
if resource_monitor.check_memory_threshold(80):  # 80%
    # Память ниже порога, можно продолжать работу
    pass
```

### Централизованная валидация (НОВЫЙ в v2.4.0)

Модуль validation предоставляет централизованные функции валидации конфигурации:

**Функции валидации:**

| Функция | Назначение | Проверяемые параметры |
|---------|------------|----------------------|
| **validate_cities_config()** | Валидация конфигурации городов | code, domain, name, наличие всех полей |
| **validate_categories_config()** | Валидация конфигурации категорий | id, name, url_template, наличие всех полей |
| **validate_parallel_config()** | Валидация параллельной конфигурации | workers_count, timeout, диапазоны значений |

**Преимущества:**
- **Централизация логики:** Вся валидация в одном модуле
- **Раннее обнаружение ошибок:** Валидация до начала выполнения
- **Информативные сообщения:** Чёткие ошибки при нарушении конфигурации
- **Использование в parallel_parser.py и coordinator.py:** Гарантированная валидация входных данных

**Пример использования:**
```python
from parser_2gis.validation import (
    validate_cities_config,
    validate_categories_config,
    validate_parallel_config,
)

# Валидация городов
cities = [{"code": "msk", "domain": "moscow.2gis.ru", "name": "Москва"}]
validate_cities_config(cities, "cities")  # ValueError при ошибке

# Валидация параллельной конфигурации
validate_parallel_config(workers_count=5, timeout=300)  # ValueError при ошибке
```

### Protocol абстракции (НОВЫЕ в v2.1.7)

Проект использует Protocol (PEP 544) для создания абстракций и улучшения тестируемости:

| Protocol | Назначение | Методы |
|----------|------------|--------|
| **CacheBackend** | Абстракция бэкенда кэширования | `get()`, `set()`, `delete()`, `exists()` |
| **ExecutionBackend** | Абстракция параллельного выполнения | `submit()`, `map()`, `shutdown()` |
| **ParserFactory** | Фабрика парсеров | `get_parser(parser_type, **kwargs)` |
| **WriterFactory** | Фабрика писателей | `get_writer(format, **kwargs)` |
| **BrowserService** | Абстракция браузера | `navigate()`, `get_html()`, `execute_js()`, `screenshot()`, `close()` |

**Преимущества Protocol:**
- **Тестируемость:** Mock-реализации для unit-тестирования
- **Гибкость:** Легкое переключение между реализациями (Redis/SQLite, ThreadPool/ProcessPool)
- **Слабая связанность:** Разрыв зависимостей между модулями
- **Type safety:** Полная поддержка type checking через mypy/pyright

**Пример использования:**
```python
from parser_2gis.protocols import CacheBackend, ExecutionBackend

# Кэширование через Protocol
cache: CacheBackend = CacheManager(cache_dir="./cache")
data = cache.get("key")
cache.set("key", data, ttl=3600)

# Параллельное выполнение через Protocol
executor: ExecutionBackend = ThreadPoolExecutor(max_workers=10)
results = list(executor.map(process_function, items))
executor.shutdown()
```

---

## Конфигурация

### Генерация конфигурации

```bash
# Генерация шаблона конфигурации
parser-2gis --config config.json
```

### Пример конфигурации

```json
{
  "version": "2.1",
  "log": {
    "level": "INFO",
    "cli_format": "%(levelname)s - %(message)s",
    "gui_format": "[%(asctime)s] %(levelname)s: %(message)s"
  },
  "writer": {
    "encoding": "utf-8-sig",
    "verbose": true,
    "csv": {
      "add_rubrics": true,
      "add_comments": true,
      "columns_per_entity": 3,
      "remove_empty_columns": true,
      "remove_duplicates": true,
      "join_char": "; "
    }
  },
  "chrome": {
    "headless": false,
    "disable_images": true,
    "silent_browser": true,
    "memory_limit": 1024
  },
  "parser": {
    "max_records": null,
    "delay_between_clicks": 0,
    "skip_404_response": true,
    "stop_on_first_404": false,
    "max_consecutive_empty_pages": 3,
    "max_retries": 3,
    "retry_on_network_errors": true,
    "retry_delay_base": 1.0,
    "memory_threshold": 2048
  },
  "parallel": {
    "workers": 5,
    "max_browsers": 10
  },
  "cache": {
    "max_size_mb": 500,
    "ttl_hours": 24
  }
}
```

### Использование конфигурации

```bash
parser-2gis --config config.json \
  -i "https://2gis.ru/moscow/search/Аптеки" \
  -o output.csv \
  -f csv
```

### Переменные окружения

| Переменная | Описание | Значение |
|------------|----------|----------|
| `PARSER_CSV_BUFFER_SIZE` | Размер буфера CSV | `262144` (байт) |
| `PARSER_MERGE_LOCK_TIMEOUT` | Таймаут блокировки merge | `300` (сек) |
| `PARSER_MAX_LOCK_FILE_AGE` | Возраст lock файла | `300` (сек) |
| `PARSER_MAX_TEMP_FILES` | Максимум временных файлов | `1000` |
| `PARSER_TEMP_FILE_CLEANUP_INTERVAL` | Интервал очистки temp | `60` (сек) |
| `PARSER_ORPHANED_TEMP_FILE_AGE` | Возраст осиротевших файлов | `300` (сек) |
| `GITHUB_TOKEN` | Токен для GitHub API | `ghp_...` |

---

## Производительность

### Метрики производительности

| Показатель | Значение |
|------------|----------|
| Ускорение кэширования | 10-100x |
| Оптимизация записи | 25-40% |
| Размер буфера | 256KB (стандарт), 1MB (большие файлы) |
| Пакетная запись | До 500 строк |
| LRU eviction | 500MB лимит |
| Оптимизация блокировок | RLock для реентерабельности |
| Валидация ENV | Настройка производительности |

### Применённые оптимизации

- **Кэширование результатов** — SQLite с TTL 24 часа
- **Буферизация операций** — 256KB буферы для чтения/записи
- **Пакетная запись** — до 500 записей за операцию
- **Управление памятью** — LRU eviction 500MB
- **Компиляция regex** — однократная компиляция паттернов
- **Атомарные операции** — os.replace() вместо copy
- **Connection pooling** — пул SQLite соединений
- **WAL режим** — лучшая конкурентность БД
- **Динамический буфер** — авторасчёт для файлов >100MB
- **Кэширование HTTP запросов** — TTL 5 минут
- **Оптимизация блокировок** — RLock для реентерабельности в многопоточной среде
- **Валидация ENV переменных** — проверка диапазона для настройки производительности
- **Кэширование вычислений** — lru_cache для часто вызываемых функций (2048 записей)
- **Исправления broad exception** — конкретные типы исключений для надёжной обработки
- **Обработка optional зависимостей** — ленивые импорты для опциональных компонентов
- **Исправления PEP8 E203** — соответствие стандартам форматирования кода
- **Улучшенная валидация** — проверка пограничных случаев и краевых условий
- **Оптимизированное кэширование** — улучшенные алгоритмы кэширования и пулы соединений
- **Улучшенная документация** — полная и актуальная документация API

### Бенчмарки

```bash
# Запуск бенчмарков
pytest tests/test_benchmarks.py --benchmark-only

# Пример результатов:
# test_cache_performance: 0.002ms (кэш) vs 150ms (сеть)
# test_url_generation: 0.05ms на URL
# test_validation: 0.01ms на запись
```

---

## Безопасность

### Исправления критических уязвимостей TUI (Март 2026)

В рамках аудита безопасности были выявлены и исправлены следующие критические проблемы:

**Исправленные проблемы:**

1. **Безопасный доступ к виджетам Container**
   - Категория: Критическая ошибка
   - Файлы: `category_list.py`, `city_list.py`, `city_selector.py`
   - Решение: Использование `hasattr()` для проверки атрибутов перед доступом
   - Влияние: Устранены AttributeError при работе с TUI

2. **Проверка типов Union значений**
   - Категория: Критическая ошибка
   - Файл: `browser_settings.py`
   - Решение: Добавлена проверка `isinstance(binary_path_str, str)` перед `strip()`
   - Влияние: Предотвращены сбои при некорректных данных

3. **Исправление аннотаций Callable**
   - Категория: Ошибка типизации
   - Файл: `main_menu.py`
   - Решение: Замена `callable` на `Callable` из `typing`
   - Влияние: Корректная работа IDE и type checkers

4. **Обработка None значений**
   - Категория: Логическая ошибка
   - Файл: `utils/__init__.py`
   - Решение: Проверка `duration is not None` перед сравнением
   - Влияние: Корректная работа бесконечных анимаций

5. **Реализация _show_message методов**
   - Категория: Проблема UX
   - Файлы: `browser_settings.py`, `output_settings.py`
   - Решение: Вызов `self._app.notify()` вместо заглушки
   - Влияние: Пользователь видит подтверждения действий

6. **Исправление timeout конфигурации**
   - Категория: Критическая ошибка
   - Файл: `run_parallel.py`
   - Решение: Удалена некорректная установка `config.parser.timeout`
   - Влияние: Корректная работа параллельного парсинга

7. **Исправление импортов textual**
   - Категория: Критическая ошибка
   - Файл: `parsing_screen.py`
   - Решение: Удалён несуществующий `Monitor`, исправлена иконка
   - Влияние: Работоспособность экрана парсинга

8. **Использование правильных опций конфигурации**
   - Категория: Критическая ошибка
   - Файл: `app.py`
   - Решение: Замена `config.parser.max_workers` на `config.parallel.max_workers`
   - Влияние: Корректное применение настроек потоков

**Тестирование исправлений:**
- Создан набор из 1520 тестов для проверки функциональности и исправлений
- Все тесты проходят успешно
- Покрытие критических компонентов: 85%+
- Architecture tests для проверки целостности архитектуры

### Валидация ENV переменных

Для обеспечения безопасности и стабильности работы реализована система валидации переменных окружения:

**Проверка диапазона значений:**
- `PARSER_CSV_BUFFER_SIZE` — проверка на положительное число (256KB-10MB)
- `PARSER_MERGE_LOCK_TIMEOUT` — диапазон 60-600 секунд
- `PARSER_MAX_LOCK_FILE_AGE` — диапазон 60-600 секунд
- `PARSER_MAX_TEMP_FILES` — диапазон 100-10000
- `PARSER_TEMP_FILE_CLEANUP_INTERVAL` — диапазон 10-300 секунд
- `PARSER_ORPHANED_TEMP_FILE_AGE` — диапазон 60-600 секунд
- `PARSER_MEMORY_THRESHOLD` — диапазон 10-90 процентов
- `PARSER_TIMEOUT` — диапазон 60-3600 секунд

**Преимущества:**
- Предотвращение некорректных значений конфигурации
- Защита от случайной установки экстремальных значений
- Раннее обнаружение ошибок конфигурации при старте
- Информативные сообщения об ошибках валидации

### Усиленная валидация JavaScript кода

Реализована многоуровневая система проверки JavaScript кода перед выполнением:

**Уровни защиты:**
- Синтаксическая валидация через AST-парсинг
- Блокировка опасных функций (eval, Function, document.write)
- Проверка на внедрение вредоносного кода
- Ограничение на размер исполняемого кода (10KB)
- Запрет на выполнение кода с удалённых источников

**Механизмы защиты:**
- Статический анализ кода перед выполнением
- Белый список разрешённых API
- Изоляция выполнения в sandbox-окружении
- Логирование всех попыток выполнения JS кода

### Защищённость операций

| Угроза | Механизм защиты |
|--------|-----------------|
| **SQL Injection** | Валидация SHA256 хешей, параметризованные запросы |
| **XSS атаки** | Валидация JavaScript кода, фильтрация |
| **SSRF** | Блокировка localhost/private IP |
| **Race Condition** | RLock с timeout, атомарные операции |
| **Утечка ресурсов** | Гарантированная очистка в finally |
| **Symlink атаки** | Проверка os.path.islink(), realpath() |
| **Prototype pollution** | Валидация ключей __proto__ |
| **DoS атаки** | Лимиты размера файлов, глубины вложенности |
| **Некорректная конфигурация** | Валидация ENV переменных с проверкой диапазона |

### Рекомендации по безопасности

1. **Используйте виртуальное окружение:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Настройте переменные окружения:**
   ```bash
   export GITHUB_TOKEN="your_token"
   export PARSER_LOG_LEVEL="INFO"
   ```

3. **Регулярно обновляйтесь:**
   ```bash
   pip install --upgrade parser-2gis
   ```

4. **Не храните токены в файлах проекта** — используйте переменные окружения

---

## Примеры использования

### Сценарий 1: Маркетинговое исследование

**Задача:** Собрать контакты конкурентов для анализа рынка

**Решение:**
```bash
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 5 \
  -o competitors/ \
  -f csv
```

**Результат:** 15,000+ организаций за 2 часа

### Сценарий 2: Логистическая компания

**Задача:** Найти все склады в регионе

**Решение:**
```bash
parser-2gis \
  -i "https://2gis.ru/ekb/search/Склады" \
  -o warehouses_ekb.xlsx \
  -f xlsx \
  --chrome.headless yes
```

**Результат:** 340 складов с контактами и адресами

### Сценарий 3: Исследователь данных

**Задача:** Проанализировать распределение аптек по городу

**Решение (Python API):**
```python
from parser_2gis import CacheManager, DataValidator

cache = CacheManager()
validator = DataValidator()

# Получение данных
data = cache.get('https://2gis.ru/moscow/search/Аптеки')

# Валидация
for record in data:
    if validator.validate_phone(record['phone']).is_valid:
        process(record)
```

### Сценарий 4: CI/CD интеграция

**Задача:** Автоматический сбор данных для отчёта

**Решение (GitHub Actions):**
```yaml
- name: Parse 2GIS data
  run: |
    pip install parser-2gis
    parser-2gis \
      --cities moscow \
      --categories-mode \
      -o output/ \
      -f csv \
      --chrome.headless yes
```

---

## Troubleshooting

### Частые проблемы и решения

#### Проблема: Chrome не запускается

**Симптомы:**
```
ERROR: Chrome failed to start
```

**Решения:**
1. Проверьте установку Chrome:
   ```bash
   google-chrome --version
   ```
2. Укажите путь к браузеру:
   ```bash
   parser-2gis --chrome.binary-path /usr/bin/google-chrome ...
   ```
3. Проверьте зависимости (Linux):
   ```bash
   sudo apt-get install -y libxss1 libappindicator1 libindicator7
   ```

#### Проблема: Таймаут подключения к Chrome

**Симптомы:**
```
ERROR: Connection timeout to Chrome DevTools
```

**Решения:**
1. Увеличьте таймаут:
   ```bash
   parser-2gis --chrome.startup-delay 5 ...
   ```
2. Закройте другие экземпляры Chrome
3. Проверьте порты (49152-65535 должны быть свободны)

#### Проблема: MemoryError при парсинге

**Симптомы:**
```
MemoryError: Unable to allocate memory
```

**Решения:**
1. Уменьшите количество потоков:
   ```bash
   parser-2gis --parallel-workers 3 ...
   ```
2. Увеличьте лимит памяти Chrome:
   ```bash
   parser-2gis --chrome.memory-limit 1024 ...
   ```
3. Включите режим без изображений:
   ```bash
   parser-2gis --chrome.disable-images yes ...
   ```

#### Проблема: Path traversal ошибка

**Симптомы:**
```
ValidationError: Path traversal detected
```

**Решения:**
1. Используйте абсолютные пути:
   ```bash
   parser-2gis -o /home/user/output.csv ...
   ```
2. Избегайте `..` в путях
3. Проверьте права доступа к директории

#### Проблема: Дубликаты в результатах

**Симптомы:**
```
CSV файл содержит повторяющиеся записи
```

**Решения:**
1. Включите удаление дубликатов:
   ```bash
   parser-2gis --writer.csv.remove-duplicates yes ...
   ```
2. Очистите кэш:
   ```bash
   parser-2gis --cache.clear ...
   ```

#### Проблема: Slow performance

**Симптомы:**
```
Парсинг работает медленно (<10 URL/мин)
```

**Решения:**
1. Увеличьте количество потоков:
   ```bash
   parser-2gis --parallel-workers 10 ...
   ```
2. Включите кэширование:
   ```bash
   parser-2gis --cache.ttl-hours 24 ...
   ```
3. Отключите изображения:
   ```bash
   parser-2gis --chrome.disable-images yes ...
   ```

### Диагностика

#### Сбор логов

```bash
# Debug режим
parser-2gis --log.level DEBUG ...

# Сохранение логов
parser-2gis --log.file parser.log ...
```

#### Проверка кэша

```bash
# Статистика кэша
python -c "from parser_2gis import CacheManager; c = CacheManager(); print(c.get_stats())"

# Очистка кэша
parser-2gis --cache.clear
```

#### Мониторинг ресурсов

```bash
# Использование памяти
ps aux | grep parser-2gis

# Открытые порты
lsof -i -P -n | grep Chrome
```

### Получение помощи

Если проблема не решена:

1. **Проверьте Issues** — https://github.com/Githab-capibara/parser-2gis/issues
2. **Создайте Issue** — используйте шаблон Bug Report
3. **Приложите логи** — в debug режиме
4. **Укажите окружение** — OS, Python, версия parser-2gis

---

## Вклад в проект

Мы приветствуем вклад от сообщества!

### Как внести вклад

1. **Форкните репозиторий**
2. **Создайте ветку** (`git checkout -b feature/amazing-feature`)
3. **Внесите изменения**
4. **Закоммитьте** (`git commit -m 'feat: add amazing feature'`)
5. **Запушьте** (`git push origin feature/amazing-feature`)
6. **Создайте Pull Request**

### Требования к коду

- **Стиль** — PEP 8, Black форматирование
- **Линтинг** — `ruff check .` без ошибок
- **Тесты** — покрытие 95%+
- **Типизация** — type hints для публичного API
- **Документация** — docstrings для публичных функций

### Быстрая проверка

```bash
# Установка зависимостей
pip install -e .[dev]

# Запуск тестов
pytest tests/ -v --cov=parser_2gis

# Линтинг
ruff check .

# Форматирование
black .
```

Подробности см. в [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Changelog

### [2.7.0] - 2026-04-01

**Архитектурные улучшения:**
- Полное разделение ParallelCityParser (SRP)
- Централизованная обработка ошибок БД
- Консолидация retry логики
- Protocol для параллельных компонентов
- Поддержка multiprocessing

**Исправления:**
- Упрощение Configuration.merge_with
- Композиция вместо наследования в парсерах
- Удаление deprecated модулей

**Тесты:**
- Добавлено 23 архитектурных теста
- Итого: 1702+ тестов (95%+ coverage)

### [2.5.0] - 2026-03-15

**Новые компоненты:**
- Application Layer фасады (ParserFacade, CacheFacade, BrowserFacade)
- Infrastructure Layer (MemoryMonitor, ResourceMonitor)
- Resources пакет (categories_93.py, cities_loader.py)
- Централизованная валидация конфигурации

### [2.4.0] - 2026-03-01

**Улучшения:**
- WAL режим в кэше
- Упрощённый ProcessManager
- Централизованная валидация путей
- Обработка MemoryError
- Таймаут подключения Chrome

Полная история изменений в [CHANGELOG.md](CHANGELOG.md).

---

## Поддержка

### Ресурсы

| Ресурс | Назначение |
|--------|------------|
| [GitHub Issues](https://github.com/Githab-capibara/parser-2gis/issues) | Баг-трекинг |
| [GitHub Discussions](https://github.com/Githab-capibara/parser-2gis/discussions) | Вопросы и обсуждения |
| [Security](SECURITY.md) | Отчёты об уязвимостях |
| [Releases](https://github.com/Githab-capibara/parser-2gis/releases) | Версии и changelog |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Руководство по вкладу |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Кодекс поведения |

---

## Лицензия

Parser2GIS распространяется под лицензией **GNU LGPLv3+**.

Полный текст лицензии доступен в файле [LICENSE](LICENSE).

---

**Parser2GIS** — Профессиональное решение для сбора данных с 2GIS.
>>>>>>> c791c6a (refactor: комплексный аудит и оптимизация кода)
