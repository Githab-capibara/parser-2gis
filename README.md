# Parser2GIS 🌍

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-LGPLv3%2B-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-20%20passed-brightgreen.svg)](tests/)
[![Code Quality](https://img.shields.io/badge/score-95/100-brightgreen.svg)](https://github.com/Githab-capibara/parser-2gis)
[![GitHub](https://img.shields.io/badge/GitHub-Githab--capibara-orange.svg)](https://github.com/Githab-capibara/parser-2gis)

**Parser2GIS** — мощный инструмент для парсинга данных с сервиса 2GIS (2ГИС), использующий браузер Chrome для обхода анти-бот защит.

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
- [Структура проекта](#структура-проекта)
- [Тестирование](#тестирование)
- [Разработка](#разработка)
- [История изменений](#история-изменений)
- [Отчеты о качестве кода](#отчеты-о-качестве-кода)
- [FAQ](#faq)
- [Поддержка](#поддержка)

---

## 🎯 О проекте

Parser2GIS — Python-приложение для автоматизированного сбора данных с сайта 2GIS (2ГИС). Проект позволяет:

- ✅ Парсить организации по городам и категориям
- ✅ Сохранять данные в форматах CSV, XLSX, JSON
- ✅ Работать в режимах CLI и GUI
- ✅ Использовать параллельный парсинг (до 20 потоков)
- ✅ Настраивать параметры через конфигурационные файлы
- ✅ Кэшировать результаты (ускорение 10-100x)
- ✅ Валидировать данные перед сохранением
- ✅ Экспортировать статистику работы
- ✅ Автоматически обрабатывать ошибки и 404 страницы
- ✅ Использовать адаптивные лимиты для городов
- ✅ Мониторить здоровье браузера с авто-перезапуском

### Технологии

| Компонент | Версия | Назначение |
|-----------|--------|------------|
| **Python** | 3.10–3.12 | Основной язык |
| **Pydantic v2** | Актуальная | Валидация данных |
| **Chrome DevTools Protocol** | Актуальная | Управление браузером |
| **Rich** | Актуальная | Прогресс-бары и вывод в CLI |
| **pytest** | Актуальная | Тестирование |
| **SQLite** | Встроенная | Кэширование результатов |
| **psutil** | Актуальная | Мониторинг ресурсов |
| **tqdm** | Актуальная | Прогресс-бары |

### Поддерживаемые ОС

- ✅ **Linux Ubuntu** — основная поддерживаемая ОС
- ⚠️ **Windows/macOS** — ограниченная поддержка (требуется дополнительная настройка)

---

## ✨ Основные возможности

### Парсинг данных

- ✅ **204 города** в 18 странах
- ✅ **93 категории** для парсинга
- ✅ **1786 рубрик** для точного поиска
- ✅ Парсинг фирм, остановок, зданий
- ✅ Извлечение контактных данных, отзывов, графиков работы
- ✅ Автоматическая навигация по страницам
- ✅ Обработка пагинации

### Форматы вывода

| Формат | Описание | Преимущества |
|--------|----------|--------------|
| **CSV** | Таблицы с разделителями | Совместимость, скорость |
| **XLSX** | Файлы Microsoft Excel | Форматирование, фильтры |
| **JSON** | Структурированные данные | Программный парсинг |

### Режимы работы

- ✅ **CLI** — командная строка для автоматизации
- ✅ **TUI** — текстовый интерфейс для интерактивной работы
- ✅ **Параллельный парсинг** — до 20 потоков для ускорения

### Настройки

- ✅ Гибкая конфигурация через JSON
- ✅ Настройки Chrome (headless, память, блокировка)
- ✅ Настройки парсера (задержки, лимиты, retry)
- ✅ Настройки вывода (кодировка, колонки, форматирование)

---

## 📦 Установка

### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| **Python** | 3.10–3.12 | Обязательно |
| **Google Chrome** | Любая актуальная | Для парсинга |
| **Git** | Любая актуальная | Для работы с репозиторием |
| **pip** | Актуальная | Установка зависимостей |

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

#### Парсинг всех категорий города

```bash
# Все 93 категорий Омска (5 потоков)
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

### TUI режим

```bash
# Запуск текстового интерфейса
parser-2gis

# Запуск нового TUI (pytermgui)
parser-2gis --tui-new

# Запуск TUI с автоматическим парсингом Омска
parser-2gis --tui-new-omsk
```

### Примеры использования API

#### Кэширование результатов

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
```

#### Прогресс-бар для CLI

```python
from parser_2gis.cli import ProgressManager

# Создаем менеджер прогресса
progress = ProgressManager()

# Запускаем прогресс-бар
progress.start(total_pages=10, total_records=1000)

# Обновляем прогресс
for page in range(10):
    progress.update_page()
    for record in range(100):
        progress.update_record()

# Завершаем и выводим статистику
progress.finish()
# Вывод: "✅ Завершено за 45.2 сек (22.1 записей/сек)"
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
- ⚡ Быстрый запуск
- 🔧 Легкая интеграция в CI/CD
- 📜 Подходит для сценариев и автоматизации
- 🎛️ Полный контроль через аргументы
- 📊 Красивые прогресс-бары (через ProgressManager)

### TUI режим

Текстовый интерфейс для интерактивной работы.

**Преимущества:**
- 🖼️ Удобный текстовый интерфейс
- 🏙️ Визуальный выбор городов и категорий
- 📈 Просмотр прогресса в реальном времени
- 🎓 Не требует знаний командной строки
- 🖱️ Поддержка мыши и навигации с клавиатуры

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

### Аргументы парсера (v2.0, v2.1)

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
| `--parser.memory-threshold` | Порог памяти для очистки в МБ (v2.1) | 2048 |

### Полный пример

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
  --parser.use-gc yes \
  --parser.stop-on-first-404 yes \
  --parser.max-consecutive-empty-pages 5 \
  --parser.max-retries 3 \
  --parser.retry-on-network-errors yes \
  -o output/ \
  -f csv
```

---

## 🖥️ TUI интерфейс

**Примечание:** В текущей версии используется текстовый интерфейс (TUI) на основе Rich и pytermgui.

### Возможности

- 🏙️ Выбор городов из списка (204 города)
- 📂 Выбор категорий/рубрик (1786 рубрик)
- 📝 Ручной ввод URL
- 🔧 Настройки Chrome и парсера
- 📊 Прогресс-бар и логирование
- 💾 Выбор формата вывода
- 🖱️ Поддержка мыши и клавиатурной навигации

### Запуск

```bash
# Запуск старого TUI (rich)
parser-2gis

# Запуск нового TUI (pytermgui)
parser-2gis --tui-new

# Запуск TUI с парсингом Омска
parser-2gis --tui-new-omsk

# Windows
python.exe -m parser_2gis
```

### Новый TUI (pytermgui)

Современный интерактивный интерфейс с поддержкой:
- Многоэкранной навигации
- Поиска городов и категорий
- Настройки через формы
- Прогресс-баров в реальном времени
- Просмотра кэша и статистики

Подробнее см. [parser_2gis/tui_pytermgui/README.md](parser_2gis/tui_pytermgui/README.md)

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

**Пример конфигурации:**
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
- 📊 Форматирование ячеек
- 📏 Автоматическая ширина колонок
- 🔍 Поддержка фильтров
- 💼 Совместимость с Excel

### JSON

Структурированные данные.

**Преимущества:**
- 🗂️ Полная структура данных
- 💻 Легкий парсинг программно
- 📦 Поддержка вложенных объектов

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
    "memory_threshold": 2048
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
- ⚡ Ускорение повторных запусков в 10-100 раз
- 🗑️ Автоматическое удаление устаревшего кэша
- 📊 Статистика использования кэша
- 🧹 Возможность очистки кэша

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
- 📊 Двойной прогресс-бар (страницы и записи)
- ⏱️ Отображение ETA и скорости
- 📈 Итоговая статистика по завершении
- 🔕 Возможность отключения

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
- 📞 Форматирование телефонных номеров
- ✉️ Проверка email-адресов
- 🔗 Проверка URL
- 🧹 Очистка текста от лишних символов
- ✅ Валидация целых записей

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
- 📄 Красивые HTML отчеты
- 📦 Структурированные JSON данные
- 📊 Читаемые CSV файлы
- 📝 Текстовые отчеты
- 📈 Полная статистика работы

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
- 📝 Поддержка консоли и файлов
- 🔄 Ротация по размеру и дате
- 📋 Форматирование сообщений
- 🎚️ Разные уровни логирования
- 🔍 Фильтрация по типам

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
- 🌍 Автоматическая классификация городов (small, medium, large, huge)
- 📏 Адаптивные лимиты пустых страниц (2-7)
- ⏱️ Адаптивные таймауты для навигации (30-120 сек)
- 📊 Определение размера города на основе первых страниц

**Классификация городов:**

| Размер | Записей на страницу | Лимит пустых страниц |
|--------|---------------------|----------------------|
| `small` (маленький) | ≤ 10 | 2 |
| `medium` (средний) | ≤ 50 | 3 |
| `large` (крупный) | ≤ 200 | 5 |
| `huge` (огромный) | > 200 | 7 |

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
- 🔍 Анализ типа ошибки (502, 503, 504, 404, 403, 500)
- 📚 Учет контекста (количество записей, история попыток)
- ⏱️ Экспоненциальная задержка между попытками
- 🔢 Лимит максимального количества попыток

**Логика retry:**
- 🌐 Сетевые ошибки (502, 503, 504, Timeout) — всегда retry
- 📄 404 с записями — retry (возможна временная проблема)
- ❌ 404 без записей — не retry (конец категории)
- 🚫 403 (блокировка) — не retry (бесполезно)
- ⚠️ 500 (ошибка сервера) — retry

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
```

### 3. EndOfResultsDetector — Детектор окончания результатов

Автоматическое определение окончания результатов на странице для оптимизации парсинга.

**Преимущества:**
- 🔍 Определение конца результатов
- 📄 Проверка наличия пагинации
- ⚡ Оптимизация времени парсинга
- 🚫 Избегание лишних запросов

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
```

### 4. ParallelOptimizer — Оптимизатор параллельного парсинга

Интеллектуальное управление задачами параллельного парсинга с учетом приоритетов и ресурсов.

**Преимущества:**
- 🎯 Приоритизация задач
- 💾 Мониторинг использования памяти
- 📊 Статистика выполнения
- ⚡ Оптимизация распределения задач

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
```

### 5. BrowserHealthMonitor — Монитор здоровья браузера

Непрерывный мониторинг состояния браузера с автоматическим перезапуском при критических ошибках.

**Преимущества:**
- ❤️ Мониторинг здоровья браузера
- 🔄 Автоматический перезапуск при ошибках
- 📊 Статистика критических ошибок
- 🛡️ Предотвращение зависаний

**Пример использования:**

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

## 🏗️ Структура проекта

```
parser-2gis/
├── parser_2gis/              # Основной пакет
│   ├── main.py               # Точка входа CLI
│   ├── config.py             # Конфигурация (Pydantic)
│   ├── common.py             # Общие утилиты
│   ├── version.py            # Версия пакета
│   ├── exceptions.py         # Исключения
│   ├── cache.py              # Менеджер кэша
│   ├── validator.py          # Валидатор данных
│   ├── statistics.py         # Экспорт статистики
│   ├── paths.py              # Утилиты путей
│   ├── parallel_optimizer.py # Оптимизатор параллельного парсинга
│   ├── parallel_parser.py    # Параллельный парсер
│   │
│   ├── chrome/               # Работа с Chrome
│   │   ├── browser.py        # Запуск браузера
│   │   ├── remote.py         # Chrome DevTools Protocol
│   │   ├── options.py        # Опции Chrome
│   │   ├── dom.py            # Работа с DOM
│   │   ├── health_monitor.py # Монитор здоровья браузера
│   │   ├── utils.py          # Утилиты Chrome
│   │   └── exceptions.py     # Исключения Chrome
│   │
│   ├── parser/               # Парсеры данных
│   │   ├── parsers/
│   │   │   ├── main.py       # Основной парсер
│   │   │   ├── firm.py       # Парсер фирм
│   │   │   └── in_building.py # Парсер "В здании"
│   │   ├── adaptive_limits.py # Адаптивные лимиты
│   │   ├── smart_retry.py    # Интеллектуальный retry
│   │   ├── end_of_results.py # Детектор окончания результатов
│   │   ├── factory.py        # Фабрика парсеров
│   │   ├── options.py        # Опции парсера
│   │   ├── utils.py          # Утилиты парсера
│   │   └── exceptions.py     # Исключения парсера
│   │
│   ├── writer/               # Писатели файлов
│   │   ├── writers/
│   │   │   ├── csv_writer.py # CSV writer
│   │   │   ├── xlsx_writer.py # XLSX writer
│   │   │   └── json_writer.py # JSON writer
│   │   ├── factory.py        # Фабрика writers
│   │   ├── options.py        # Опции writers
│   │   └── models/           # Модели данных (Pydantic)
│   │
│   ├── runner/               # Запуск парсера
│   │   ├── runner.py         # Базовый класс
│   │   └── cli.py            # CLI запуск
│   │
│   ├── logger/               # Логирование
│   │   ├── logger.py         # Основной логгер
│   │   ├── file_handler.py   # Обработчик файлов
│   │   ├── visual_logger.py  # Визуальный логгер
│   │   └── options.py        # Опции логирования
│   │
│   ├── cli/                  # CLI приложение
│   │   ├── app.py            # CLI приложение
│   │   └── progress.py       # ProgressManager
│   │
│   ├── tui/                  # TUI приложение
│   │   ├── app.py            # Главное окно TUI
│   │   ├── components.py     # Компоненты интерфейса
│   │   └── logger.py         # Визуальный логгер
│   │
│   └── data/                 # Данные
│       ├── cities.json       # Города (204 города)
│       ├── rubrics.json      # Рубрики (1786 рубрик)
│       ├── categories_93.py  # 93 категории
│       └── images/           # Изображения
│
├── testes/                   # Тесты (pytest)
│   ├── conftest.py           # Конфигурация pytest
│   ├── test_common.py        # Тесты common.py
│   ├── test_config.py        # Тесты config.py
│   ├── test_chrome.py        # Тесты chrome/
│   ├── test_parser.py        # Тесты parser/
│   ├── test_writer.py        # Тесты writer/
│   ├── test_logger.py        # Тесты logger/
│   ├── test_file_logger.py   # Тесты file_handler.py
│   ├── test_runner.py        # Тесты runner/
│   ├── test_integration.py   # Интеграционные тесты
│   ├── test_main_categories_mode.py # Тесты categories-mode
│   ├── test_parallel_parser.py # Тесты параллельного парсера
│   ├── test_parser_options.py # Тесты опций парсера
│   ├── test_paths.py         # Тесты paths.py
│   └── test_version_exceptions.py # Тесты версии
│
├── scripts/                  # Скрипты обновления
│   ├── update_cities_list.py # Обновление городов
│   └── update_rubrics_list.py # Обновление рубрик
│
├── output/                   # Выходные файлы (по умолчанию)
├── README.md                 # Этот файл
├── CHANGELOG.md              # История изменений
├── CONTRIBUTING.md           # Руководство для разработчиков
├── LICENSE                   # Лицензия LGPLv3+
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

- ✅ **293 тестов** — все проходят
- 📊 **Покрытие:** ~80%

### Маркеры тестов

| Маркер | Описание |
|--------|----------|
| `slow` | Медленные тесты |
| `integration` | Интеграционные тесты |
| `tui` | Тесты TUI |
| `requires_chrome` | Тесты, требующие Chrome |
| `requires_network` | Тесты, требующие сеть |

### Написание тестов

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

### Сообщение коммита

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

---

## 📜 История изменений

### [Невошедшее] — v2.1 (НОВЫЕ ФУНКЦИИ)

#### Добавлено
- ✅ **AdaptiveLimits** — адаптивные лимиты для разных городов
- ✅ **SmartRetryManager** — интеллектуальный retry механизм
- ✅ **EndOfResultsDetector** — детектор окончания результатов
- ✅ **ParallelOptimizer** — оптимизатор параллельного парсинга
- ✅ **BrowserHealthMonitor** — монитор здоровья браузера с авто-перезапуском
- ✅ **stop_on_first_404** — немедленная остановка при первом 404
- ✅ **max_consecutive_empty_pages** — лимит подряд пустых страниц
- ✅ **26 новых тестов** — покрытие всех новых функций

#### Изменено
- ✅ Увеличен порог памяти по умолчанию (500 → 2048 МБ)
- ✅ Улучшена обработка ошибок в скриптах обновления данных
- ✅ Обновлена документация

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

### [1.2.1] — 14-03-2024

#### Добавлено
- ✅ Поддержка парсинга остановок
- ✅ Генератор ссылок добавляет в URL сортировку по алфавиту
- ✅ Обновлён список рубрик

### [1.2.0] — 08-02-2024

#### Добавлено
- ✅ Небольшой багфикс схемы ответов сервера
- ✅ Поддержка ссылок организаций `https://2gis.ru/<city>/firm/<firm_id>`
- ✅ Обновлён список рубрик и городов

Полный список изменений см. в [CHANGELOG.md](CHANGELOG.md).

---

## 📊 Отчеты о качестве кода

### Аудит кода от 9 марта 2026

| Категория | До исправлений | После исправлений | Улучшение |
|-----------|----------------|-------------------|-----------|
| **Критических ошибок** | 13 | 0 | -100% ✅ |
| **Высоких ошибок** | 30 | 15 | -50% |
| **Средних ошибок** | 60 | 45 | -25% |
| **Низких ошибок** | 54 | 40 | -26% |
| **Score кода** | 42/100 | 95/100 | +126% ✅ |
| **Ошибки mypy** | 34 | 0 | -100% ✅ |
| **Предупреждения flake8** | 30 | 0 | -100% ✅ |
| **Тестов пройдено** | 59 | 269 | +356% ✅ |

### Отчеты

> Отчеты о качестве кода доступны в файле [audit-report.md](audit-report.md).

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

Подробное руководство для разработчиков см. в [CONTRIBUTING.md](CONTRIBUTING.md).

### Начало работы

#### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| **Python** | 3.10–3.12 | Обязательно |
| **Google Chrome** | Любая актуальная | Для парсинга |
| **Git** | Любая актуальная | Для работы с репозиторием |

#### Установка для разработки

```bash
# Клонирование репозитория
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate  # Linux/macOS

# Установка зависимостей
pip install -e .[dev]

# Установка pre-commit хуков
pre-commit install
```

### Настройка переменной окружения GITHUB_TOKEN

Для работы с GitHub API (например, для автоматической синхронизации изменений) необходимо настроить переменную окружения:

1. **Получите токен GitHub:**
   - Перейдите в Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - Создайте новый токен с разрешениями: `contents` (read/write), `repository` (полный доступ)

2. **Установите переменную окружения:**

   **Linux/macOS:**
   ```bash
   export GITHUB_TOKEN="ghp_..."
   ```

   **Windows (cmd):**
   ```cmd
   set GITHUB_TOKEN=ghp_...
   ```

   **Windows (PowerShell):**
   ```powershell
   $env:GITHUB_TOKEN="ghp_..."
   ```

3. **Проверка установки:**
   ```bash
   echo $GITHUB_TOKEN  # Linux/macOS
   echo %GITHUB_TOKEN%  # Windows cmd
   echo $env:GITHUB_TOKEN  # Windows PowerShell
   ```

> ⚠️ **Важно:** Никогда не коммитьте токен в репозиторий! Используйте файл `.env` (добавлен в `.gitignore`) или копируйте команду `export` в `.bashrc`/`.zshrc`.

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

---

## 📄 Лицензия

Этот проект лицензирован под **GNU LGPLv3+** — см. файл [LICENSE](LICENSE).

---

## 🙏 Благодарности

- Команде **2GIS** за отличный сервис
- Сообществу **Pydantic** за отличный инструмент валидации
- Разработчикам **PySimpleGUI** за удобный GUI фреймворк
- Разработчикам **tqdm** за отличную библиотеку прогресс-баров
- Всем **контрибьюторам** за вклад в проект

---

## 📝 Примечания

- ⚠️ Проект использует Chrome DevTools Protocol для управления браузером
- ⚠️ Парсинг может быть ограничен политиками 2GIS
- ⚠️ Рекомендуется использовать разумные задержки и лимиты
- ⚠️ Проект предназначен только для образовательных целей
- ✅ Кэширование данных работает в SQLite базе данных
- ✅ Статистика работы парсера доступна в 4 форматах (JSON, CSV, HTML, TXT)

---

<p align="center">
  <strong>Parser2GIS — Парсер данных 2GIS на Python 🌍</strong><br>
  <em>Создано с ❤️ для сообщества</em>
</p>
