# Parser2GIS

<p align="center">
  <a href="#-описание">
    <img alt="Logo" width="128" src="https://user-images.githubusercontent.com/20641837/174094285-6e32eb04-7feb-4a60-bddf-5a0fde5dba4d.png"/>
  </a>
</p>

<p align="center">
  <a href="https://github.com/Githab-capibara/parser-2gis/actions/workflows/tests.yml"><img src="https://github.com/interlark/parser-2gis/actions/workflows/tests.yml/badge.svg" alt="Tests"/></a>
  <a href="https://pypi.org/project/parser-2gis"><img src="https://badgen.net/pypi/v/parser-2gis" alt="PyPi version"/></a>
  <a href="https://pypi.org/project/parser-2gis"><img src="https://badgen.net/pypi/python/parser-2gis" alt="Supported Python versions"/></a>
  <a href="https://github.com/Githab-capibara/parser-2gis/releases"><img src="https://img.shields.io/github/downloads/interlark/parser-2gis/total.svg" alt="Downloads"/></a>
  <a href="https://github.com/Githab-capibara/parser-2gis"><img src="https://img.shields.io/github/stars/interlark/parser-2gis" alt="GitHub stars"/></a>
</p>

**Parser2GIS** — парсер сайта [2GIS](https://2gis.ru/) с помощью браузера [Google Chrome](https://google.com/chrome).

## 📋 Содержание

- [Описание](#-описание)
- [Возможности](#-возможности)
- [Поддерживаемые страны](#-поддерживаемые-страны)
- [Установка](#-установка)
- [Быстрый старт](#-быстрый-старт)
- [Использование](#-использование)
  - [CLI (командная строка)](#cli-командная-строка)
  - [GUI (графический интерфейс)](#gui-графический-интерфейс)
- [Конфигурация](#-конфигурация)
- [Форматы вывода](#-форматы-вывода)
- [Архитектура проекта](#-архитектура-проекта)
- [Тестирование](#-тестирование)
- [Разработка](#-разработка)
- [Утилиты](#-утилиты)
- [История изменений](#-история-изменений)
- [Поддержка проекта](#-поддержка-проекта)
- [Лицензия](#-лицензия)
- [Контакты](#-контакты)

---

## ℹ️ Описание

Parser2GIS — это инструмент для автоматического сбора базы адресов и контактов предприятий, которые работают на территории следующих стран:

- 🇷🇺 **Россия** (155 городов)
- 🇰🇿 **Казахстан** (18 городов)
- 🇧🇾 **Беларусь** (Минск)
- 🇦🇿 **Азербайджан** (Баку)
- 🇰🇬 **Киргизия** (Бишкек, Ош)
- 🇺🇿 **Узбекистан** (Ташкент, Самарканд)
- 🇨🇿 **Чехия** (Прага)
- 🇪🇬 **Египет** (Новый Каир)
- 🇮🇹 **Италия** (Падуя)
- 🇸🇦 **Саудовская Аравия** (14 городов)
- 🇨🇾 **Кипр**
- 🇦🇪 **ОАЭ**
- 🇨🇱 **Чили** (Сантьяго)
- 🇶🇦 **Катар**
- 🇴🇲 **Оман**
- 🇧🇭 **Бахрейн**
- 🇰🇼 **Кувейт**
- 🇮🇶 **Ирак** (Басра)

Парсер извлекает данные из API 2GIS, включая:
- Наименование и описание организации
- Адрес, почтовый индекс, район, город, регион
- Координаты (широта и долгота)
- Телефоны, e-mail, веб-сайты
- Социальные сети (Instagram, Facebook, VK, WhatsApp, Viber, Telegram и др.)
- Часы работы
- Рейтинг и количество отзывов
- Рубрики (категории)

---

## ✨ Возможности

- 💰 **Абсолютно бесплатный** — открытый исходный код
- 🤖 **Обход анти-бот блокировок** — успешно работает на территории РФ
- 🖥️ **Кроссплатформенность** — работает под Windows, Linux и MacOS
- 📄 **Три формата вывода** — CSV, XLSX и JSON
- 🔗 **Генератор ссылок** — по городам и рубрикам
- 🎨 **GUI и CLI** — графический интерфейс и командная строка
- ⚙️ **Гибкая настройка** — множество параметров конфигурации
- 🧹 **Сборщик мусора** — контроль потребления памяти
- 🚀 **Автоматическая навигация** — по страницам результатов

---

## 🚀 Установка

### Требования

- **Python 3.8, 3.9, 3.10, 3.11**
- **Google Chrome** (обязательно)

### Установка одним файлом

Скачайте последний [релиз](https://github.com/Githab-capibara/parser-2gis/releases/latest).

### Установка из PyPI

```bash
# Только CLI
pip install parser-2gis

# CLI + GUI
pip install parser-2gis[gui]
```

### Установка для разработки

```bash
# Клонируйте репозиторий
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Установите зависимости
pip install -e .[dev]

# Установите pre-commit хуки
pre-commit install
```

---

## 📖 Быстрый старт

### Пример использования в командной строке

```bash
# Парсинг аптек в Москве в CSV
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" -o result.csv -f csv

# Парсинг с настройками
parser-2gis -i "https://2gis.ru/moscow/search/Рестораны" \
    -o result.xlsx -f xlsx \
    --parser.max-records 100 \
    --chrome.headless yes
```

### Пример использования в Python

```python
from parser_2gis import main

if __name__ == '__main__':
    main()
```

---

## 💻 Использование

### CLI (командная строка)

#### Обязательные аргументы

| Аргумент | Описание |
|----------|----------|
| `-i`, `--url` | URL с выдачей 2GIS (один или несколько) |
| `-o`, `--output-path` | Путь до результирующего файла |
| `-f`, `--format` | Формат файла: `csv`, `xlsx` или `json` |

#### Аргументы для парсинга городов

| Аргумент | Описание | По умолчанию |
|----------|----------|----------|
| `--cities` | Коды городов для парсинга (например: `moscow spb kazan`) | - |
| `--query` | Поисковый запрос для генерации URL по городам | `Организации` |
| `--rubric` | Код рубрики для фильтрации результатов | - |

#### Аргументы браузера

| Аргумент | Описание | По умолчанию |
|----------|----------|----------|
| `--chrome.binary_path` | Путь к исполняемому файлу Chrome | Авто |
| `--chrome.disable-images` | Отключить изображения | `yes` |
| `--chrome.headless` | Скрытый режим браузера | `no` |
| `--chrome.silent-browser` | Отключить отладочную информацию | `yes` |
| `--chrome.start-maximized` | Запустить окно развёрнутым | `no` |
| `--chrome.memory-limit` | Лимит оперативной памяти (МБ) | 75% от общей |

#### Аргументы CSV/XLSX

| Аргумент | Описание | По умолчанию |
|----------|----------|----------|
| `--writer.csv.add-rubrics` | Добавить колонку "Рубрики" | `yes` |
| `--writer.csv.add-comments` | Добавлять комментарии к ячейкам | `yes` |
| `--writer.csv.columns-per-entity` | Количество колонок для множественных значений | `3` |
| `--writer.csv.remove-empty-columns` | Удалить пустые колонки | `yes` |
| `--writer.csv.remove-duplicates` | Удалить повторяющиеся записи | `yes` |
| `--writer.csv.join_char` | Разделитель для комплексных значений | `; ` |

#### Аргументы парсера

| Аргумент | Описание | По умолчанию |
|----------|----------|----------|
| `--parser.use-gc` | Включить сборщик мусора | `no` |
| `--parser.gc-pages-interval` | Запуск GC каждые N страниц | `10` |
| `--parser.max-records` | Максимальное количество записей с URL | Авто |
| `--parser.skip-404-response` | Пропускать 404 ответы | `yes` |
| `--parser.delay_between_clicks` | Задержка между кликами (мс) | `0` |

#### Прочие аргументы

| Аргумент | Описание | По умолчанию |
|----------|----------|----------|
| `--writer.verbose` | Отображать наименования позиций | `yes` |
| `--writer.encoding` | Кодировка файла | `utf-8-sig` |

#### Примеры

```bash
# Базовый пример
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" -o pharmacies.csv -f csv

# Несколько URL
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
               "https://2gis.ru/spb/search/Аптеки" \
            -o pharmacies.csv -f csv

# Парсинг по городам (CLI)
parser-2gis --cities moscow spb kazan \
            --query "Аптеки" \
            -o pharmacies.csv -f csv

# Парсинг по городам с рубрикой
parser-2gis --cities moscow spb \
            --query "Рестораны" \
            --rubric "161" \
            -o restaurants.xlsx -f xlsx

# Комбинированный режим (URL + города)
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
            --cities spb kazan \
            --query "Аптеки" \
            -o pharmacies.csv -f csv

# Скрытый режим с ограничением записей
parser-2gis -i "https://2gis.ru/moscow/search/Рестораны" \
            -o restaurants.json -f json \
            --chrome.headless yes \
            --parser.max-records 50

# Парсинг с отладочной информацией браузера
parser-2gis -i "https://2gis.ru/moscow/search/Кафе" \
            -o cafes.xlsx -f xlsx \
            --chrome.silent-browser no
```

### GUI (графический интерфейс)

Для запуска GUI просто выполните команду без обязательных аргументов:

```bash
parser-2gis
```

Или с флагом GUI:

```bash
pip install parser-2gis[gui]
parser-2gis
```

**Возможности GUI:**
- Добавление и редактирование URL
- Генератор ссылок по городам и рубрикам
- 🌍 **Выбор городов** — новый интерфейс для выбора городов из списка (180+ городов)
- Выбор формата вывода
- Настройка параметров парсера
- Просмотр логов в реальном времени
- Настройки приложения

---

## ⚙️ Конфигурация

Конфигурация хранится в файле `parser-2gis.config` в зависимости от ОС:

| ОС | Путь |
|----|------|
| **Windows** | `C:\Users\%USERPROFILE%\AppData\Local\parser-2gis\parser-2gis.config` |
| **Linux** | `~/.config/parser-2gis/parser-2gis.config` |
| **macOS** | `~/Library/Application Support/parser-2gis/parser-2gis.config` |

### Структура конфигурации

```json
{
    "version": "0.1",
    "log": {
        "level": "DEBUG",
        "cli_format": "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s",
        "gui_format": "%(asctime)s.%(msecs)03d | %(message)s"
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
        "start_maximized": false,
        "memory_limit": 3072
    },
    "parser": {
        "skip_404_response": true,
        "delay_between_clicks": 0,
        "max_records": 1000,
        "use_gc": false,
        "gc_pages_interval": 10
    }
}
```

---

## 📄 Форматы вывода

### CSV

Таблица с заголовками и следующими колонками:

| Колонка | Описание |
|---------|----------|
| Наименование | Название организации |
| Описание | Дополнительная информация |
| Рубрики | Категории деятельности |
| Адрес | Полный адрес |
| Телефон 1, Телефон 2, ... | Номера телефонов |
| E-mail 1, E-mail 2, ... | Адреса электронной почты |
| Веб-сайт | Официальный сайт |
| Instagram, Facebook, VK | Социальные сети |
| WhatsApp, Viber, Telegram | Мессенджеры |
| Часы работы | Режим работы |
| Рейтинг | Средняя оценка |
| Количество отзывов | Число отзывов |
| Широта, Долгота | Координаты |
| 2GIS URL | Ссылка на карточку |

### XLSX

Excel-таблица с теми же данными, что и CSV, с форматированием заголовков.

### JSON

Массив объектов API 2GIS в формате JSON.

---

## 🏗️ Архитектура проекта

```
parser-2gis/
├── parser_2gis/              # Основной пакет
│   ├── __init__.py           # Точка входа (экспортирует main и __version__)
│   ├── main.py               # Главный модуль CLI (парсинг аргументов, точка входа)
│   ├── config.py             # Конфигурация (Pydantic BaseModel)
│   ├── common.py             # Общие утилиты (декораторы, валидация, URL encoder)
│   ├── paths.py              # Пути к данным и изображениям
│   ├── version.py            # Версия пакета (1.2.1) и конфигурации (0.1)
│   ├── exceptions.py         # Экспорт исключений
│   │
│   ├── chrome/               # Работа с Chrome через DevTools Protocol
│   │   ├── browser.py        # Запуск браузера с временным профилем
│   │   ├── remote.py         # Chrome DevTools Protocol обёртка
│   │   ├── dom.py            # DOM-узлы (DOMNode модель)
│   │   ├── options.py        # Опции Chrome (headless, memory_limit)
│   │   ├── utils.py          # Утилиты (поиск пути к Chrome, свободный порт)
│   │   ├── exceptions.py     # Исключения Chrome
│   │   └── patches/
│   │       ├── __init__.py   # Применение всех патчей
│   │       └── pychrome.py   # Патч обработки пустых сообщений CDP
│   │
│   ├── parser/               # Парсеры данных
│   │   ├── factory.py        # Фабрика парсеров (get_parser)
│   │   ├── options.py        # Опции парсера (max_records, delay)
│   │   ├── utils.py          # Утилиты (blocked_requests)
│   │   ├── exceptions.py     # Исключения парсера
│   │   └── parsers/
│   │       ├── __init__.py
│   │       ├── main.py       # Основной парсер (поисковая выдача)
│   │       ├── firm.py       # Парсер фирм (/firm/<id>)
│   │       └── in_building.py # Парсер "В здании" (/inside/<id>)
│   │
│   ├── writer/               # Писатели файлов
│   │   ├── factory.py        # Фабрика писателей (get_writer)
│   │   ├── options.py        # Опции писателя (encoding, CSV options)
│   │   ├── exceptions.py     # Исключения писателя
│   │   ├── models/           # Модели данных (Pydantic)
│   │   │   ├── __init__.py
│   │   │   ├── catalog_item.py  # CatalogItem (основная модель)
│   │   │   ├── address.py       # Address
│   │   │   ├── adm_div_item.py  # AdmDivItem (административные единицы)
│   │   │   ├── contact_group.py # ContactGroup, Contact
│   │   │   ├── name_ex.py       # NameEx (расширенное имя)
│   │   │   ├── org.py           # Org
│   │   │   ├── point.py         # Point (координаты)
│   │   │   ├── reviews.py       # Reviews (рейтинг, отзывы)
│   │   │   ├── rubric.py        # Rubric (рубрики)
│   │   │   └── schedule.py      # Schedule (часы работы)
│   │   └── writers/
│   │       ├── __init__.py
│   │       ├── file_writer.py  # Базовый абстрактный писатель
│   │       ├── csv_writer.py   # CSV writer (с удалением пустых колонок и дубликатов)
│   │       ├── xlsx_writer.py  # XLSX writer (конвертация из CSV)
│   │       └── json_writer.py  # JSON writer (потоковая запись)
│   │
│   ├── logger/               # Логирование
│   │   ├── __init__.py
│   │   ├── logger.py         # Настройка логгера (CLI, GUI, QueueHandler)
│   │   └── options.py        # Опции логирования (уровень, формат)
│   │
│   ├── runner/               # Запуск парсера
│   │   ├── __init__.py
│   │   ├── runner.py         # Базовый абстрактный runner
│   │   ├── cli.py            # CLI runner (синхронный)
│   │   └── gui.py            # GUI runner (поток с отменой)
│   │
│   ├── cli/                  # CLI приложение
│   │   ├── __init__.py
│   │   └── app.py            # Запуск CLIRunner
│   │
│   ├── gui/                  # GUI приложение (PySimpleGUI)
│   │   ├── __init__.py
│   │   ├── app.py            # Главное окно (URL, лог, кнопки)
│   │   ├── settings.py       # Диалог настроек (вкладки: браузер, парсер, CSV)
│   │   ├── theme.py          # Тема оформления (цвета, шрифты, отступы)
│   │   ├── utils.py          # Утилиты GUI (event handler, context menu)
│   │   ├── error_popup.py    # Всплывающее окно ошибки
│   │   ├── rubric_selector.py # Диалог выбора рубрик (дерево)
│   │   ├── urls_editor.py    # Редактор URL (текст с номерами строк)
│   │   ├── urls_generator.py # Генератор URL (города, запрос, рубрика)
│   │   ├── city_selector.py  # Выбор городов (список по странам)
│   │   └── widgets/          # Кастомные виджеты
│   │       ├── sg/           # PySimpleGUI виджеты (RubricsTree)
│   │       └── tk/           # Tkinter виджеты (CustomText, LineNumberedText)
│   │
│   └── data/                 # Данные
│       ├── cities.json       # Список городов (204 города, 18 стран)
│       ├── rubrics.json      # Список рубрик (1786 рубрик)
│       └── images/           # Изображения (icon, logo, loading, settings)
│
├── testes/                   # Тесты (pytest)
│   ├── __init__.py
│   ├── conftest.py           # Фикстуры pytest (test_data_dir, sample_urls)
│   ├── test_chrome.py        # Тесты Chrome (options, remote, exceptions)
│   ├── test_common.py        # Тесты общих утилит (платформа, декораторы)
│   ├── test_config.py        # Тесты конфигурации (создание, загрузка, слияние)
│   ├── test_gui_theme.py     # Тесты GUI тем (цвета, шрифты)
│   ├── test_gui_utils.py     # Тесты GUI утилит (event handler, url_encode)
│   ├── test_integration.py   # Комплексные интеграционные тесты
│   ├── test_logger.py        # Тесты логирования (уровни, QueueHandler)
│   ├── test_parser.py        # Интеграционные тесты парсера
│   ├── test_parser_options.py # Тесты опций парсера
│   ├── test_paths.py         # Тесты путей (data_path, user_path, images)
│   ├── test_runner.py        # Тесты runners (CLI, GUI)
│   ├── test_version_exceptions.py # Тесты версий и исключений
│   └── test_writer.py        # Тесты писателей (CSV, JSON, XLSX)
│
├── scripts/                  # Скрипты обновления данных
│   ├── update_cities_list.py # Обновление списка городов (2GIS API)
│   └── update_rubrics_list.py # Обновление списка рубрик (2GIS API)
│
├── parser-2gis.py            # Точка входа standalone (PyInstaller)
├── setup.py                  # Установка пакета (зависимости, entry points)
├── setup.cfg                 # Конфигурация flake8, mypy, pytest
├── pytest.ini                # Конфигурация pytest (маркеры, таймауты)
├── tox.ini                   # Конфигурация tox (flake8, mypy, py38-310)
├── .pre-commit-config.yaml   # Pre-commit хуки (trailing-whitespace, flake8, mypy)
├── .gitignore                # Git ignore (venv, __pycache__, dist, build)
├── LICENSE                   # Лицензия LGPLv3+
├── MANIFEST.in               # Manifest (включение данных в пакет)
├── CHANGELOG.md              # История изменений (0.1.0 - 1.2.1)
└── README.md                 # Этот файл
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=parser_2gis

# Конкретный тест
pytest testes/test_parser.py

# С выводом логов
pytest -v -s

# Тесты с маркерами
pytest -m integration
pytest -m slow
```

### Структура тестов

| Файл | Описание |
|------|----------|
| `test_common.py` | Тесты общих утилит (платформа, декораторы, валидация, floor_to_hundreds, unwrap_dot_dict) |
| `test_config.py` | Тесты конфигурации (создание, загрузка, слияние, валидация, auto_create) |
| `test_logger.py` | Тесты логирования (настройка, уровни, QueueHandler, LogOptions) |
| `test_parser.py` | Интеграционные тесты парсера (парсинг с проверкой CSV/JSON) |
| `test_integration.py` | Комплексные интеграционные тесты (Config+Parser, Config+Writer) |
| `test_writer.py` | Тесты писателей файлов (CSVOptions, WriterOptions, CSVWriter, JSONWriter, XLSXWriter) |
| `test_paths.py` | Тесты путей к данным и изображениям (data_path, user_path, image_path) |
| `test_runner.py` | Тесты runners (AbstractRunner, GUIRunner, CLIRunner) |
| `test_parser_options.py` | Тесты опций парсера (ParserOptions валидация) |
| `test_chrome.py` | Тесты Chrome браузера (ChromeOptions, ChromeRemote, исключения) |
| `test_gui_theme.py` | Тесты GUI тем (цвета, типографика, get_font, get_spacing) |
| `test_gui_utils.py` | Тесты GUI утилит (generate_event_handler, url_query_encode, ensure_gui_enabled) |
| `test_version_exceptions.py` | Тесты версий и исключений (version, config_version, все исключения) |

### Pre-commit

```bash
# Запуск всех хуков
pre-commit run --all-files

# Проверка стиля
flake8 parser_2gis

# Проверка типов
mypy parser_2gis
```

### Маркеры тестов

- `slow` — медленные тесты
- `integration` — интеграционные тесты
- `gui` — тесты GUI
- `requires_chrome` — тесты, требующие Chrome
- `requires_network` — тесты, требующие сеть

---

## 🛠️ Разработка

### Зависимости для разработки

```bash
pip install -e .[dev]
```

Включает:
- `pytest>=6.2,<8` — тестирование
- `tox>=3.5,<4` — автоматизация тестирования
- `pre-commit>=2.6` — pre-commit хуки
- `wheel>=0.36.2,<0.38` — сборка пакетов
- `pyinstaller>=5.0,<5.7.0` (Windows) или `pyinstaller>=6.6.0` (Linux/Mac) — сборка standalone

### Основные зависимости

- `pychrome==0.2.4` — работа с Chrome DevTools Protocol
- `pydantic>=1.9.0,<2.0` — валидация данных
- `psutil>=5.4.8` — работа с системной памятью
- `requests>=2.13.0` — HTTP-запросы
- `xlsxwriter>=3.0.5` — создание XLSX файлов
- `PySimpleGUI==4.59.0` (опционально) — GUI интерфейс

### Сборка standalone приложения

```bash
# Windows
python setup.py build_standalone

# Linux/Mac
python setup.py build_standalone
```

Создаётся исполняемый файл `Parser2GIS` в папке `dist/`.

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

### Вклад в проект

1. Fork репозитория
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Закоммитьте изменения (`git commit -m 'Добавлена amazing-feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Стиль кода

- **flake8**: max-line-length=130, игнорируемые правила: E501, W503
- **mypy**: строгая проверка типов
- **Форматирование**: 4 пробела, UTF-8 кодировка
- **Комментарии**: на русском языке

---

## 📝 История изменений

### [1.2.1] — 14-03-2024
- ✅ Поддержка парсинга остановок
- ✅ Сортировка URL по алфавиту для исключения повторений поисковой выдачи
- ✅ Обновлён список рубрик

### [1.2.0] — 08-02-2024
- ✅ Поддержка ссылок организаций `https://2gis.ru/<city>/firm/<firm_id>`
- ✅ Обновлён список рубрик и городов

### [1.1.2] — 08-03-2023
- ✅ Поддержка Chrome v111
- ✅ Новый город Басра (Ирак)
- ✅ Обновлён список рубрик и городов

### [1.1.1] — 03-02-2023
- ✅ Обновлён список рубрик и городов
- ✅ Добавлены поля контактов "Telegram", "Viber" и "WhatsApp"

### [1.1.0] — 05-01-2023
- ✅ Обновлён список рубрик и городов
- ✅ Добавлены поля "Рейтинг" и "Количество отзывов"
- ✅ Добавлена возможность записи результата в Excel таблицу
- ✅ Добавлена автоматическая навигация к странице, если в URL есть параметр страницы `/page/<номер_страницы>`

### [0.1.10] — 25-10-2022
- ✅ Обновлён список рубрик и городов
- ⚠️ Отключен скрытый режим парсинга по-умолчанию

### [0.1.9] — 18-08-2022
- ✅ Новые рубрики: *Клубы настольного тенниса, Атрибутика для болельщиков, Полицейские станции*
- ✅ Поддержка парсинга ссылок "В здании"

### [0.1.8] — 10-08-2022
- ✅ Совместимость с Windows 7, Windows 8

### [0.1.7] — 19-07-2022
- ⚠️ Исправлена возможная ошибка во время получения нового ключа авторизации
- ⚠️ Исправлен баг с остановкой парсера при возникновении ошибки
- ✅ Новые рубрики: *Прокат компьютеров / ноутбуков, Буккроссинг, Пляжные принадлежности, Администрация города/посёлка/села*

### [0.1.6] — 03-07-2022
- ⚠️ Исправлен релиз под Linux
- ⚠️ Пропуск некорректных ответов сервера (JSON expected)
- ✅ Новая страна: *Кувейт*
- ✅ Новые рубрики: *Купальники, Мебель для салонов красоты, Дневные детские лагеря*

### [0.1.5] — 25-05-2022
- ⚠️ Исправлен баг с редкой ошибкой чтения ответа сервера при парсинге CSV
- ✅ Колонка "Часовой пояс" в CSV

### [0.1.4] — 24-05-2022
- ⚠️ Исправлен баг с неполным удалением временного профиля браузера

### [0.1.3] — 23-05-2022
- ⚠️ CSV: Исправлено название колонки `Веб сайт` -> `Веб-сайт`
- ⚠️ Usage: Убрана ошибочно влезшая версия конфигурации

### [0.1.2] — 22-05-2022
- ✅ Предупреждение при неудачной попытке загрузки GUI

### [0.1.1] — 22-05-2022
- ⚠️ Ссылка на репозиторий внутри модуля и в манифесте

### [0.1.0] — 22-05-2022
- ✅ Первый релиз

---

## 👍 Поддержка проекта

Parser2GIS — проект с открытым исходным кодом, разрабатываемый энтузиастами.

### Поддержать финансово

<a href="https://yoomoney.ru/to/4100118362270186" target="_blank">
  <img alt="Yoomoney Donate" src="https://github.com/interlark/parser-2gis/assets/20641837/e875e948-0d69-4ed5-804c-8a1736ab0c9d" width="200">
</a>

### Другие способы поддержки

- ⭐ Поставьте звезду на GitHub
- 🐛 Сообщайте об ошибках
- 💡 Предлагайте новые функции
- 📖 Улучшайте документацию

---

## 📄 Лицензия

Проект распространяется под лицензией **LGPLv3+** (GNU Lesser General Public License v3 or later).

**Автор:** Andy Trofimov <interlark@gmail.com>

```
Copyright (C) 2022-2025 Andy Trofimov <interlark@gmail.com>

Parser2GIS is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Parser2GIS is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with Parser2GIS.  If not, see <https://www.gnu.org/licenses/>.
```

---

## 📞 Контакты

- **GitHub**: [https://github.com/Githab-capibara/parser-2gis](https://github.com/Githab-capibara/parser-2gis)
- **PyPI**: [https://pypi.org/project/parser-2gis](https://pypi.org/project/parser-2gis)
- **Документация**: [https://github.com/interlark/parser-2gis/wiki](https://github.com/interlark/parser-2gis/wiki)
- **Changelog**: [https://github.com/Githab-capibara/parser-2gis/blob/main/CHANGELOG.md](https://github.com/Githab-capibara/parser-2gis/blob/main/CHANGELOG.md)

---

<p align="center">
  <strong>Parser2GIS © 2022-2025</strong><br>
  Сделано с ❤️ для сообщества
</p>
