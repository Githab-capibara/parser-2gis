# Parser2GIS 🌍

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-300%20passed-brightgreen.svg)](testes/)
[![GitHub](https://img.shields.io/badge/GitHub-Githab--capibara-orange.svg)](https://github.com/Githab-capibara/parser-2gis)

**Parser2GIS** — это мощный инструмент для парсинга данных с сервиса 2GIS (2ГИС), использующий браузер Chrome для обхода анти-бот защит.

---

## 📋 Содержание

- [О проекте](#о-проекте)
- [Основные возможности](#основные-возможности)
- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
- [Режимы работы](#режимы-работы)
- [CLI интерфейс](#cli-интерфейс)
- [GUI интерфейс](#gui-интерфейс)
- [Форматы вывода](#форматы-вывода)
- [Конфигурация](#конфигурация)
- [Параллельный парсинг](#параллельный-парсинг)
- [Новые функции](#новые-функции)
- [Структура проекта](#структура-проекта)
- [Тестирование](#тестирование)
- [Разработка](#разработка)
- [История изменений](#история-изменений)
- [FAQ](#faq)
- [Руководство для разработчиков](#руководство-для-разработчиков)
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

### Технологии

- **Python 3.8-3.11** — основной язык разработки
- **Pydantic** — валидация конфигураций и данных
- **Chrome DevTools Protocol** — управление браузером
- **PySimpleGUI** — графический интерфейс (опционально)
- **pytest** — фреймворк для тестирования
- **SQLite** — хранение кэша результатов

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
- ✅ **Параллельный парсинг** — по городам и категориям

### Настройки

- ✅ Гибкая конфигурация через JSON
- ✅ Настройки Chrome (headless, память, блокировка)
- ✅ Настройки парсера (задержки, лимиты)
- ✅ Настройки вывода (кодировка, колонки, форматирование)

### Новые возможности (v2.0)

- ✅ **CacheManager** — кэширование результатов в SQLite (ускорение 10-100x)
- ✅ **ProgressManager** — красивые прогресс-бары для CLI режима
- ✅ **DataValidator** — валидация и очистка данных
- ✅ **StatisticsExporter** — экспорт статистики в JSON, CSV, HTML, TXT
- ✅ **FileLogger** — улучшенное логирование с поддержкой консоли и файлов

---

## 📦 Установка

### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.8 – 3.11 | Обязательно |
| Google Chrome | Любая актуальная | Для парсинга |
| Git | Любая актуальная | Для работы с репозиторием |

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

### GUI режим

```bash
# Запуск графического интерфейса
parser-2gis
```

### Использование новых функций

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

---

## 🎮 Режимы работы

### CLI режим

Командная строка для автоматизации и сценариев.

**Преимущества:**
- Быстрый запуск
- Легкая интеграция в CI/CD
- Подходит для сценариев и автоматизации
- Полный контроль через аргументы
- Красивые прогресс-бары (через ProgressManager)

### GUI режим

Графический интерфейс для интерактивной работы.

**Преимущества:**
- Удобный интерфейс
- Визуальный выбор городов и категорий
- Просмотр прогресса в реальном времени
- Не требует знаний командной строки

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
```python
{
  "writer": {
    "csv": {
      "add_rubrics": True,
      "add_comments": True,
      "columns_per_entity": 3,
      "remove_empty_columns": True,
      "remove_duplicates": True,
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
    "gc_pages_interval": 10
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

## 🏗️ Структура проекта

```
parser-2gis/
├── parser_2gis/              # Основной пакет
│   ├── main.py               # Точка входа CLI
│   ├── config.py             # Конфигурация (Pydantic)
│   ├── common.py             # Общие утилиты
│   ├── version.py            # Версия пакета
│   ├── exceptions.py         # Исключения
│   ├── cache.py              # Менеджер кэша (новое!)
│   ├── validator.py          # Валидатор данных (новое!)
│   ├── statistics.py         # Экспорт статистики (новое!)
│   │
│   ├── chrome/               # Работа с Chrome
│   │   ├── browser.py        # Запуск браузера
│   │   ├── remote.py         # Chrome DevTools Protocol
│   │   ├── options.py        # Опции Chrome
│   │   ├── dom.py            # Работа с DOM
│   │   └── exceptions.py     # Исключения Chrome
│   │
│   ├── parser/               # Парсеры данных
│   │   ├── parsers/
│   │   │   ├── main.py       # Основной парсер
│   │   │   ├── firm.py       # Парсер фирм
│   │   │   └── in_building.py # Парсер "В здании"
│   │   ├── options.py        # Опции парсера
│   │   ├── utils.py          # Утилиты парсера
│   │   └── exceptions.py     # Исключения парсера
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
│   │   ├── file_logger.py     # FileLogger (новое!)
│   │   └── options.py        # Опции логирования
│   │
│   ├── cli/                  # CLI приложение
│   │   ├── app.py            # CLI приложение
│   │   └── progress.py       # ProgressManager (новое!)
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
│   ├── test_logger.py        # Тесты logger/ (20 новых тестов!)
│   ├── test_runner.py        # Тесты runner/
│   ├── test_integration.py   # Интеграционные тесты
│   ├── test_main_categories_mode.py # Тесты categories-mode
│   └── ...                   # Остальные тесты
│
├── scripts/                  # Скрипты обновления
│   ├── update_cities_list.py # Обновление городов
│   └── update_rubrics_list.py # Обновление рубрик
│
├── output/                   # Выходные файлы (по умолчанию)
├── README.md                 # Этот файл
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
```

### Статистика тестов

- ✅ **300 тестов** — все проходят
- ⏭️ **2 пропущены** — требуют PySimpleGUI
- 📊 **Покрытие:** ~80%
- 🆕 **20 новых тестов** — для FileLogger

### Маркеры тестов

| Маркер | Описание |
|--------|----------|
| `slow` | Медленные тесты |
| `integration` | Интеграционные тесты |
| `gui` | Тесты GUI |
| `requires_chrome` | Тесты, требующие Chrome |
| `requires_network` | Тесты, требующие сеть |

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

### [Невошедшее] — v2.0 (НОВЫЕ ФУНКЦИИ)

#### Добавлено
- ✅ **CacheManager** — кэширование результатов в SQLite (ускорение 10-100x)
- ✅ **ProgressManager** — красивые прогресс-бары для CLI режима
- ✅ **DataValidator** — валидация и очистка данных
- ✅ **StatisticsExporter** — экспорт статистики в JSON, CSV, HTML, TXT
- ✅ **FileLogger** — улучшенное логирование с поддержкой консоли и файлов
- ✅ **20 новых тестов** для FileLogger
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

### [1.1.0] — 05-01-2023

#### Добавлено
- ✅ Обновлён список рубрик и городов
- ✅ Добавлены поля: **Рейтинг** и **Количество отзывов**
- ✅ Добавлена возможность записи результата в Excel таблицу (XLSX)
- ✅ Добавлена автоматическая навигация к странице

Полный список изменений см. в [CHANGELOG.md](CHANGELOG.md).

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

---

## 📚 Руководство для разработчиков

### Начало работы

#### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.8 – 3.11 | Обязательно |
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
- Всем контрибьюторам за вклад в проект

---

## 📝 Примечания

- Проект использует Chrome DevTools Protocol для управления браузером
- Парсинг может быть ограничен политиками 2GIS
- Рекомендуется использовать разумные задержки и лимиты
- Проект предназначен только для образовательных целей
- Кэширование данных работает в SQLite базе данных
- Статистика работы парсера доступна в 4 форматах

---

## 🆕 v2.0 Новые возможности

### Что нового в версии 2.0?

Версия 2.0 добавляет 5 новых модулей для улучшения функциональности:

1. **CacheManager** — кэширование результатов в SQLite
2. **ProgressManager** — красивые прогресс-бары для CLI
3. **DataValidator** — валидация и очистка данных
4. **StatisticsExporter** — экспорт статистики работы парсера
5. **FileLogger** — улучшенное логирование

Все модули полностью документированы на русском языке и протестированы.

### Миграция с версии 1.x

Версия 2.0 полностью обратно совместима с версией 1.x. Все новые функции — дополнительные, старый код продолжает работать без изменений.

### Пример использования новых функций

```python
from pathlib import Path
from datetime import datetime
from parser_2gis import (
    CacheManager,
    ProgressManager,
    DataValidator,
    ParserStatistics,
    StatisticsExporter
)

# Кэширование
cache = CacheManager(Path('/tmp/cache'))
data = cache.get(url)
if data is None:
    data = parse(url)
    cache.set(url, data)

# Прогресс
progress = ProgressManager()
progress.start(total_pages=10)
for page in pages:
    progress.update_page()
progress.finish()

# Валидация
validator = DataValidator()
validated = validator.validate_record(record)

# Статистика
stats = ParserStatistics()
# ... заполняем ...
exporter = StatisticsExporter()
exporter.export_to_html(stats, Path('stats.html'))
```

---

<p align="center">
  <strong>Parser2GIS — Парсер данных 2GIS на Python 🌍</strong><br>
  <em>Создано с ❤️ для сообщества</em>
</p>