# Parser2GIS

<!-- NOTE: переписано ИИ -->
[![Python](https://img.shields.io/pypi/pyversions/parser-2gis)](https://pypi.org/project/parser-2gis/)
[![License](https://img.shields.io/pypi/l/parser-2gis)](LICENSE)
[![Tests](https://img.shields.io/github/actions/workflow/status/Githab-capibara/parser-2gis/tests.yml)](https://github.com/Githab-capibara/parser-2gis/actions)

Парсер сайта 2GIS для сбора данных об организациях, рубриках и городах.

## Возможности

- **Параллельный парсинг** — одновременная обработка нескольких городов и рубрик
- **Кэширование** — сохранение результатов в SQLite с поддержкой WAL-режима
- **Автоматические повторные попытки** — при ошибках сети и временных сбоях
- **Несколько форматов вывода** — CSV, JSON, XLSX
- **CLI-интерфейс** — удобная командная строка с прогресс-баром
- **Валидация данных** — проверка URL, путей и телефонных номеров
- **Chrome-интеграция** — управление браузером для рендеринга JavaScript

## Установка

```bash
pip install parser-2gis
```

или из исходников:

```bash
pip install -e .
```

## Быстрый старт

### CLI

```bash
# Парсинг организаций по рубрике
parser-2gis --city Москва --rubric "Кафе" --output result.csv

# Параллельный парсинг нескольких городов
parser-2gis --cities Москва Санкт-Петербург Екатеринбург --rubric "Рестораны" --parallel 3

# Использование прокси
parser-2gis --city Москва --rubric "Магазины" --proxy http://user:pass@proxy:8080
```

### Python API

```python
from parser_2gis import ParallelCityParser

parser = ParallelCityParser(
    cities=["Москва", "Санкт-Петербург"],
    rubrics=["Кафе", "Рестораны"],
    parallel_workers=3,
)

results = parser.run()
```

## Конфигурация

Конфигурация хранится в `config.ini`:

```ini
[parser]
max_records = 1000
timeout = 30

[parallel]
workers = 3
max_retries = 3

[chrome]
headless = true
```

## Архитектура

```
parser_2gis/
├── cli/           # Командная строка
├── parser/        # Парсеры страниц 2GIS
├── parallel/      # Параллельный парсинг
├── cache/        # Кэширование (SQLite)
├── writer/        # Запись в файлы
├── validation/    # Валидация данных
├── chrome/       # Управление браузером
└── utils/        # Утилиты
```

## Тестирование

```bash
pytest tests/ -v
```

## Требования

- Python 3.10+
- Chrome/Chromium (для рендеринга JS)
- Зависимости: см. `pyproject.toml`

## Лицензия

GNU Lesser General Public License v3 (LGPL-3.0). Подробности в файле [LICENSE](LICENSE).

## Автор

Andy Trofimov <interlark@gmail.com>