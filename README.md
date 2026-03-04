# Parser2GIS

<p align="center">
  <a href="#-описание">
    <img alt="Logo" width="128" src="https://user-images.githubusercontent.com/20641837/174094285-6e32eb04-7feb-4a60-bddf-5a0fde5dba4d.png"/>
  </a>
</p>

<p align="center">
  <a href="https://github.com/Githab-capibara/parser-2gis/actions/workflows/tests.yml"><img src="https://github.com/Githab-capibara/parser-2gis/actions/workflows/tests.yml/badge.svg" alt="Tests"/></a>
  <a href="https://pypi.org/project/parser-2gis"><img src="https://badgen.net/pypi/v/parser-2gis" alt="PyPi version"/></a>
  <a href="https://pypi.org/project/parser-2gis"><img src="https://badgen.net/pypi/python/parser-2gis" alt="Supported Python versions"/></a>
  <a href="https://github.com/Githab-capibara/parser-2gis/releases"><img src="https://img.shields.io/github/downloads/Githab-capibara/parser-2gis/total.svg" alt="Downloads"/></a>
  <a href="https://github.com/Githab-capibara/parser-2gis"><img src="https://img.shields.io/github/stars/Githab-capibara/parser-2gis" alt="GitHub stars"/></a>
</p>

**Parser2GIS** — мощный инструмент для автоматического сбора данных с сайта [2GIS](https://2gis.ru/) с использованием браузера [Google Chrome](https://google.com/chrome).

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
- [Частые вопросы (FAQ)](#-частые-вопросы-faq)
- [История изменений](#-история-изменений)
- [Поддержка проекта](#-поддержка-проекта)
- [Лицензия](#-лицензия)
- [Контакты](#-контакты)

---

## ℹ️ Описание

Parser2GIS автоматически собирает базу данных предприятий с полной информацией: адреса, контакты, режим работы, рейтинги и отзывы. Работает через браузер Chrome, что обеспечивает обход анти-бот защит.

### 🌍 Поддерживаемые страны и города

| Страна | Городов | Примеры городов |
|--------|---------|-----------------|
| 🇷🇺 Россия | 155 | Москва, Санкт-Петербург, Казань, Екатеринбург, Новосибирск |
| 🇰🇿 Казахстан | 18 | Алматы, Астана, Шымкент, Караганда |
| 🇸🇦 Саудовская Аравия | 14 | Эр-Рияд, Джидда, Мекка, Медина |
| 🇰🇬 Киргизия | 2 | Бишкек, Ош |
| 🇺🇿 Узбекистан | 2 | Ташкент, Самарканд |
| 🇧🇾 Беларусь | 1 | Минск |
| 🇦🇿 Азербайджан | 1 | Баку |
| 🇨🇿 Чехия | 1 | Прага |
| 🇪🇬 Египет | 1 | Новый Каир |
| 🇮🇹 Италия | 1 | Падуя |
| 🇨🇾 Кипр | 1 | Никосия |
| 🇦🇪 ОАЭ | 1 | Дубай |
| 🇨🇱 Чили | 1 | Сантьяго |
| 🇶🇦 Катар | 1 | Доха |
| 🇴🇲 Оман | 1 | Маскат |
| 🇧🇭 Бахрейн | 1 | Манама |
| 🇰🇼 Кувейт | 1 | Эль-Кувейт |
| 🇮🇶 Ирак | 1 | Басра |

**Всего: 204 города в 18 странах**

### 📊 Извлекаемые данные

| Категория | Поля |
|-----------|------|
| **Основная информация** | Наименование, Описание, Рубрики |
| **Адрес** | Полный адрес, Почтовый индекс, Район, Город, Регион, Страна |
| **Координаты** | Широта, Долгота |
| **Контакты** | Телефоны (множественные), E-mail, Веб-сайт |
| **Соцсети** | Instagram, Facebook, VK, WhatsApp, Viber, Telegram, Twitter, YouTube, Skype |
| **Рейтинг** | Средняя оценка, Количество отзывов |
| **Режим работы** | Часы работы, Часовой пояс |
| **Ссылки** | URL карточки 2GIS |

---

## ✨ Возможности

| Возможность | Описание |
|-------------|----------|
| 💰 **Бесплатный** | Открытый исходный код (LGPLv3+) |
| 🤖 **Анти-блокировка** | Обход защит 2GIS через Chrome |
| 🖥️ **Кроссплатформенность** | Windows, Linux, macOS |
| 📄 **3 формата вывода** | CSV, XLSX, JSON |
| 🔗 **Генератор URL** | По городам и рубрикам |
| 🎨 **Два режима** | GUI и CLI |
| ⚙️ **Гибкая настройка** | 20+ параметров конфигурации |
| 🧹 **Контроль памяти** | Сборщик мусора для RAM |
| 🚀 **Авто-навигация** | Переход по страницам результатов |
| 🏢 **Парсинг зданий** | Поддержка ссылок "В здании" |
| 🚉 **Парсинг остановок** | Сбор данных об остановках |
| 📍 **Парсинг фирм** | Поддержка ссылок `/firm/<id>` |

---

## 🚀 Установка

### Требования

| Компонент | Версия | Обязательно |
|-----------|--------|-------------|
| Python | 3.8 – 3.11 | ✅ Да |
| Google Chrome | Любая актуальная | ✅ Да |

### Вариант 1: Готовый исполняемый файл

Скачайте последний релиз: [**Releases**](https://github.com/Githab-capibara/parser-2gis/releases/latest)

- **Windows**: `Parser2GIS.exe`
- **Linux/macOS**: `Parser2GIS`

### Вариант 2: Установка через PyPI

```bash
# Только CLI (командная строка)
pip install parser-2gis

# CLI + GUI (графический интерфейс)
pip install parser-2gis[gui]
```

### Вариант 3: Установка из исходников (для разработки)

```bash
# Клонирование репозитория
git clone https://github.com/Githab-capibara/parser-2gis.git
cd parser-2gis

# Создание виртуального окружения (рекомендуется)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate  # Windows

# Установка пакета в режиме разработки
pip install -e .[dev]

# Установка pre-commit хуков
pre-commit install
```

---

## 📖 Быстрый старт

### Пример 1: Базовый парсинг

```bash
# Парсинг аптек в Москве (CSV)
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" -o pharmacies.csv -f csv
```

### Пример 2: Парсинг с настройками

```bash
# Парсинг ресторанов с ограничением в 100 записей (скрытый режим)
parser-2gis -i "https://2gis.ru/moscow/search/Рестораны" \
    -o restaurants.xlsx -f xlsx \
    --parser.max-records 100 \
    --chrome.headless yes
```

### Пример 3: Парсинг нескольких городов

```bash
# Парсинг аптек в 3 городах
parser-2gis --cities moscow spb kazan \
    --query "Аптеки" \
    -o pharmacies.csv -f csv \
    --chrome.headless yes
```

### Пример 4: Использование в Python

```python
from parser_2gis import main

if __name__ == '__main__':
    main()
```

---

## 💻 Использование

### CLI (командная строка)

#### Обязательные аргументы

| Аргумент | Короткий | Описание | Пример |
|----------|----------|----------|--------|
| `--url` | `-i` | URL с выдачей 2GIS (один или несколько) | `-i "https://2gis.ru/moscow/search/Аптеки"` |
| `--output-path` | `-o` | Путь к результирующему файлу | `-o result.csv` |
| `--format` | `-f` | Формат файла: `csv`, `xlsx`, `json` | `-f csv` |

#### Аргументы для парсинга городов

| Аргумент | Описание | По умолчанию | Пример |
|----------|----------|--------------|--------|
| `--cities` | Коды городов (например: `moscow spb`) | — | `--cities omsk kazan` |
| `--query` | Поисковый запрос для генерации URL | `Организации` | `--query "Рестораны"` |
| `--rubric` | Код рубрики для фильтрации | — | `--rubric "161"` |

#### Аргументы браузера Chrome

| Аргумент | Описание | По умолчанию | Пример |
|----------|----------|--------------|--------|
| `--chrome.binary_path` | Путь к Chrome (если не в PATH) | Авто | `--chrome.binary_path "/usr/bin/google-chrome"` |
| `--chrome.disable-images` | Отключить изображения | `yes` | `--chrome.disable-images no` |
| `--chrome.headless` | **Скрытый режим (без окна)** | `no` | `--chrome.headless yes` |
| `--chrome.silent-browser` | Отключить отладочный вывод | `yes` | `--chrome.silent-browser no` |
| `--chrome.start-maximized` | Развернуть окно браузера | `no` | `--chrome.start-maximized yes` |
| `--chrome.memory-limit` | Лимит RAM (МБ) | 75% от общей | `--chrome.memory-limit 4096` |

#### Аргументы CSV/XLSX

| Аргумент | Описание | По умолчанию |
|----------|----------|--------------|
| `--writer.csv.add-rubrics` | Добавить колонку "Рубрики" | `yes` |
| `--writer.csv.add-comments` | Комментарии к ячейкам | `yes` |
| `--writer.csv.columns-per-entity` | Колонки для множественных значений | `3` |
| `--writer.csv.remove-empty-columns` | Удалить пустые колонки | `yes` |
| `--writer.csv.remove-duplicates` | Удалить дубликаты записей | `yes` |
| `--writer.csv.join_char` | Разделитель для комплексных значений | `; ` |

#### Аргументы парсера

| Аргумент | Описание | По умолчанию |
|----------|----------|--------------|
| `--parser.use-gc` | Включить сборщик мусора | `no` |
| `--parser.gc-pages-interval` | Запуск GC каждые N страниц | `10` |
| `--parser.max-records` | Максимум записей с URL | Авто |
| `--parser.skip-404-response` | Пропускать 404 ответы | `yes` |
| `--parser.delay_between_clicks` | Задержка между кликами (мс) | `0` |

#### Прочие аргументы

| Аргумент | Описание | По умолчанию |
|----------|----------|--------------|
| `--writer.verbose` | Отображать названия позиций | `yes` |
| `--writer.encoding` | Кодировка файла | `utf-8-sig` |

### Примеры использования CLI

#### Базовый парсинг

```bash
# Парсинг аптек в Москве (CSV)
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" -o pharmacies.csv -f csv
```

#### Несколько URL одновременно

```bash
# Парсинг аптек в Москве и Санкт-Петербурге
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
               "https://2gis.ru/spb/search/Аптеки" \
            -o pharmacies.csv -f csv
```

#### Парсинг по городам (рекомендуется!)

```bash
# Парсинг аптек в 3 городах
parser-2gis --cities moscow spb kazan \
            --query "Аптеки" \
            -o pharmacies.csv -f csv
```

#### Парсинг с рубрикой

```bash
# Парсинг ресторанов с рубрикой "Рестораны" (код 161)
parser-2gis --cities moscow spb \
            --query "Рестораны" \
            --rubric "161" \
            -o restaurants.xlsx -f xlsx
```

#### Комбинированный режим (URL + города)

```bash
# Парсинг по URL + дополнительные города
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
            --cities spb kazan \
            --query "Аптеки" \
            -o pharmacies.csv -f csv
```

#### Скрытый режим (без окна браузера)

```bash
# Парсинг в фоновом режиме (Chrome не виден)
parser-2gis -i "https://2gis.ru/moscow/search/Рестораны" \
            -o restaurants.json -f json \
            --chrome.headless yes
```

#### С ограничением записей

```bash
# Максимум 50 записей с каждого URL
parser-2gis -i "https://2gis.ru/moscow/search/Кафе" \
            -o cafes.xlsx -f xlsx \
            --parser.max-records 50
```

#### С отладочной информацией

```bash
# Вывод отладочной информации браузера
parser-2gis -i "https://2gis.ru/moscow/search/Кафе" \
            -o cafes.xlsx -f xlsx \
            --chrome.silent-browser no
```

#### Парсинг с задержкой (анти-детект)

```bash
# Задержка 200мс между кликами
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
            -o pharmacies.csv -f csv \
            --parser.delay_between_clicks 200
```

#### Со сборщиком мусора (для больших объёмов)

```bash
# GC каждые 10 страниц для экономии RAM
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
            -o pharmacies.csv -f csv \
            --parser.use-gc yes \
            --parser.gc-pages-interval 10
```

---

### GUI (графический интерфейс)

Для запуска GUI выполните команду без обязательных аргументов:

```bash
parser-2gis
```

Или установите GUI-версию:

```bash
pip install parser-2gis[gui]
parser-2gis
```

#### Возможности GUI

| Функция | Описание |
|---------|----------|
| ➕ **Добавление URL** | Ручное добавление или импорт из файла |
| 🌍 **Выбор городов** | Визуальный выбор из 204 городов (18 стран) |
| 🔗 **Генератор ссылок** | Автоматическая генерация URL по городам и рубрикам |
| 📁 **Выбор формата** | CSV, XLSX, JSON |
| ⚙️ **Настройки парсера** | Все параметры конфигурации |
| 📊 **Лог в реальном времени** | Просмотр процесса парсинга |
| 🎨 **Современный дизайн** | Удобный интерфейс с тёмной темой |

#### Работа с GUI

1. **Запуск**: `parser-2gis` (без аргументов)
2. **Добавление URL**:
   - Введите URL вручную в поле "URL для парсинга"
   - Или нажмите **"Города"** для выбора из списка
   - Или нажмите **"Редактор"** для работы с несколькими URL
3. **Выбор формата**: CSV, XLSX или JSON
4. **Путь к файлу**: Укажите путь сохранения
5. **Запуск**: Нажмите **"▶ Запуск"**

---

## ⚙️ Конфигурация

Конфигурация хранится в файле `parser-2gis.config` в зависимости от ОС:

| ОС | Путь |
|----|------|
| **Windows** | `C:\Users\%USERPROFILE%\AppData\Local\parser-2gis\parser-2gis.config` |
| **Linux** | `~/.config/parser-2gis/parser-2gis.config` |
| **macOS** | `~/Library/Application Support/parser-2gis/parser-2gis.config` |

### Пример конфигурации

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
│   ├── __init__.py           # Точка входа (main, __version__)
│   ├── main.py               # CLI (парсинг аргументов)
│   ├── config.py             # Конфигурация (Pydantic)
│   ├── common.py             # Утилиты (декораторы, валидация)
│   ├── paths.py              # Пути к данным
│   ├── version.py            # Версия (1.2.1)
│   ├── exceptions.py         # Исключения
│   │
│   ├── chrome/               # Работа с Chrome
│   │   ├── browser.py        # Запуск браузера
│   │   ├── remote.py         # Chrome DevTools Protocol
│   │   ├── dom.py            # DOM-узлы
│   │   ├── options.py        # Опции Chrome
│   │   └── utils.py          # Утилиты Chrome
│   │
│   ├── parser/               # Парсеры данных
│   │   ├── factory.py        # Фабрика парсеров
│   │   ├── options.py        # Опции парсера
│   │   ├── utils.py          # Утилиты парсера
│   │   └── parsers/
│   │       ├── main.py       # Основной парсер (поиск)
│   │       ├── firm.py       # Парсер фирм (/firm/<id>)
│   │       └── in_building.py # Парсер "В здании"
│   │
│   ├── writer/               # Писатели файлов
│   │   ├── factory.py        # Фабрика писателей
│   │   ├── options.py        # Опции писателя
│   │   ├── models/           # Модели данных (Pydantic)
│   │   └── writers/
│   │       ├── csv_writer.py # CSV writer
│   │       ├── xlsx_writer.py # XLSX writer
│   │       └── json_writer.py # JSON writer
│   │
│   ├── logger/               # Логирование
│   │   ├── logger.py         # Настройка логгера
│   │   └── options.py        # Опции логирования
│   │
│   ├── runner/               # Запуск парсера
│   │   ├── runner.py         # Базовый runner
│   │   ├── cli.py            # CLI runner
│   │   └── gui.py            # GUI runner
│   │
│   ├── cli/                  # CLI приложение
│   │   └── app.py            # Запуск CLIRunner
│   │
│   ├── gui/                  # GUI приложение (PySimpleGUI)
│   │   ├── app.py            # Главное окно
│   │   ├── settings.py       # Диалог настроек
│   │   ├── city_selector.py  # Выбор городов
│   │   ├── urls_generator.py # Генератор URL
│   │   └── rubric_selector.py # Выбор рубрик
│   │
│   └── data/                 # Данные
│       ├── cities.json       # Города (204 города)
│       └── rubrics.json      # Рубрики (1786 рубрик)
│
├── testes/                   # Тесты (pytest)
├── scripts/                  # Скрипты обновления данных
├── parser-2gis.py            # Точка входа
└── setup.py                  # Установка пакета
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
| `test_common.py` | Общие утилиты (платформа, декораторы) |
| `test_config.py` | Конфигурация (создание, загрузка) |
| `test_logger.py` | Логирование (уровни, QueueHandler) |
| `test_parser.py` | Интеграционные тесты парсера |
| `test_writer.py` | Писатели файлов (CSV, JSON, XLSX) |
| `test_chrome.py` | Chrome браузер (options, remote) |
| `test_gui_*.py` | Тесты GUI (темы, утилиты) |

### Маркеры тестов

- `slow` — медленные тесты
- `integration` — интеграционные тесты
- `gui` — тесты GUI
- `requires_chrome` — тесты, требующие Chrome
- `requires_network` — тесты, требующие сеть

### Pre-commit

```bash
# Запуск всех хуков
pre-commit run --all-files

# Проверка стиля
flake8 parser_2gis

# Проверка типов
mypy parser_2gis
```

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
- `pyinstaller` — сборка standalone

### Основные зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| `pychrome` | 0.2.4 | Chrome DevTools Protocol |
| `pydantic` | >=1.9.0,<2.0 | Валидация данных |
| `psutil` | >=5.4.8 | Системная память |
| `requests` | >=2.13.0 | HTTP-запросы |
| `xlsxwriter` | >=3.0.5 | Создание XLSX |
| `PySimpleGUI` | 4.59.0 | GUI интерфейс (опционально) |

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

---

## ❓ Частые вопросы (FAQ)

### 🔹 Как запустить парсер в фоновом режиме?

Используйте флаг `--chrome.headless yes`:

```bash
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
    -o pharmacies.csv -f csv \
    --chrome.headless yes
```

Браузер Chrome будет работать без видимого окна.

### 🔹 Как распарсить несколько городов сразу?

Используйте аргумент `--cities`:

```bash
parser-2gis --cities moscow spb kazan \
    --query "Аптеки" \
    -o pharmacies.csv -f csv
```

### 🔹 Как ограничить количество записей?

Используйте `--parser.max-records`:

```bash
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
    -o pharmacies.csv -f csv \
    --parser.max-records 100
```

### 🔹 Как добавить задержку между кликами?

Для обхода анти-бот защит используйте `--parser.delay_between_clicks`:

```bash
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
    -o pharmacies.csv -f csv \
    --parser.delay_between_clicks 200
```

### 🔹 Как уменьшить потребление памяти?

Включите сборщик мусора:

```bash
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
    -o pharmacies.csv -f csv \
    --parser.use-gc yes \
    --parser.gc-pages-interval 10
```

### 🔹 Где хранится конфигурация?

| ОС | Путь |
|----|------|
| Windows | `%APPDATA%\parser-2gis\parser-2gis.config` |
| Linux | `~/.config/parser-2gis/parser-2gis.config` |
| macOS | `~/Library/Application Support/parser-2gis/parser-2gis.config` |

### 🔹 Как обновить список городов?

```bash
python scripts/update_cities_list.py
```

### 🔹 Что делать, если Chrome не найден?

Укажите путь вручную:

```bash
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" \
    -o pharmacies.csv -f csv \
    --chrome.binary_path "/usr/bin/google-chrome"
```

### 🔹 Какие версии Python поддерживаются?

Python **3.8, 3.9, 3.10, 3.11**

### 🔹 Работает ли парсер в России?

Да! Парсер успешно обходит анти-бот блокировки и работает на территории РФ.

---

## 📝 История изменений

### [Невошедшее]

**Исправлено:**
- Исправлена совместимость с Pydantic v2 (замена `.dict()` на `.model_dump()`)
- Улучшена обработка ошибок в скриптах обновления данных
- Переведены комментарии в скриптах на русский язык
- Улучшена читаемость кода и документация

### [1.2.1] — 14-03-2024

**Добавлено:**
- Поддержка парсинга остановок
- Сортировка URL по алфавиту для исключения повторений
- Обновлён список рубрик

### [1.2.0] — 08-02-2024

**Добавлено:**
- Поддержка ссылок организаций `/firm/<id>`
- Обновлён список рубрик и городов

### [1.1.2] — 08-03-2023

**Добавлено:**
- Поддержка Chrome v111
- Новый город Басра (Ирак)

### [1.1.1] — 03-02-2023

**Добавлено:**
- Поля контактов: Telegram, Viber, WhatsApp

### [1.1.0] — 05-01-2023

**Добавлено:**
- Поля "Рейтинг" и "Количество отзывов"
- Запись результата в Excel (XLSX)
- Авто-навигация к странице `/page/<номер>`

[Полная история изменений →](CHANGELOG.md)

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
- **Changelog**: [https://github.com/Githab-capibara/parser-2gis/blob/main/CHANGELOG.md](https://github.com/Githab-capibara/parser-2gis/blob/main/CHANGELOG.md)

---

<p align="center">
  <strong>Parser2GIS © 2022-2025</strong><br>
  Сделано с ❤️ для сообщества
</p>
