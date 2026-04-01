# Contributing to parser-2gis

Спасибо за интерес к проекту parser-2gis! Мы приветствуем вклад от сообщества.

## Содержание

- [Как внести вклад](#как-внести-вклад)
- [Стандарты кода](#стандарты-кода)
- [Процесс разработки](#процесс-разработки)
- [Тестирование](#тестирование)
- [Документация](#документация)
- [Отчёт об ошибках](#отчёт-об-ошибках)
- [Предложение функций](#предложение-функций)

## Как внести вклад

### Типы вклада

Мы принимаем различные виды вклада:

- **Багфиксы** — исправление ошибок
- **Новые функции** — расширение функциональности
- **Документация** — улучшение документации
- **Тесты** — увеличение покрытия тестами
- **Рефакторинг** — улучшение архитектуры кода
- **Производительность** — оптимизация скорости/памяти

### Быстрый старт

1. **Форкните репозиторий**
   ```bash
   # На GitHub нажмите Fork
   ```

2. **Клонируйте форк**
   ```bash
   git clone https://github.com/YOUR_USERNAME/parser-2gis.git
   cd parser-2gis
   ```

3. **Создайте ветку**
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Внесите изменения**

5. **Закоммитьте и отправьте**
   ```bash
   git add .
   git commit -m "Add: your commit message"
   git push origin feature/your-feature-name
   ```

6. **Создайте Pull Request**

## Стандартарты кода

### Требования к коду

- **Python 3.10+** — минимальная версия
- **Типизация** — используйте type hints
- **Docstrings** — документируйте публичные API
- **Стиль** — следуйте PEP 8

### Инструменты

Проект использует:

- **Ruff** — линтер и форматтер
- **Black** — форматирование кода
- **Mypy** — проверка типов
- **Pytest** — тестирование

### Установка зависимостей

```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -e .[dev]

# Установка pre-commit хуков
pre-commit install
```

### Проверка кода

```bash
# Линтинг
ruff check .

# Форматирование
black .

# Проверка типов
mypy parser_2gis/

# Тесты
pytest tests/ -v --cov=parser_2gis
```

### Стиль кода

#### Именование

```python
# Классы — PascalCase
class CacheManager:
    pass

# Функции и переменные — snake_case
def get_data():
    pass

# Константы — UPPER_SNAKE_CASE
MAX_WORKERS = 20

# Приватные методы — _prefix
def _internal_method():
    pass
```

#### Docstrings

Используйте Google style docstrings:

```python
def parse_url(url: str, timeout: int = 30) -> dict:
    """Парсит URL и возвращает данные.

    Args:
        url: URL для парсинга.
        timeout: Таймаут в секундах.

    Returns:
        Словарь с данными.

    Example:
        >>> parse_url("https://2gis.ru/moscow")
        {'name': 'Москва', ...}
    """
```

#### Type Hints

```python
from typing import Optional, List, Dict, Any

def process_data(
    items: List[dict],
    max_count: Optional[int] = None,
    options: Dict[str, Any] | None = None
) -> List[dict]:
    pass
```

## Процесс разработки

### Ветвление

- `main` — основная ветка
- `feature/*` — новые функции
- `bugfix/*` — исправления ошибок
- `docs/*` — документация
- `refactor/*` — рефакторинг

### Коммиты

Следуйте [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Типы:**

- `feat` — новая функция
- `fix` — исправление ошибки
- `docs` — документация
- `style` — форматирование
- `refactor` — рефакторинг
- `test` — тесты
- `chore` — обслуживание

**Примеры:**

```bash
feat(parser): добавить поддержку JSON вывода
fix(cache): исправить утечку памяти в CacheManager
docs(readme): обновить примеры CLI
refactor(parallel): упростить координацию потоков
test(validation): добавить тесты валидации городов
```

### Code Review

Все PR проходят code review:

1. **Автоматическая проверка** — CI/CD пайплайн
2. **Review от мейнтейнера** — проверка кода
3. **Исправление замечаний** — ответ на review
4. **Merge** — слияние после approval

## Тестирование

### Запуск тестов

```bash
# Все тесты
pytest tests/ -v

# С покрытием
pytest tests/ -v --cov=parser_2gis --cov-report=html

# Конкретный файл
pytest tests/test_cache.py -v

# Конкретный тест
pytest tests/test_cache.py::test_cache_get_set -v
```

### Написание тестов

```python
import pytest
from parser_2gis.cache import CacheManager

def test_cache_get_set(tmp_path):
    """Тест кэширования."""
    cache = CacheManager(tmp_path, ttl_hours=24)
    
    # Arrange
    data = {"key": "value"}
    
    # Act
    cache.set("test_url", data)
    result = cache.get("test_url")
    
    # Assert
    assert result == data
```

### Покрытие

Целевое покрытие: **95%+**

```bash
# Проверка покрытия
pytest --cov=parser_2gis --cov-fail-under=95
```

## Документация

### Обновление документации

- **README.md** — основные изменения
- **CHANGELOG.md** — все изменения
- **ARCHITECTURE.md** — архитектурные изменения
- **Docstrings** — изменения API

### Стиль документации

- **Язык** — русский для пользователей, английский для кода
- **Примеры** — всегда приводите примеры использования
- **Скриншоты** — для UI изменений

## Отчёт об ошибках

### Шаблоны отчёта

**Баг:**

```markdown
**Описание:**
Краткое описание ошибки.

**Воспроизведение:**
1. Запустить команду '...'
2. Ввести данные '...'
3. Увидеть ошибку

**Ожидаемое поведение:**
Что должно было произойти.

**Фактическое поведение:**
Что произошло вместо ожидаемого.

**Окружение:**
- OS: Ubuntu 22.04
- Python: 3.11
- Версия parser-2gis: 2.7.0

**Логи:**
```
[ERROR] Сообщение ошибки
```

**Скриншоты:**
При необходимости.
```

**Feature Request:**

```markdown
**Описание:**
Описание новой функции.

**Мотивация:**
Зачем нужна эта функция?

**Пример использования:**
Как это будет работать?

**Альтернативы:**
Какие есть альтернативные решения?
```

### Где создавать

- **GitHub Issues** — https://github.com/Githab-capibara/parser-2gis/issues
- **Выберите шаблон** — Bug Report или Feature Request

## Предложение функций

### Процесс

1. **Создайте Issue** — опишите функцию
2. **Обсуждение** — сообщество оценивает
3. **Одобрение** — мейнтейнеры одобряют
4. **Реализация** — создайте PR
5. **Review** — проверка кода
6. **Merge** — слияние

### Критерии

Функция будет одобрена если:

- ✅ Решает реальную проблему
- ✅ Совместима с архитектурой
- ✅ Имеет тесты
- ✅ Документирована
- ✅ Не ломает обратную совместимость

## Вопросы

### Где задать

- **GitHub Discussions** — общие вопросы
- **GitHub Issues** — баги и фичи
- **Email** — [указать email]

### FAQ

**Q: Как установить?**
```bash
pip install parser-2gis
```

**Q: Как запустить тесты?**
```bash
pytest tests/ -v
```

**Q: Как собрать документацию?**
```bash
# Документация в README.md
```

## Благодарности

Спасибо всем контрибьюторам:

- [@Githab-capibara](https://github.com/Githab-capibara) — основной разработчик
- [Все контрибьюторы](https://github.com/Githab-capibara/parser-2gis/graphs/contributors)

## Лицензия

Проект распространяется под лицензией LGPLv3+.
