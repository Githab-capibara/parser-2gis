# Руководство для разработчиков (Contributing)

Благодарим за интерес к проекту Parser2GIS! Это руководство поможет вам начать работу с проектом.

## 📋 Содержание

- [Начало работы](#-начало-работы)
- [Структура проекта](#-структура-проекта)
- [Запуск проекта](#-запуск-проекта)
- [Тестирование](#-тестирование)
- [Стиль кода](#-стиль-кода)
- [Вклад в проект](#-вклад-в-проект)
- [Создание релиза](#-создание-релиза)

---

## 🚀 Начало работы

### Требования

| Компонент | Версия | Примечание |
|-----------|--------|------------|
| Python | 3.8 – 3.11 | Обязательно |
| Google Chrome | Любая актуальная | Для парсинга |
| Git | Любая актуальная | Для работы с репозиторием |

### Установка для разработки

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

---

## 🏗️ Структура проекта

```
parser-2gis/
├── parser_2gis/              # Основной пакет
│   ├── main.py               # Точка входа CLI
│   ├── config.py             # Конфигурация (Pydantic)
│   ├── common.py             # Общие утилиты
│   ├── version.py            # Версия пакета
│   │
│   ├── chrome/               # Работа с Chrome
│   │   ├── browser.py        # Запуск браузера
│   │   ├── remote.py         # Chrome DevTools Protocol
│   │   └── options.py        # Опции Chrome
│   │
│   ├── parser/               # Парсеры данных
│   │   ├── parsers/
│   │   │   ├── main.py       # Основной парсер
│   │   │   ├── firm.py       # Парсер фирм
│   │   │   └── in_building.py # Парсер "В здании"
│   │   └── options.py        # Опции парсера
│   │
│   ├── writer/               # Писатели файлов
│   │   ├── writers/
│   │   │   ├── csv_writer.py # CSV writer
│   │   │   ├── xlsx_writer.py # XLSX writer
│   │   │   └── json_writer.py # JSON writer
│   │   └── models/           # Модели данных
│   │
│   ├── gui/                  # GUI приложение
│   │   ├── app.py            # Главное окно
│   │   ├── city_selector.py  # Выбор городов
│   │   └── urls_generator.py # Генератор URL
│   │
│   └── data/                 # Данные
│       ├── cities.json       # Города (204 города)
│       └── rubrics.json      # Рубрики (1786 рубрик)
│
├── testes/                   # Тесты (pytest)
├── scripts/                  # Скрипты обновления данных
└── setup.py                  # Установка пакета
```

---

## ▶️ Запуск проекта

### Запуск CLI

```bash
# Запуск с аргументами
parser-2gis -i "https://2gis.ru/moscow/search/Аптеки" -o result.csv -f csv

# Запуск GUI
parser-2gis
```

### Запуск тестов

```bash
# Все тесты
pytest

# Тесты с покрытием
pytest --cov=parser_2gis

# Конкретный тест
pytest testes/test_parser.py
```

### Pre-commit хуки

```bash
# Запуск всех хуков
pre-commit run --all-files

# Проверка стиля
flake8 parser_2gis

# Проверка типов
mypy parser_2gis
```

---

## 🧪 Тестирование

### Запуск тестов

```bash
# Все тесты
pytest

# С покрытием
pytest --cov=parser_2gis --cov-report=html

# С выводом логов
pytest -v -s

# Тесты с маркерами
pytest -m integration
pytest -m slow
```

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
    # Arrange
    url = "https://2gis.ru/moscow/search/Аптеки"
    
    # Act
    parser = MainParser(url, chrome_options, parser_options)
    
    # Assert
    assert parser is not None
    assert parser._url == url
```

---

## 📝 Стиль кода

### Основные правила

- **flake8**: max-line-length=130, игнорируемые правила: E501, W503, C901, W503, E722, E731
- **mypy**: строгая проверка типов
- **Форматирование**: 4 пробела, UTF-8 кодировка
- **Комментарии**: на русском языке

### Пример кода

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

### Pre-commit конфигурация

Файл: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.2.0
    hooks:
      - id: trailing-whitespace
      - id: check-json
      - id: check-ast
  
  - repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
      - id: flake8
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.950
    hooks:
      - id: mypy
```

---

## 🤝 Вклад в проект

### Процесс внесения изменений

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

### Требования к Pull Request

- ✅ Все тесты проходят
- ✅ Pre-commit хуки выполнены
- ✅ Код соответствует стилю проекта
- ✅ Добавлены тесты для новых функций
- ✅ Обновлена документация (при необходимости)

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

**Пример:**
```
feat(parser): добавлена поддержка парсинга остановок

- Добавлен новый парсер для остановок
- Обновлены тесты
- Обновлена документация

Fixes #52
```

---

## 📦 Создание релиза

### Обновление версии

1. Обновите версию в `parser_2gis/version.py`:
   ```python
   version = '1.2.2'
   ```

2. Обновите `CHANGELOG.md`:
   - Добавьте новую секцию с версией
   - Опишите все изменения

3. Закоммитьте изменения:
   ```bash
   git add parser_2gis/version.py CHANGELOG.md
   git commit -m 'chore: release version 1.2.2'
   ```

### Сборка standalone приложения

```bash
# Windows
python setup.py build_standalone

# Linux/Mac
python setup.py build_standalone
```

Исполняемый файл будет создан в папке `dist/`.

### Публикация на PyPI

```bash
# Установка зависимостей
pip install twine

# Сборка пакета
python setup.py sdist bdist_wheel

# Публикация
twine upload dist/*
```

### Создание релиза на GitHub

1. Создайте тег:
   ```bash
   git tag -a v1.2.2 -m 'Release version 1.2.2'
   git push origin v1.2.2
   ```

2. Создайте релиз на GitHub:
   - Перейдите на https://github.com/Githab-capibara/parser-2gis/releases
   - Нажмите "Draft a new release"
   - Выберите тег v1.2.2
   - Добавьте описание из CHANGELOG.md
   - Прикрепите бинарные файлы из `dist/`

---

## 🔧 Утилиты

### Обновление списка городов

```bash
python scripts/update_cities_list.py
```

Загружает данные с `https://data.2gis.com` через Chrome и сохраняет в `parser_2gis/data/cities.json`.

### Обновление списка рубрик

```bash
python scripts/update_rubrics_list.py
```

Загружает данные с `https://hermes.2gis.ru/api/data/availableParameters` и сохраняет в `parser_2gis/data/rubrics.json`.

---

## 📚 Дополнительные ресурсы

- [Документация Pydantic](https://docs.pydantic.dev/)
- [Chrome DevTools Protocol](https://chromedevtools.github.io/devtools-protocol/)
- [PySimpleGUI Documentation](https://pysimplegui.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)

---

## ❓ Вопросы?

- 📖 Прочитайте [README.md](README.md)
- 📝 Посмотрите [CHANGELOG.md](CHANGELOG.md)
- 🐛 Сообщите об ошибке в [Issues](https://github.com/Githab-capibara/parser-2gis/issues)
- 💬 Обсудите в [Discussions](https://github.com/Githab-capibara/parser-2gis/discussions)

---

<p align="center">
  <strong>Благодарим за вклад в Parser2GIS! 🎉</strong>
</p>
