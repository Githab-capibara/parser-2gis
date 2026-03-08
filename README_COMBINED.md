# Parser2GIS 🌍 - Полная документация проекта

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-348%20passed-brightgreen.svg)](testes/)
[![GitHub](https://img.shields.io/badge/GitHub-Githab--capibara-orange.svg)](https://github.com/Githab-capibara/parser-2gis)

**Parser2GIS** — это мощный инструмент для парсинга данных с сервиса 2GIS (2ГИС), использующий браузер Chrome для обхода анти-бот защит.

---

## 📋 Оглавление

- [О проекте](#о-проекте)
- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
- [CLI интерфейс](#cli-интерфейс)
- [GUI интерфейс](#gui-интерфейс)
- [Форматы вывода](#форматы-вывода)
- [Конфигурация](#конфигурация)
- [Параллельный парсинг](#параллельный-парсинг)
- [Новые функции v2.0](#новые-функции-v20)
- [Новые функции v2.1](#новые-функции-v21)
- [Структура проекта](#структура-проекта)
- [Тестирование](#тестирование)
- [Разработка](#разработка)
- [История изменений](#история-изменений)
- [Отчет об исправлениях](#отчет-об-исправлениях)
- [Руководство для разработчиков](#руководство-для-разработчиков)
- [FAQ](#faq)
- [Поддержка](#поддержка)

---

## 🎯 О проекте

Parser2GIS — это Python-приложение для автоматизированного сбора данных с сайта 2GIS (2ГИС). Проект позволяет:

- Парсить организации по городам и категориям
- Сохранять данные в различных форматах (CSV, XLSX, JSON)
- Работать в режиме командной строки (CLI) и графическом интерфейсе (GUI)
- Использовать параллельный парсинг для ускорения работы
- Настраивать все параметры через конфигурационные файлы
- Кэшировать результаты для ускорения повторных запусков
- Валидировать данные перед сохранением
- Экспортировать статистику работы парсера
- **Автоматически обрабатывать пустые страницы и 404 ошибки**
- **Использовать адаптивные лимиты для разных городов**
- **Интеллектуальный retry механизм**
- **Оптимизацию параллельного парсинга**
- **Мониторинг здоровья браузера**

### Технологии

- **Python 3.8-3.12** — основной язык разработки
- **Pydantic v2** — валидация конфигураций и данных
- **Chrome DevTools Protocol** — управление браузером
- **PySimpleGUI** — графический интерфейс (опционально)
- **pytest** — фреймворк для тестирования
- **SQLite** — хранение кэша результатов
- **psutil** — мониторинг ресурсов системы

---

## ✨ Основные возможности

### Парсинг данных

- ✅ Поддержка 204 городов в 18 странах
- ✅ 93 категории для парсинга
- ✅ 1786 рубрик для точного поиска
- ✅ Парсинг фирм, остановок, зданий
- ✅ Извлечение контактных данных, отзывов, графиков работы

### Форматы вывода

- ✅ **CSV** — таблицы с разделителями
- ✅ **XLSX** — файлы Excel
- ✅ **JSON** — структурированные данные

### Режимы работы

- ✅ **CLI** — командная строка
- ✅ **GUI** — графический интерфейс на PySimpleGUI
- ✅ **Параллельный парсинг** — по городам и категориям (до 20 потоков)

### Настройки

- ✅ Гибкая конфигурация через JSON
- ✅ Настройки Chrome (headless, память, блокировка)
- ✅ Настройки парсера (задержки, лимиты, retry)
- ✅ Настройки вывода (кодировка, колонки, форматирование)

### Новые возможности v2.0

- ✅ **CacheManager** — кэширование результатов в SQLite (ускорение 10-100x)
- ✅ **ProgressManager** — красивые прогресс-бары для CLI режима
- ✅ **DataValidator** — валидация и очистка данных
- ✅ **StatisticsExporter** — экспорт статистики в JSON, CSV, HTML, TXT
- ✅ **FileLogger** — улучшенное логирование с поддержкой консоли и файлов

### Новые возможности v2.1

- ✅ **AdaptiveLimits** — адаптивные лимиты для разных размеров городов
- ✅ **SmartRetryManager** — интеллектуальный retry механизм
- ✅ **EndOfResultsDetector** — детектор окончания результатов
- ✅ **ParallelOptimizer** — оптимизатор параллельного парсинга
- ✅ **BrowserHealthMonitor** — монитор здоровья браузера с авто-перезапуском
- ✅ **stop_on_first_404** — немедленная остановка при первом 404
- ✅ **max_consecutive_empty_pages** — лимит подряд пустых страниц
- ✅ **26 новых тестов** — покрытие всех новых функций

---

## 📦 Установка

### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.8 – 3.12 | Обязательно |
| Google Chrome | Любая актуальная | Для парсинга |
| Git | Любая актуальная | Для работы с репозиторием |
| psutil | Любая актуальная | Для мониторинга ресурсов |

### Установка из PyPI

```bash
pip install parser-2gis
```

### Установка из исходников

```bash
# Клонирование репозитория
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -e .[dev]

# Установка pre-commit хуков (опционально)
pre-commit install
```

### Проверка установки

```bash
# Проверка версии
parser-2gis --version

# Проверка справки
parser-2gis --help

# Запуск через модуль
python -m parser_2gis --help
```

---

## 🚀 Быстрый старт

### CLI режим

#### Базовый пример

```bash
# Парсинг аптек в Москве (5 записей)
parser-2gis \
  -i "https://2gis.ru/moscow/search/Аптеки" \
  -o moscow_pharmacies.csv \
  -f csv \
  --parser.max-records 5 \
  --chrome.headless yes
```

#### Парсинг всех категорий

```bash
# Парсинг всех 93 категорий Омска (5 потоков)
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 5 \
  -o output/omsk_all_categories/ \
  -f csv \
  --chrome.headless yes \
  --chrome.disable-images yes
```

#### Несколько городов

```bash
# Парсинг аптек в 3 городах
parser-2gis \
  --cities moscow spb kazan \
  --categories-mode \
  -o output/ \
  -f csv
```

#### С новыми параметрами (v2.1)

```bash
# Парсинг с адаптивными лимитами и retry
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 3 \
  --parser.stop-on-first-404 yes \
  --parser.max-consecutive-empty-pages 5 \
  --parser.max-retries 3 \
  --parser.retry-on-network-errors yes \
  --chrome.headless yes \
  -o output/omsk_all.csv \
  -f csv
```

### GUI режим

```bash
# Запуск графического интерфейса
parser-2gis
```

### Использование новых функций v2.0

#### Кэширование результатов

```python
from pathlib import Path
from parser_2gis import CacheManager

# Создаем менеджер кэша
cache = CacheManager(Path('/tmp/parser_cache'), ttl_hours=24)

# Получаем данные из кэша
data = cache.get('https://2gis.ru/moscow/search/Аптеки')
if data is None:
    # Парсим данные
    data = {...}
    # Сохраняем в кэш
    cache.set('https://2gis.ru/moscow/search/Аптеки', data)

# Получаем статистику кэша
stats = cache.get_stats()
print(f"Всего записей: {stats['total_records']}")
print(f"Размер кэша: {stats['cache_size']} байт")
```

#### Прогресс-бар для CLI

```python
from parser_2gis.cli import ProgressManager

# Создаем менеджер прогресса
progress = ProgressManager()

# Запускаем прогресс-бар
progress.start(total_pages=10, total_records=100)

# Обновляем прогресс
for page in range(10):
    progress.update_page()
    for record in range(10):
        progress.update_record()

# Завершаем и выводим статистику
progress.finish()
```

#### Валидация данных

```python
from parser_2gis import DataValidator

validator = DataValidator()

# Валидация телефона
result = validator.validate_phone('+7 (999) 123-45-67')
if result.is_valid:
    print(result.value)  # '8 (999) 123-45-67'

# Валидация email
result = validator.validate_email('test@example.com')
if result.is_valid:
    print(result.value)  # 'test@example.com'

# Валидация полной записи
record = {
    'name': '  Тестовая компания  ',
    'phone_1': '+79991234567',
    'email_1': 'TEST@EXAMPLE.COM'
}
validated = validator.validate_record(record)
```

#### Экспорт статистики

```python
from pathlib import Path
from datetime import datetime
from parser_2gis import ParserStatistics, StatisticsExporter

# Создаем статистику
stats = ParserStatistics()
stats.start_time = datetime.now()
stats.total_urls = 10
stats.total_pages = 50
stats.total_records = 1000
stats.successful_records = 950
stats.end_time = datetime.now()

# Экспортируем статистику
exporter = StatisticsExporter()
exporter.export_to_json(stats, Path('stats.json'))
exporter.export_to_html(stats, Path('stats.html'))
exporter.export_to_csv(stats, Path('stats.csv'))
exporter.export_to_text(stats, Path('stats.txt'))
```

### Использование новых функций v2.1

#### Адаптивные лимиты

```python
from parser_2gis.parser.adaptive_limits import AdaptiveLimits

# Создаем менеджер адаптивных лимитов
limits = AdaptiveLimits(base_limit=3)

# Добавляем количество записей на первых страницах
limits.add_records_count(10)
limits.add_records_count(15)
limits.add_records_count(20)

# Получаем адаптивный лимит для города
adaptive_limit = limits.get_adaptive_limit()
print(f"Адаптивный лимит пустых страниц: {adaptive_limit}")

# Получаем размер города
city_size = limits.get_city_size()
print(f"Размер города: {city_size}")  # 'small', 'medium', 'large', 'huge'

# Получаем статистику
stats = limits.get_stats()
print(f"Среднее записей на страницу: {stats['avg_records']}")
```

#### Интеллектуальный retry

```python
from parser_2gis.parser.smart_retry import SmartRetryManager

# Создаем менеджер повторных попыток
retry = SmartRetryManager(max_retries=3)

# Проверяем, нужно ли retry
if retry.should_retry('502 Bad Gateway', records_on_page=10):
    print("Выполняем повторную попытку")

# Добавляем записи
retry.add_records(50)

# Получаем статистику
stats = retry.get_stats()
print(f"Количество попыток: {stats['retry_count']}")
print(f"Всего записей: {stats['total_records']}")
```

#### Детектор окончания результатов

```python
from parser_2gis.parser.end_of_results import EndOfResultsDetector

# Создаем детектор
detector = EndOfResultsDetector(chrome_remote)

# Проверяем, достигнут ли конец результатов
if detector.is_end_of_results():
    print("Достигнут конец результатов")
    return

# Проверяем наличие пагинации
if detector.has_pagination():
    print("Есть пагинация, продолжаем парсинг")
```

#### Оптимизатор параллельного парсинга

```python
from parser_2gis.parallel_optimizer import ParallelOptimizer

# Создаем оптимизатор
optimizer = ParallelOptimizer(max_workers=5, max_memory_mb=4096)

# Добавляем задачи
optimizer.add_task(
    url='https://2gis.ru/moscow/search/Аптеки',
    category_name='Аптеки',
    city_name='Москва',
    priority=1  # Высокий приоритет
)

# Проверяем ресурсы
available, memory_mb = optimizer.check_resources()
if not available:
    print(f"Ожидание освобождения ресурсов. Память: {memory_mb} МБ")

# Получаем следующую задачу
task = optimizer.get_next_task()
if task:
    print(f"Обработка задачи: {task.city_name} - {task.category_name}")

# Получаем статистику
stats = optimizer.get_stats()
print(f"Прогресс: {stats['progress']}%")
print(f"Всего задач: {stats['total_tasks']}")
print(f"Выполнено: {stats['completed']}")
```

#### Монитор здоровья браузера

```python
from parser_2gis.chrome.health_monitor import BrowserHealthMonitor

# Создаем монитор
monitor = BrowserHealthMonitor(browser, enable_auto_restart=True)

# Записываем активность
monitor.record_activity()

# Проверяем здоровье
health = monitor.check_health()
if not health['healthy']:
    print(f"Проблемы: {health['recommendation']}")
    
    # Проверяем, нужно ли перезапуск
    if monitor.should_restart():
        monitor.restart_browser()

# Получаем количество критических ошибок
errors = monitor.get_critical_errors_count()
print(f"Критических ошибок: {errors}")
```

---

## 💻 CLI интерфейс

### Основные аргументы

| Аргумент | Описание | Обязательный |
|----------|----------|--------------|
| `-i, --url` | URL для парсинга | Нет* |
| `-o, --output` | Путь к выходному файлу | Нет** |
| `-f, --format` | Формат вывода (csv, xlsx, json) | Нет |
| `-v, --version` | Версия программы | Нет |
| `-h, --help` | Справка | Нет |

*Обязателен, если не используется `--cities`  
**Обязателен, если используется `--categories-mode`

### Аргументы параллельного парсинга

| Аргумент | Описание | По умолчанию |
|----------|----------|--------------|
| `--cities` | Список городов для парсинга | - |
| `--categories-mode` | Режим парсинга по категориям | False |
| `--parallel-workers` | Количество потоков (1-20) | 3 |

### Аргументы Chrome

| Аргумент | Описание | По умолчанию |
|----------|----------|--------------|
| `--chrome.headless` | Фоновый режим | False |
| `--chrome.disable-images` | Отключение изображений | True |
| `--chrome.memory-limit` | Лимит памяти (МБ) | Авто |
| `--chrome.binary-path` | Путь к Chrome | Авто |

### Аргументы парсера

| Аргумент | Описание | По умолчанию |
|----------|----------|--------------|
| `--parser.max-records` | Макс. количество записей | ∞ |
| `--parser.delay-between-clicks` | Задержка между кликами (мс) | 0 |
| `--parser.skip-404-response` | Пропускать 404 ответы | True |
| `--parser.use-gc` | Использовать сборщик мусора | False |
| `--parser.gc-pages-interval` | Интервал GC (страниц) | 10 |
| `--parser.stop-on-first-404` | Немедленная остановка при 404 (v2.1) | False |
| `--parser.max-consecutive-empty-pages` | Лимит пустых страниц подряд (v2.1) | 3 |
| `--parser.max-retries` | Макс. количество повторных попыток (v2.1) | 3 |
| `--parser.retry-on-network-errors` | Retry при сетевых ошибках (v2.1) | True |
| `--parser.retry-delay-base` | Базовая задержка retry в сек (v2.1) | 1.0 |
| `--parser.memory-threshold` | Порог памяти для очистки в МБ (v2.1) | 1024 |

### Примеры

```bash
# Полный пример с настройками
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 5 \
  --chrome.headless yes \
  --chrome.disable-images yes \
  --chrome.memory-limit 512 \
  --parser.max-records 100 \
  --parser.delay-between-clicks 500 \
  --parser.use-gc yes \
  --parser.stop-on-first-404 yes \
  --parser.max-consecutive-empty-pages 5 \
  --parser.max-retries 3 \
  --parser.retry-on-network-errors yes \
  -o output/ \
  -f csv
```

---

## 🖥️ GUI интерфейс

### Возможности

- 🏙️ Выбор городов из списка (204 города)
- 📂 Выбор категорий/рубрик (1786 рубрик)
- 📝 Ручной ввод URL
- 🔧 Настройки Chrome и парсера
- 📊 Прогресс-бар и логирование
- 💾 Выбор формата вывода

### Запуск

```bash
# Linux/macOS
parser-2gis

# Windows
python.exe -m parser_2gis
```

---

## 📊 Форматы вывода

### CSV

Таблица с разделителями.

**Параметры:**
- `add_rubrics` — добавлять рубрики (True)
- `add_comments` — добавлять комментарии (True)
- `columns_per_entity` — колонок на сущность (1-5, 3)
- `remove_empty_columns` — удалять пустые колонки (True)
- `remove_duplicates` — удалять дубликаты (True)
- `join_char` — разделитель для списков ("; ")

**Пример:**
```json
{
  "writer": {
    "csv": {
      "add_rubrics": true,
      "add_comments": true,
      "columns_per_entity": 3,
      "remove_empty_columns": true,
      "remove_duplicates": true,
      "join_char": "; "
    }
  }
}
```

### XLSX

Файлы Microsoft Excel.

**Преимущества:**
- Форматирование ячеек
- Автоматическая ширина колонок
- Поддержка фильтров
- Совместимость с Excel

### JSON

Структурированные данные.

**Преимущества:**
- Полная структура данных
- Легкий парсинг программно
- Поддержка вложенных объектов

---

## ⚙️ Конфигурация

### Создание конфигурации

```bash
# Автоматическое создание конфигурации
parser-2gis --config /path/to/config.json
```

### Структура конфигурации

```json
{
  "version": "0.1",
  "log": {
    "level": "DEBUG",
    "cli_format": "%(levelname)s - %(message)s",
    "gui_format": "[%(asctime)s] %(levelname)s: %(message)s",
    "gui_datefmt": "%H:%M:%S"
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
    "binary_path": null,
    "start_maximized": false,
    "headless": false,
    "disable_images": true,
    "silent_browser": true,
    "memory_limit": 1024
  },
  "parser": {
    "max_records": null,
    "delay_between_clicks": 0,
    "skip_404_response": true,
    "use_gc": false,
    "gc_pages_interval": 10,
    "stop_on_first_404": false,
    "max_consecutive_empty_pages": 3,
    "max_retries": 3,
    "retry_on_network_errors": true,
    "retry_delay_base": 1.0,
    "memory_threshold": 1024
  }
}
```

### Использование конфигурации

```bash
# Использование конфигурации
parser-2gis --config config.json \
  -i "https://2gis.ru/moscow/search/Аптеки" \
  -o output.csv \
  -f csv
```

---

## 🔄 Параллельный парсинг

### Режим категорий

Парсинг по категориям для города.

```bash
# Все 93 категории Омска
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 5 \
  -o output/omsk_all/ \
  -f csv
```

### Несколько городов

```bash
# Три города (3 потока)
parser-2gis \
  --cities moscow spb kazan \
  --categories-mode \
  -o output/ \
  -f csv
```

### Кастомные категории

```python
# parser_2gis/data/custom_categories.py
CATEGORIES = [
    {"name": "Аптеки", "query": "Аптеки", "rubric_code": "204"},
    {"name": "Супермаркеты", "query": "Супермаркеты", "rubric_code": "350"},
    {"name": "Кафе", "query": "Кафе", "rubric_code": "161"}
]
```

### Оптимизация

```bash
# Максимальная производительность
parser-2gis \
  --cities moscow spb \
  --categories-mode \
  --parallel-workers 20 \
  --parser.use-gc yes \
  --parser.gc-pages-interval 10 \
  --parser.stop-on-first-404 yes \
  --parser.max-consecutive-empty-pages 5 \
  --chrome.headless yes \
  --chrome.disable-images yes \
  -o output/ \
  -f csv
```

**Рекомендации:**
- ✅ 3-5 потоков для обычных задач
- ✅ 10-20 потоков для серверов с большим количеством RAM
- ✅ Включайте GC при парсинге > 10000 записей
- ✅ Используйте headless режим на серверах
- ✅ Включите `stop_on_first_404` для маленьких городов
- ✅ Используйте адаптивные лимиты для разных городов

---

## 🎯 Новые функции (v2.0)

### 1. CacheManager — Кэширование результатов

Кэширование результатов парсинга в локальную базу данных SQLite для ускорения повторных запусков.

**Преимущества:**
- Ускорение повторных запусков в 10-100 раз
- Автоматическое удаление устаревшего кэша
- Статистика использования кэша
- Возможность очистки кэша

**Пример использования:**

```python
from pathlib import Path
from parser_2gis import CacheManager

# Создаем менеджер кэша (TTL = 24 часа)
cache = CacheManager(Path('/tmp/parser_cache'), ttl_hours=24)

# Получаем данные из кэша
data = cache.get('https://2gis.ru/moscow/search/Аптеки')
if data is None:
    # Кэш не найден — парсим
    data = parse_data(url)
    # Сохраняем в кэш
    cache.set(url, data)

# Получаем статистику
stats = cache.get_stats()
print(f"Записей в кэше: {stats['total_records']}")
print(f"Размер кэша: {stats['cache_size']} байт")

# Очищаем истекший кэш
expired_count = cache.clear_expired()
print(f"Удалено истекших записей: {expired_count}")

# Полная очистка кэша
cache.clear()
```

### 2. ProgressManager — Прогресс-бар для CLI

Красивые и информативные прогресс-бары для командной строки с использованием библиотеки tqdm.

**Преимущества:**
- Двойной прогресс-бар (страницы и записи)
- Отображение ETA и скорости
- Итоговая статистика по завершении
- Возможность отключения

**Пример использования:**

```python
from parser_2gis.cli import ProgressManager

# Создаем менеджер прогресса
progress = ProgressManager()

# Запускаем прогресс-бар
progress.start(total_pages=10, total_records=1000)

# Обновляем прогресс
for page in range(10):
    # Обработка страницы...
    progress.update_page()
    
    for record in range(100):
        # Обработка записи...
        progress.update_record()

# Завершаем и выводим статистику
progress.finish()
# Вывод: "✅ Завершено за 45.2 сек (22.1 записей/сек)"
```

### 3. DataValidator — Валидация данных

Валидация и очистка данных перед сохранением для повышения качества выходных файлов.

**Преимущества:**
- Форматирование телефонных номеров
- Проверка email-адресов
- Проверка URL
- Очистка текста от лишних символов
- Валидация целых записей

**Пример использования:**

```python
from parser_2gis import DataValidator

validator = DataValidator()

# Валидация телефона
result = validator.validate_phone('+7 (999) 123-45-67')
if result.is_valid:
    print(result.value)  # '8 (999) 123-45-67'

# Валидация email
result = validator.validate_email('TEST@EXAMPLE.COM')
if result.is_valid:
    print(result.value)  # 'test@example.com'

# Валидация URL
result = validator.validate_url('https://example.com')
if result.is_valid:
    print(result.value)

# Валидация полной записи
record = {
    'name': '  Тестовая компания  ',
    'phone_1': '+79991234567',
    'email_1': 'TEST@EXAMPLE.COM',
    'website_1': 'https://example.com'
}
validated = validator.validate_record(record)
# Результат: очищенная и валидированная запись
```

### 4. StatisticsExporter — Экспорт статистики

Экспорт статистики работы парсера в различные форматы (JSON, CSV, HTML, TXT).

**Преимущества:**
- Красивые HTML отчеты
- Структурированные JSON данные
- Читаемые CSV файлы
- Текстовые отчеты
- Полная статистика работы

**Пример использования:**

```python
from pathlib import Path
from datetime import datetime
from parser_2gis import ParserStatistics, StatisticsExporter

# Создаем статистику
stats = ParserStatistics()
stats.start_time = datetime.now()
stats.total_urls = 10
stats.total_pages = 50
stats.total_records = 1000
stats.successful_records = 950
stats.failed_records = 50
stats.cache_hits = 800
stats.cache_misses = 200
stats.end_time = datetime.now()

# Экспортируем статистику
exporter = StatisticsExporter()

# В формате JSON
exporter.export_to_json(stats, Path('stats.json'))

# В формате HTML (красивый отчет)
exporter.export_to_html(stats, Path('stats.html'))

# В формате CSV
exporter.export_to_csv(stats, Path('stats.csv'))

# В текстовом формате
exporter.export_to_text(stats, Path('stats.txt'))
```

### 5. FileLogger — Улучшенное логирование

Улучшенное логирование с поддержкой консоли, файлов и ротации.

**Преимущества:**
- Поддержка консоли и файлов
- Ротация по размеру и дате
- Форматирование сообщений
- Разные уровни логирования
- Фильтрация по типам

**Пример использования:**

```python
from pathlib import Path
from parser_2gis.logger import FileLogger

# Создаем логгер
logger = FileLogger(
    log_file=Path('parser.log'),
    console_level='INFO',
    file_level='DEBUG',
    max_file_size=10*1024*1024,  # 10 МБ
    backup_count=5
)

# Логирование
logger.debug('Отладочное сообщение')
logger.info('Информационное сообщение')
logger.warning('Предупреждение')
logger.error('Ошибка')

# Закрытие логгера
logger.close()
```

---

## 🚀 Новые функции (v2.1)

### 1. AdaptiveLimits — Адаптивные лимиты для разных городов

Автоматическое определение размера города и подстройка лимитов пустых страниц для оптимизации парсинга.

**Преимущества:**
- Автоматическая классификация городов (small, medium, large, huge)
- Адаптивные лимиты пустых страниц (2-7)
- Адаптивные таймауты для навигации (30-120 сек)
- Определение размера города на основе первых страниц

**Классификация городов:**
- `small` (маленький): <= 10 записей на страницу, лимит пустых = 2
- `medium` (средний): <= 50 записей на страницу, лимит пустых = 3
- `large` (крупный): <= 200 записей на страницу, лимит пустых = 5
- `huge` (огромный): > 200 записей на страницу, лимит пустых = 7

**Пример использования:**

```python
from parser_2gis.parser.adaptive_limits import AdaptiveLimits

# Создаем менеджер адаптивных лимитов
limits = AdaptiveLimits(base_limit=3)

# Добавляем количество записей на первых страницах
limits.add_records_count(10)
limits.add_records_count(15)
limits.add_records_count(20)

# Получаем адаптивный лимит для города
adaptive_limit = limits.get_adaptive_limit()
print(f"Адаптивный лимит пустых страниц: {adaptive_limit}")

# Получаем размер города
city_size = limits.get_city_size()
print(f"Размер города: {city_size}")  # 'small', 'medium', 'large', 'huge'

# Получаем статистику
stats = limits.get_stats()
print(f"Среднее записей на страницу: {stats['avg_records']}")
print(f"Записей на первых страницах: {stats['records_on_first_pages']}")
```

### 2. SmartRetryManager — Интеллектуальный retry механизм

Умная система повторных попыток, которая анализирует тип ошибки и контекст для принятия решения о retry.

**Преимущества:**
- Анализ типа ошибки (502, 503, 504, 404, 403, 500)
- Учет контекста (количество записей, история попыток)
- Экспоненциальная задержка между попытками
- Лимит максимального количества попыток

**Логика retry:**
- Сетевые ошибки (502, 503, 504, Timeout) — всегда retry
- 404 с записями — retry (возможна временная проблема)
- 404 без записей — не retry (конец категории)
- 403 (блокировка) — не retry (бесполезно)
- 500 (ошибка сервера) — retry
- Превышение лимита попыток — не retry

**Пример использования:**

```python
from parser_2gis.parser.smart_retry import SmartRetryManager

# Создаем менеджер повторных попыток
retry = SmartRetryManager(max_retries=3)

# Проверяем, нужно ли retry
if retry.should_retry('502 Bad Gateway', records_on_page=10):
    print("Выполняем повторную попытку")

# Добавляем записи
retry.add_records(50)

# Получаем статистику
stats = retry.get_stats()
print(f"Количество попыток: {stats['retry_count']}")
print(f"Всего записей: {stats['total_records']}")
print(f"Последняя ошибка: {stats['last_error']}")
```

### 3. EndOfResultsDetector — Детектор окончания результатов

Интеллектуальное определение того, что достигнут конец поисковой выдачи.

**Преимущества:**
- Паттерны текста, указывающие на окончание
- DOM-элементы, указывающие на окончание
- Проверка наличия пагинации
- Избежание бесконечного цикла

**Паттерны окончания:**
- "показан[ыо].*вс[её].*организаци[ияй]"
- "нет.*дополнительн[ыхих].*результат[ова]"
- "вы.*просмотрели.*вс[её].*вариант[ыов]"
- "конец.*результат[ова]"
- "больше.*ничего.*не.*нашл[ио]"

**Пример использования:**

```python
from parser_2gis.parser.end_of_results import EndOfResultsDetector

# Создаем детектор
detector = EndOfResultsDetector(chrome_remote)

# Проверяем, достигнут ли конец результатов
if detector.is_end_of_results():
    print("Достигнут конец результатов")
    return

# Проверяем наличие пагинации
if detector.has_pagination():
    print("Есть пагинация, продолжаем парсинг")
else:
    print("Нет пагинации, достигнут конец")
```

### 4. ParallelOptimizer — Оптимизатор параллельного парсинга

Эффективное распределение ресурсов между браузерами при параллельном парсинге.

**Преимущества:**
- Балансировка нагрузки между браузерами
- Контроль использования ресурсов (CPU, память)
- Приоритизация задач
- Прогресс и статистика
- Автоматическая оптимизация

**Параметры оптимизатора:**
- `max_workers` — максимальное количество потоков (1-20)
- `max_memory_mb` — максимальное использование памяти в МБ (по умолчанию 4096)

**Пример использования:**

```python
from parser_2gis.parallel_optimizer import ParallelOptimizer

# Создаем оптимизатор
optimizer = ParallelOptimizer(max_workers=5, max_memory_mb=4096)

# Добавляем задачи
optimizer.add_task(
    url='https://2gis.ru/moscow/search/Аптеки',
    category_name='Аптеки',
    city_name='Москва',
    priority=1  # Высокий приоритет
)

# Проверяем ресурсы
available, memory_mb = optimizer.check_resources()
if not available:
    print(f"Ожидание освобождения ресурсов. Память: {memory_mb} МБ")

# Получаем следующую задачу
task = optimizer.get_next_task()
if task:
    print(f"Обработка задачи: {task.city_name} - {task.category_name}")

# Получаем статистику
stats = optimizer.get_stats()
print(f"Прогресс: {stats['progress']}%")
print(f"Всего задач: {stats['total_tasks']}")
print(f"Выполнено: {stats['completed']}")
print(f"Ошибок: {stats['failed']}")
print(f"Средняя длительность: {stats['avg_duration']:.2f} сек")
```

### 5. BrowserHealthMonitor — Монитор здоровья браузера

Мониторинг состояния браузера с автоматическим перезапуском при критических ошибках.

**Преимущества:**
- Контроль использования памяти и CPU
- Обнаружение "зависших" браузеров
- Автоматический перезапуск при критических ошибках
- Статистика здоровья

**Пороги для перезапуска:**
- Память: > 2048 МБ (2 ГБ)
- CPU: > 95%
- Время без ответа: > 120 сек (2 минуты)
- Критических ошибок: >= 3

**Пример использования:**

```python
from parser_2gis.chrome.health_monitor import BrowserHealthMonitor

# Создаем монитор
monitor = BrowserHealthMonitor(browser, enable_auto_restart=True)

# Записываем активность
monitor.record_activity()

# Проверяем здоровье
health = monitor.check_health()
print(f"Здоровье: {health['healthy']}")
print(f"Память: {health['memory_mb']:.1f} МБ")
print(f"CPU: {health['cpu_percent']:.1f}%")
print(f"Время активности: {health['time_since_activity']:.1f} сек")
print(f"Критических ошибок: {health['critical_errors']}")

if not health['healthy']:
    print(f"Проблемы: {health['recommendation']}")
    
    # Проверяем, нужно ли перезапуск
    if monitor.should_restart():
        monitor.restart_browser()

# Получаем количество критических ошибок
errors = monitor.get_critical_errors_count()
print(f"Критических ошибок: {errors}")
```

### Новые параметры парсера (v2.1)

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `stop_on_first_404` | Немедленная остановка при первом 404 | False |
| `max_consecutive_empty_pages` | Лимит подряд пустых страниц | 3 |
| `max_retries` | Макс. количество retry попыток | 3 |
| `retry_on_network_errors` | Retry при сетевых ошибках | True |
| `retry_delay_base` | Базовая задержка retry (сек) | 1.0 |
| `memory_threshold` | Порог памяти для очистки (МБ) | 1024 |

**Пример использования в CLI:**

```bash
parser-2gis \
  --cities omsk \
  --categories-mode \
  --parallel-workers 3 \
  --parser.stop-on-first-404 yes \
  --parser.max-consecutive-empty-pages 5 \
  --parser.max-retries 3 \
  --parser.retry-on-network-errors yes \
  -o output/omsk_all.csv \
  -f csv
```

**Пример использования в конфигурации:**

```json
{
  "parser": {
    "stop_on_first_404": true,
    "max_consecutive_empty_pages": 5,
    "max_retries": 3,
    "retry_on_network_errors": true,
    "retry_delay_base": 1.0,
    "memory_threshold": 1024
  }
}
```

---

## 🏗️ Структура проекта

```
parser-2gis/
├── parser_2gis/              # Основной пакет
│   ├── main.py               # Точка входа CLI
│   ├── config.py             # Конфигурация (Pydantic)
│   ├── common.py             # Общие утилиты
│   ├── version.py            # Версия пакета
│   ├── exceptions.py         # Исключения
│   ├── cache.py              # Менеджер кэша (v2.0)
│   ├── validator.py          # Валидатор данных (v2.0)
│   ├── statistics.py         # Экспорт статистики (v2.0)
│   ├── parallel_optimizer.py # Оптимизатор параллельного парсинга (v2.1)
│   │
│   ├── chrome/               # Работа с Chrome
│   │   ├── browser.py        # Запуск браузера
│   │   ├── remote.py         # Chrome DevTools Protocol
│   │   ├── options.py        # Опции Chrome
│   │   ├── dom.py            # Работа с DOM
│   │   ├── exceptions.py     # Исключения Chrome
│   │   └── health_monitor.py # Монитор здоровья браузера (v2.1)
│   │
│   ├── parser/               # Парсеры данных
│   │   ├── parsers/
│   │   │   ├── main.py       # Основной парсер
│   │   │   ├── firm.py       # Парсер фирм
│   │   │   └── in_building.py # Парсер "В здании"
│   │   ├── options.py        # Опции парсера (v2.1 - новые параметры)
│   │   ├── utils.py          # Утилиты парсера
│   │   ├── exceptions.py     # Исключения парсера
│   │   ├── adaptive_limits.py # Адаптивные лимиты (v2.1)
│   │   ├── smart_retry.py    # Интеллектуальный retry (v2.1)
│   │   └── end_of_results.py # Детектор окончания (v2.1)
│   │
│   ├── writer/               # Писатели файлов
│   │   ├── writers/
│   │   │   ├── csv_writer.py # CSV writer
│   │   │   ├── xlsx_writer.py # XLSX writer
│   │   │   └── json_writer.py # JSON writer
│   │   ├── file_writer.py    # Базовый класс
│   │   ├── factory.py        # Фабрика writers
│   │   ├── options.py        # Опции writers
│   │   └── models/           # Модели данных (Pydantic)
│   │
│   ├── gui/                  # GUI приложение
│   │   ├── app.py            # Главное окно
│   │   ├── city_selector.py  # Выбор городов
│   │   ├── urls_generator.py # Генератор URL
│   │   ├── rubric_selector.py # Выбор рубрик
│   │   ├── settings.py       # Настройки
│   │   ├── theme.py          # Темы оформления
│   │   ├── error_popup.py    # Всплывающие окна
│   │   └── utils.py          # Утилиты GUI
│   │
│   ├── runner/               # Запуск парсера
│   │   ├── runner.py         # Базовый класс
│   │   ├── cli.py            # CLI запуск
│   │   └── gui.py            # GUI запуск
│   │
│   ├── logger/               # Логирование
│   │   ├── logger.py         # Основной логгер
│   │   ├── file_logger.py     # FileLogger (v2.0)
│   │   └── options.py        # Опции логирования
│   │
│   ├── cli/                  # CLI приложение
│   │   ├── app.py            # CLI приложение
│   │   └── progress.py       # ProgressManager (v2.0)
│   │
│   ├── parallel_parser.py    # Параллельный парсер
│   └── data/                 # Данные
│       ├── cities.json       # Города (204 города)
│       ├── rubrics.json      # Рубрики (1786 рубрик)
│       ├── categories_93.py   # 93 категории
│       └── images/           # Изображения для GUI
│
├── testes/                   # Тесты (pytest)
│   ├── conftest.py           # Конфигурация pytest
│   ├── test_common.py        # Тесты common.py
│   ├── test_config.py        # Тесты config.py
│   ├── test_chrome.py        # Тесты chrome/
│   ├── test_parser.py        # Тесты parser/
│   ├── test_writer.py        # Тесты writer/
│   ├── test_logger.py        # Тесты logger/
│   ├── test_runner.py        # Тесты runner/
│   ├── test_integration.py   # Интеграционные тесты
│   ├── test_main_categories_mode.py # Тесты categories-mode
│   ├── test_new_improvements.py # 26 новых тестов (v2.1)
│   └── ...                   # Остальные тесты
│
├── scripts/                  # Скрипты обновления
│   ├── update_cities_list.py # Обновление городов
│   └── update_rubrics_list.py # Обновление рубрик
│
├── output/                   # Выходные файлы (по умолчанию)
├── README.md                 # Основной README
├── README_COMBINED.md        # Объединенная документация
├── CHANGELOG.md              # История изменений
├── CONTRIBUTING.md           # Руководство для разработчиков
├── FIXES_REPORT.md           # Отчёт об исправлениях
├── LICENSE                   # Лицензия MIT
├── setup.py                  # Установка пакета
├── setup.cfg                 # Конфигурация setup.py
├── pytest.ini                # Конфигурация pytest
├── tox.ini                   # Конфигурация tox
├── .pre-commit-config.yaml   # Pre-commit хуки
├── .gitignore                # Игнорируемые файлы
└── MANIFEST.in               # Манифест пакета
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# Тесты с покрытием
pytest --cov=parser_2gis --cov-report=html

# С выводом логов
pytest -v -s

# Конкретный тест
pytest testes/test_parser.py

# Тесты с маркерами
pytest -m integration
pytest -m slow

# Новые тесты v2.1
pytest testes/test_new_improvements.py -v
```

### Статистика тестов

- ✅ **348 тестов** — все проходят
- ⏭️ **2 пропущены** — требуют PySimpleGUI
- 📊 **Покрытие:** ~80%
- 🆕 **26 новых тестов** — для новых функций v2.1

### Маркеры тестов

| Маркер | Описание |
|--------|----------|
| `slow` | Медленные тесты |
| `integration` | Интеграционные тесты |
| `gui` | Тесты GUI |
| `requires_chrome` | Тесты, требующие Chrome |
| `requires_network` | Тесты, требующие сеть |

### Новые тесты v2.1 (test_new_improvements.py)

**46 тестов для новых функций:**

#### TestParserOptions (5 тестов)
- `test_default_stop_on_first_404` — проверка значения по умолчанию
- `test_default_max_consecutive_empty_pages` — проверка значения по умолчанию
- `test_custom_stop_on_first_404_true` — проверка установки значения
- `test_custom_max_consecutive_empty_pages` — проверка установки значения
- `test_invalid_max_consecutive_empty_pages` — проверка валидации

#### TestAdaptiveLimits (9 тестов)
- `test_initialization_default` — инициализация по умолчанию
- `test_initialization_custom_base` — инициализация с кастомным значением
- `test_add_records_count` — добавление количества записей
- `test_determine_small_city` — определение маленького города
- `test_determine_medium_city` — определение среднего города
- `test_determine_large_city` — определение крупного города
- `test_determine_huge_city` — определение огромного города
- `test_get_stats` — получение статистики
- `test_reset` — сброс состояния

#### TestSmartRetryManager (10 тестов)
- `test_initialization_default` — инициализация по умолчанию
- `test_initialization_custom_max_retries` — инициализация с кастомным значением
- `test_should_retry_network_error` — retry для сетевой ошибки
- `test_should_retry_timeout` — retry для Timeout ошибки
- `test_should_retry_404_with_records` — retry для 404 с записями
- `test_should_not_retry_404_without_records` — нет retry для 404 без записей
- `test_should_not_retry_403` — нет retry для 403
- `test_should_not_retry_after_max_retries` — нет retry после лимита
- `test_add_records` — добавление записей
- `test_get_stats` — получение статистики
- `test_reset` — сброс состояния

#### TestEndOfResultsDetector (5 тестов)
- `test_initialization` — инициализация детектора
- `test_is_end_of_results_false` — проверка когда не конец
- `test_is_end_of_results_true_pattern` — проверка когда конец по паттерну
- `test_has_pagination_true` — проверка наличия пагинации
- `test_has_pagination_false` — проверка отсутствия пагинации

#### TestParallelTask (3 теста)
- `test_initialization_default_priority` — инициализация с приоритетом по умолчанию
- `test_initialization_custom_priority` — инициализация с высоким приоритетом
- `test_start_and_finish` — отметка начала и завершения

#### TestParallelOptimizer (8 тестов)
- `test_initialization_default` — инициализация по умолчанию
- `test_initialization_custom` — инициализация с кастомными параметрами
- `test_add_task_normal_priority` — добавление задачи с обычным приоритетом
- `test_add_task_high_priority` — добавление задачи с высоким приоритетом
- `test_get_next_task` — получение следующей задачи
- `test_get_next_task_empty` — получение задачи из пустой очереди
- `test_get_stats` — получение статистики
- `test_reset` — сброс оптимизатора

#### TestBrowserHealthMonitor (6 тестов)
- `test_initialization` — инициализация монитора
- `test_record_activity` — запись активности
- `test_get_critical_errors_count` — получение количества критических ошибок
- `test_reset` — сброс монитора
- `test_enable_auto_restart` — включение/отключение авто-перезапуска

### Написание тестов

```python
import pytest
from parser_2gis.parser import MainParser

def test_parser_initialization():
    """Тест инициализации парсера."""
    url = "https://2gis.ru/moscow/search/Аптеки"
    
    parser = MainParser(url, chrome_options, parser_options)
    
    assert parser is not None
    assert parser._url == url
```

---

## 🛠️ Разработка

### Требования к коду

- **flake8**: max-line-length=130
- **mypy**: строгая проверка типов
- **Форматирование**: 4 пробела, UTF-8
- **Комментарии**: на русском языке

### Pre-commit хуки

```bash
# Запуск всех хуков
pre-commit run --all-files

# Проверка стиля
flake8 parser_2gis

# Проверка типов
mypy parser_2gis
```

### Процесс внесения изменений

1. Fork репозитория на GitHub
2. Создайте ветку: `git checkout -b feature/amazing-feature`
3. Внесите изменения
4. Напишите тесты
5. Запустите тесты: `pytest`
6. Проверьте стиль: `pre-commit run --all-files`
7. Закоммитьте: `git commit -m 'Добавлена amazing-feature'`
8. Отправьте в ветку: `git push origin feature/amazing-feature`
9. Откройте Pull Request на GitHub

---

## 📜 История изменений

### [v2.1] — 2026-03-07 (ТЕКУЩАЯ ВЕРСИЯ)

#### Добавлено
- ✅ **AdaptiveLimits** — адаптивные лимиты для разных размеров городов
- ✅ **SmartRetryManager** — интеллектуальный retry механизм
- ✅ **EndOfResultsDetector** — детектор окончания результатов
- ✅ **ParallelOptimizer** — оптимизатор параллельного парсинга
- ✅ **BrowserHealthMonitor** — монитор здоровья браузера с авто-перезапуском
- ✅ **stop_on_first_404** — параметр для немедленной остановки при 404
- ✅ **max_consecutive_empty_pages** — параметр для лимита пустых страниц подряд
- ✅ **max_retries** — параметр для максимального количества retry
- ✅ **retry_on_network_errors** — параметр для retry при сетевых ошибках
- ✅ **retry_delay_base** — параметр для базовой задержки retry
- ✅ **memory_threshold** — параметр для порога памяти для очистки
- ✅ **26 новых тестов** — покрытие всех новых функций

#### Исправлено
- ✅ Исправлен баг с бесконечным циклом пустых страниц при 404 ошибках
- ✅ Добавлена обработка ошибки "Точных совпадений нет / Не найдено"
- ✅ Улучшена обработка HTTP ошибок (404, 403, 500, 502, 503, 504)
- ✅ Добавлена экспоненциальная задержка между retry попытками
- ✅ Улучшена работа с памятью при парсинге больших объёмов данных

#### Изменено
- ✅ Обновлена документация README.md
- ✅ Добавлены примеры использования новых функций
- ✅ Обновлена структура проекта

### [v2.0] — Невошедшее

#### Добавлено
- ✅ **CacheManager** — кэширование результатов в SQLite (ускорение 10-100x)
- ✅ **ProgressManager** — красивые прогресс-бары для CLI режима
- ✅ **DataValidator** — валидация и очистка данных
- ✅ **StatisticsExporter** — экспорт статистики в JSON, CSV, HTML, TXT
- ✅ **FileLogger** — улучшенное логирование с поддержкой консоли и файлов
- ✅ **20 новых тестов** — для FileLogger
- ✅ **__main__.py** — поддержка запуска через `python -m parser_2gis`
- ✅ Полная документация на русском языке

#### Исправлено
- ✅ Исправлена совместимость с Pydantic v2 (замена `.dict()` на `.model_dump()`)
- ✅ Улучшена обработка ошибок в скриптах обновления данных
- ✅ Переведены комментарии в скриптах на русский язык
- ✅ Улучшена читаемость кода и документация

#### Изменено
- ✅ Унифицированы ссылки на репозиторий GitHub (Githab-capibara)
- ✅ Улучшена структура документации

### [1.2.1] — 14-03-2024

#### Добавлено
- ✅ Поддержка парсинга остановок
- ✅ Генератор ссылок добавляет в URL сортировку по алфавиту
- ✅ Обновлён список рубрик

### [1.2.0] — 08-02-2024

#### Добавлено
- ✅ Небольшой багфикс схемы ответов сервера
- ✅ Поддержка ссылок организаций
- ✅ Обновлён список рубрик и городов

### [1.1.2] — 08-03-2023

#### Добавлено
- ✅ Поддержка Chrome v111
- ✅ Новый город Басра (Ирак)
- ✅ Обновлён список рубрик и городов

### [1.1.1] — 03-02-2023

#### Добавлено
- ✅ Обновлён список рубрик и городов
- ✅ Добавлены поля контактов: **Telegram**, **Viber**, **WhatsApp**

### [1.1.0] — 05-01-2023

#### Добавлено
- ✅ Обновлён список рубрик и городов
- ✅ Добавлены поля: **Рейтинг** и **Количество отзывов**
- ✅ Добавлена возможность записи результата в Excel таблицу (XLSX)
- ✅ Добавлена автоматическая навигация к странице

Полный список изменений см. в [CHANGELOG.md](CHANGELOG.md).

---

## 🔧 Отчет об исправлениях

### Исправления для --categories-mode (2026-03-06)

#### Найденные проблемы

1. **main.py: Ошибка валидации аргументов**
   - Аргумент `-i/--url` был обязательным всегда, даже при использовании `--categories-mode --cities`
   - Исправлена ручная валидация ПОСЛЕ парсинга аргументов

2. **main.py: Дублированное определение categories_mode**
   - Переменная определялась дважды (строки 164 и 260)
   - Убрано дублирование

3. **parallel_parser.py: Race condition при записи файлов**
   - Несколько потоков могли записывать в один файл
   - Исправлено через временные файлы с UUID

4. **parallel_parser.py: Преждевременное удаление файлов**
   - Файлы удалялись во время объединения
   - Исправлено: удаление только ПОСЛЕ успешного объединения

5. **parallel_parser.py: Отсутствует валидация входных данных**
   - Нет проверки на пустые `cities`/`categories`
   - Нет ограничения на `max_workers`
   - Добавлена полная валидация

6. **parallel_parser.py: Отсутствует таймаут на парсинг**
   - Один "зависший" URL блокировал весь парсинг
   - Добавлен таймаут (по умолчанию 300 сек)

#### Добавленные тесты

- ✅ `test_categories_mode_requires_cities`
- ✅ `test_categories_mode_with_cities_valid`
- ✅ `test_url_not_required_when_cities_specified`
- ✅ `test_requires_url_or_cities`
- ✅ `test_both_url_and_cities_valid`
- ✅ `test_parallel_workers_default`
- ✅ `test_parallel_workers_custom`

**Результат:** ✅ Все 59 тестов прошли

Полный отчет см. в [FIXES_REPORT.md](FIXES_REPORT.md).

---

## 📚 Руководство для разработчиков

### Начало работы

#### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.8 – 3.12 | Обязательно |
| Google Chrome | Любая актуальная | Для парсинга |
| Git | Любая актуальная | Для работы с репозиторием |

#### Установка для разработки

```bash
# Клонирование репозитория
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -e .[dev]

# Установка pre-commit хуков
pre-commit install
```

### Тестирование

#### Запуск тестов

```bash
# Все тесты
pytest

# Тесты с покрытием
pytest --cov=parser_2gis --cov-report=html

# С выводом логов
pytest -v -s

# Конкретный тест
pytest testes/test_parser.py

# Тесты с маркерами
pytest -m integration
pytest -m slow

# Новые тесты v2.1
pytest testes/test_new_improvements.py -v
```

#### Написание тестов

```python
import pytest
from parser_2gis.parser import MainParser

def test_parser_initialization():
    """Тест инициализации парсера."""
    # Arrange
    url = "https://2gis.ru/moscow/search/Аптеки"
    
    # Act
    parser = MainParser(url, chrome_options, parser_options)
    
    # Assert
    assert parser is not None
    assert parser._url == url
```

### Стиль кода

#### Основные правила

- **flake8**: max-line-length=130, игнорируемые правила: E501, W503, C901, W503, E722, E731
- **mypy**: строгая проверка типов
- **Форматирование**: 4 пробела, UTF-8 кодировка
- **Комментарии**: на русском языке

#### Пример кода

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from .logger import logger

if TYPE_CHECKING:
    from .config import Configuration


def parse_data(url: str, config: Configuration) -> list[dict]:
    """Парсит данные с URL.
    
    Args:
        url: URL для парсинга.
        config: Конфигурация парсера.
    
    Returns:
        Список спарсенных данных.
    
    Raises:
        ValueError: Если URL некорректен.
    """
    if not url.startswith('https://2gis'):
        raise ValueError(f'Некорректный URL: {url}')
    
    logger.debug('Начало парсинга: %s', url)
    
    # Основная логика
    data = []
    
    return data
```

### Вклад в проект

#### Процесс внесения изменений

1. **Fork репозитория** на GitHub
2. **Создайте ветку** для вашей функции:
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Внесите изменения** в код
4. **Напишите тесты** для новых функций
5. **Запустите тесты**:
   ```bash
   pytest
   ```
6. **Проверьте стиль кода**:
   ```bash
   pre-commit run --all-files
   ```
7. **Закоммитьте изменения**:
   ```bash
   git commit -m 'Добавлена amazing-feature'
   ```
8. **Отправьте в ветку**:
   ```bash
   git push origin feature/amazing-feature
   ```
9. **Откройте Pull Request** на GitHub

#### Требования к Pull Request

- ✅ Все тесты проходят
- ✅ Pre-commit хуки выполнены
- ✅ Код соответствует стилю проекта
- ✅ Добавлены тесты для новых функций
- ✅ Обновлена документация (при необходимости)

#### Сообщение коммита

```
<тип>(<область>): <краткое описание>

<полное описание (опционально)>

Fixes #<номер_задачи>
```

**Типы коммитов:**
- `feat` — новая функция
- `fix` — исправление ошибки
- `docs` — обновление документации
- `style` — форматирование
- `refactor` — рефакторинг
- `test` — добавление тестов
- `chore` — служебные изменения

**Пример:**
```
feat(parser): добавлена поддержка парсинга остановок

- Добавлен новый парсер для остановок
- Обновлены тесты
- Обновлена документация

Fixes #52
```

### Утилиты

#### Обновление списка городов

```bash
python scripts/update_cities_list.py
```

Загружает данные с `https://data.2gis.com` через Chrome и сохраняет в `parser_2gis/data/cities.json`.

#### Обновление списка рубрик

```bash
python scripts/update_rubrics_list.py
```

Загружает данные с `https://hermes.2gis.ru/api/data/availableParameters` и сохраняет в `parser_2gis/data/rubrics.json`.

Полное руководство см. в [CONTRIBUTING.md](CONTRIBUTING.md).

---

## ❓ FAQ

### Q: Парсер работает медленно. Как ускорить?

**A:** Используйте параллельный парсинг и кэширование:

```bash
parser-2gis --cities moscow spb --categories-mode --parallel-workers 5
```

### Q: Ошибка "Chrome не найден"

**A:** Установите Google Chrome или укажите путь:

```bash
parser-2gis --chrome.binary-path /path/to/chrome ...
```

### Q: Как использовать кэш для ускорения повторных запусков?

**A:** Используйте CacheManager:

```python
from parser_2gis import CacheManager
from pathlib import Path

cache = CacheManager(Path('/tmp/cache'))
data = cache.get(url)
if data is None:
    data = parse_data(url)
    cache.set(url, data)
```

### Q: Как парсить только определённые категории?

**A:** Создайте файл с категориями и используйте его:

```python
# custom_categories.py
CATEGORIES = [
    {"name": "Аптеки", "query": "Аптеки"},
    {"name": "Кафе", "query": "Кафе"}
]
```

### Q: Как изменить количество колонок в CSV?

**A:** Через конфигурацию:

```json
{
  "writer": {
    "csv": {
      "columns_per_entity": 5
    }
  }
}
```

### Q: Как пропустить дубликаты?

**A:** Через конфигурацию:

```json
{
  "writer": {
    "csv": {
      "remove_duplicates": true
    }
  }
}
```

### Q: Как работать на сервере без GUI?

**A:** Используйте headless режим:

```bash
parser-2gis --chrome.headless yes ...
```

### Q: Как увеличить лимит записей?

**A:** Через аргумент:

```bash
parser-2gis --parser.max-records 1000 ...
```

### Q: Как добавить задержку между кликами?

**A:** Через аргумент:

```bash
parser-2gis --parser.delay-between-clicks 500 ...
```

### Q: Как экспортировать статистику работы парсера?

**A:** Используйте StatisticsExporter:

```python
from parser_2gis import ParserStatistics, StatisticsExporter

stats = ParserStatistics()
# ... заполняем статистику ...
exporter = StatisticsExporter()
exporter.export_to_html(stats, Path('stats.html'))
```

### Q: Как валидировать данные перед сохранением?

**A:** Используйте DataValidator:

```python
from parser_2gis import DataValidator

validator = DataValidator()
validated = validator.validate_record(record)
```

### Q: Как избежать бесконечного цикла при 404 ошибках?

**A (v2.1):** Используйте новые параметры:

```bash
parser-2gis --parser.stop-on-first-404 yes \
            --parser.max-consecutive-empty-pages 5 ...
```

### Q: Как использовать адаптивные лимиты для разных городов?

**A (v2.1):** Адаптивные лимиты включены по умолчанию:

```python
from parser_2gis.parser.adaptive_limits import AdaptiveLimits

limits = AdaptiveLimits()
limits.add_records_count(10)
limits.add_records_count(15)
limits.add_records_count(20)

adaptive_limit = limits.get_adaptive_limit()
city_size = limits.get_city_size()
```

### Q: Как использовать интеллектуальный retry?

**A (v2.1):** Retry включен по умолчанию:

```python
from parser_2gis.parser.smart_retry import SmartRetryManager

retry = SmartRetryManager(max_retries=3)
if retry.should_retry('502 Bad Gateway', records_on_page=10):
    # Выполняем retry
```

### Q: Как мониторить здоровье браузера?

**A (v2.1):** Используйте BrowserHealthMonitor:

```python
from parser_2gis.chrome.health_monitor import BrowserHealthMonitor

monitor = BrowserHealthMonitor(browser, enable_auto_restart=True)
health = monitor.check_health()
if not health['healthy'] and monitor.should_restart():
    monitor.restart_browser()
```

---

## 📞 Поддержка

### Ресурсы

- 📖 [Документация Pydantic](https://docs.pydantic.dev/)
- 📖 [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- 📖 [PySimpleGUI Documentation](https://pysimplegui.readthedocs.io/)
- 📖 [pytest Documentation](https://docs.pytest.org/)

### Связь

- 🐛 [Сообщить об ошибке](https://github.com/Githab-capibara/parser-2gis/issues)
- 💬 [Обсуждения](https://github.com/Githab-capibara/parser-2gis/discussions)
- 📝 [Руководство для разработчиков](CONTRIBUTING.md)
- 📋 [История изменений](CHANGELOG.md)
- 🔧 [Отчёт об исправлениях](FIXES_REPORT.md)

---

## 📄 Лицензия

Этот проект лицензирован под MIT License — см. файл [LICENSE](LICENSE).

---

## 🙏 Благодарности

- Команде 2GIS за отличный сервис
- Сообществу Pydantic за отличный инструмент валидации
- Разработчикам PySimpleGUI за удобный GUI фреймворк
- Разработчикам tqdm за отличную библиотеку прогресс-баров
- Разработчикам psutil за отличную библиотеку мониторинга ресурсов
- Всем контрибьюторам за вклад в проект

---

## 📝 Примечания

- Проект использует Chrome DevTools Protocol для управления браузером
- Парсинг может быть ограничен политиками 2GIS
- Рекомендуется использовать разумные задержки и лимиты
- Проект предназначен только для образовательных целей
- Кэширование данных работает в SQLite базе данных
- Статистика работы парсера доступна в 4 форматах
- Адаптивные лимиты автоматически подстраиваются под размер города
- Интеллектуальный retry анализирует тип ошибки и контекст

---

## 🆕 v2.1 Новые возможности

### Что нового в версии 2.1?

Версия 2.1 добавляет 5 новых модулей для улучшения стабильности и производительности:

1. **AdaptiveLimits** — адаптивные лимиты для разных размеров городов
2. **SmartRetryManager** — интеллектуальный retry механизм
3. **EndOfResultsDetector** — детектор окончания результатов
4. **ParallelOptimizer** — оптимизатор параллельного парсинга
5. **BrowserHealthMonitor** — монитор здоровья браузера с авто-перезапуском

Все модули полностью документированы на русском языке и протестированы (26 новых тестов).

### Миграция с версии 2.0

Версия 2.1 полностью обратно совместима с версией 2.0. Все новые функции — дополнительные, старый код продолжает работать без изменений.

### Пример использования новых функций v2.1

```python
from parser_2gis.parser.adaptive_limits import AdaptiveLimits
from parser_2gis.parser.smart_retry import SmartRetryManager
from parser_2gis.parser.end_of_results import EndOfResultsDetector
from parser_2gis.parallel_optimizer import ParallelOptimizer
from parser_2gis.chrome.health_monitor import BrowserHealthMonitor

# Адаптивные лимиты
limits = AdaptiveLimits()
limits.add_records_count(10)
print(f"Лимит: {limits.get_adaptive_limit()}")

# Интеллектуальный retry
retry = SmartRetryManager()
if retry.should_retry('502 Bad Gateway', records_on_page=10):
    # Retry

# Детектор окончания
detector = EndOfResultsDetector(chrome_remote)
if detector.is_end_of_results():
    return

# Оптимизатор
optimizer = ParallelOptimizer(max_workers=5)
optimizer.add_task(url, cat, city, priority=1)

# Монитор здоровья
monitor = BrowserHealthMonitor(browser, enable_auto_restart=True)
health = monitor.check_health()
if not health['healthy'] and monitor.should_restart():
    monitor.restart_browser()
```

---

<p align="center">
  <strong>Parser2GIS — Парсер данных 2GIS на Python 🌍</strong><br>
  <em>Версия 2.1 — Создано с ❤️ для сообщества</em>
</p>

---

**Последнее обновление:** 2026-03-07  
**Авторы:** Githab-capibara, AI Assistant  
**Репозиторий:** https://github.com/Githab-capibara/parser-2gis.git