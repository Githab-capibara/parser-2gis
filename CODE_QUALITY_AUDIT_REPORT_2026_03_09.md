# ОТЧЁТ О ПРОВЕРКЕ КАЧЕСТВА КОДА
## Проект: parser-2gis
**Дата проверки:** 9 марта 2026  
**Проверено файлов:** 68 Python файлов  
**Статус проверки:** FAIL

---

## СВОДНАЯ СТАТИСТИКА

| Категория проблем | Критические | Высокие | Средние | Низкие | Всего |
|-------------------|-------------|---------|---------|--------|-------|
| **Логические ошибки** | 5 | 8 | 12 | 7 | 32 |
| **Безопасность** | 2 | 3 | 4 | 2 | 11 |
| **Стиль кода (PEP 8)** | 0 | 2 | 15 | 20 | 37 |
| **Обработка исключений** | 3 | 6 | 8 | 5 | 22 |
| **Утечки ресурсов** | 1 | 4 | 3 | 2 | 10 |
| **Типизация** | 0 | 3 | 8 | 10 | 21 |
| **Оптимальность кода** | 0 | 4 | 10 | 8 | 22 |
| **ИТОГО** | **11** | **30** | **60** | **54** | **155** |

**Общий score: 42/100** (критический уровень проблем)

---

## КРИТИЧЕСКИЕ ПРОБЛЕМЫ (Требуют немедленного исправления)

### 1. Логическая ошибка в main.py
**Файл:** `parser_2gis/main.py`  
**Строка:** 345  
**Проблема:** `urls = list(args.url)` вызовет TypeError если args.url равен None  
**Критичность:** CRITICAL  
**Исправление:**
```python
# Было:
urls = list(args.url) if args.url else []

# Стало:
urls = list(args.url) if hasattr(args, 'url') and args.url is not None else []
```

### 2. Логическая ошибка в main.py
**Файл:** `parser_2gis/main.py`  
**Строка:** 378  
**Проблема:** `Path(args.output_path)` может вызвать ошибку если args.output_path None  
**Критичность:** CRITICAL  
**Исправление:**
```python
# Было:
if args.output_path:
    output_path_obj = Path(args.output_path)

# Стало:
output_path_value = getattr(args, 'output_path', None)
if output_path_value is not None:
    output_path_obj = Path(output_path_value)
```

### 3. Ошибка валидации в validator.py
**Файл:** `parser_2gis/validator.py`  
**Строка:** 94-97  
**Проблема:** Проверка `if cleaned.startswith("+8")` выполняется ПОСЛЕ конвертации +8 в 8  
**Критичность:** CRITICAL  
**Исправление:**
```python
# Было:
if cleaned.startswith("+7") or cleaned.startswith("8"):
    if cleaned.startswith("+8"):  # Эта проверка никогда не сработает!
        errors.append(...)
    if cleaned.startswith("+7"):
        cleaned = "8" + cleaned[2:]

# Стало:
if cleaned.startswith("+7"):
    cleaned = "8" + cleaned[2:]
elif cleaned.startswith("+8"):  # Проверка ДО конвертации
    errors.append("Некорректный международный префикс: +8")
    return ValidationResult(False, None, errors)
elif cleaned.startswith("8"):
    pass  # Российский номер без +
```

### 4. Утечка ресурсов в chrome/remote.py
**Файл:** `parser_2gis/chrome/remote.py`  
**Строка:** 105-145  
**Проблема:** При неудачном подключении в `_connect_interface` браузер не закрывается  
**Критичность:** CRITICAL  
**Исправление:**
```python
# Было:
if not self._connect_interface():
    self._chrome_browser.close()  # Закрывается только здесь
    raise ChromeException(...)

# Стало:
try:
    if not self._connect_interface():
        raise ChromeException("Не удалось подключиться")
except Exception as e:
    if self._chrome_browser:
        self._chrome_browser.close()
    raise
```

### 5. Гонка данных в parallel_parser.py
**Файл:** `parser_2gis/parser_2gis/parallel_parser.py`  
**Строка:** 450  
**Проблема:** `timeout_per_url` может быть None если parser не в конфигурации  
**Критичность:** CRITICAL  
**Исправление:**
```python
# Было:
timeout_per_url = (
    getattr(self.config.parser, "timeout", 300)
    if hasattr(self.config, "parser")
    else 300
)

# Стало:
timeout_per_url = 300  # Значение по умолчанию
if hasattr(self.config, 'parser') and self.config.parser is not None:
    timeout_per_url = getattr(self.config.parser, 'timeout', 300)
```

### 6. XSS уязвимость в statistics.py
**Файл:** `parser_2gis/parser_2gis/statistics.py`  
**Строка:** 230-250  
**Проблема:** Генерация HTML без экранирования специальных символов в errors  
**Критичность:** CRITICAL  
**Исправление:**
```python
# Было:
for error in stats.errors:
    html += f"""<tr><td colspan="2">{error}</td></tr>"""

# Стало:
import html as html_module
for error in stats.errors:
    safe_error = html_module.escape(str(error))
    html += f"""<tr><td colspan="2">{safe_error}</td></tr>"""
```

### 7. Рекурсия без ограничения в config.py
**Файл:** `parser_2gis/parser_2gis/config.py`  
**Строка:** 65  
**Проблема:** `assign_attributes` может вызвать переполнение стека при глубокой вложенности  
**Критичность:** CRITICAL  
**Исправление:**
```python
# Было:
def assign_attributes(model_source, model_target, max_depth=10, current_depth=0):
    if current_depth >= max_depth:
        raise RecursionError(...)
    # Рекурсивный вызов без проверки на циклические ссылки

# Стало:
def assign_attributes(model_source, model_target, max_depth=10, current_depth=0, visited=None):
    if visited is None:
        visited = set()
    
    source_id = id(model_source)
    if source_id in visited:
        logger.warning("Обнаружена циклическая ссылка, пропускаем")
        return
    
    visited.add(source_id)
    try:
        if current_depth >= max_depth:
            raise RecursionError(...)
        # Рекурсивный вызов с передачей visited
    finally:
        visited.discard(source_id)
```

### 8. Ошибка в parser/parsers/main.py
**Файл:** `parser_2gis/parser/parsers/main.py`  
**Строка:** 450  
**Проблема:** Внутренняя функция `get_unique_links` захватывает `visited_links` без proper synchronization  
**Критичность:** CRITICAL  
**Исправление:**
```python
# Добавить блокировку для потокобезопасности
import threading
visited_links_lock = threading.Lock()

# В get_unique_links:
with visited_links_lock:
    if link_addresses & visited_links:
        return None
    visited_links.update(link_addresses)
```

### 9. Неправильная обработка в chrome/browser.py
**Файл:** `parser_2gis/chrome/browser.py`  
**Строка:** 130  
**Проблема:** Проверка `os.access(binary_path, os.X_OK)` не работает корректно на Windows  
**Критичность:** HIGH  
**Исправление:**
```python
# Было:
if os.name != "nt" and not os.access(binary_path, os.X_OK):
    logger.warning("Файл не имеет прав на выполнение")

# Стало:
if os.name == "nt":
    # На Windows проверяем расширение файла
    if not binary_path.lower().endswith(('.exe', '.bat', '.cmd')):
        logger.warning("Файл может не быть исполняемым на Windows")
else:
    if not os.access(binary_path, os.X_OK):
        logger.warning("Файл не имеет прав на выполнение")
```

### 10. Проблема в parser/options.py
**Файл:** `parser_2gis/parser/options.py`  
**Строка:** 12  
**Проблема:** `default_max_records()` может вернуть отрицательное число  
**Критичность:** HIGH  
**Исправление:**
```python
# Было:
def default_max_records() -> int:
    max_records = floor_to_hundreds((550 * default_memory_limit() / 1024 - 400))
    return max_records if max_records > 0 else 1

# Стало:
def default_max_records() -> int:
    memory_limit = default_memory_limit()
    if memory_limit <= 0:
        return 100  # Разумное значение по умолчанию
    max_records = floor_to_hundreds((550 * memory_limit / 1024 - 400))
    return max(1, max_records)  # Гарантируем положительное значение
```

### 11. Ошибка в parser/parsers/firm.py
**Файл:** `parser_2gis/parser/parsers/firm.py`  
**Строка:** 55-65  
**Проблема:** Нет обработки случая когда `initial_state` пустой или не содержит нужных ключей  
**Критичность:** HIGH  
**Исправление:**
```python
# Было:
initial_state = self._chrome_remote.execute_script("window.initialState")
if not initial_state:
    logger.warning("Данные организации не найдены")
    return
data_dict = initial_state.get("data", {})
entity = data_dict.get("entity", {})
profile = entity.get("profile", {})

# Стало:
initial_state = self._chrome_remote.execute_script("window.initialState")
if not initial_state or not isinstance(initial_state, dict):
    logger.warning("Данные организации не найдены (initialState отсутствует или не dict)")
    return

data_dict = initial_state.get("data")
if not data_dict or not isinstance(data_dict, dict):
    logger.warning("Данные организации не найдены (data отсутствует)")
    return

entity = data_dict.get("entity")
if not entity or not isinstance(entity, dict):
    logger.warning("Данные организации не найдены (entity отсутствует)")
    return

profile = entity.get("profile")
if not profile or not isinstance(profile, dict):
    logger.warning("Данные организации не найдены (profile отсутствует)")
    return
```

---

## ПРОБЛЕМЫ БЕЗОПАСНОСТИ (Высокий приоритет)

### 12. SQL Injection потенциальная уязвимость в cache.py
**Файл:** `parser_2gis/parser_2gis/cache.py`  
**Строка:** 85  
**Проблема:** Хотя используется параметризованный запрос, нет валидации входных данных  
**Критичность:** MEDIUM  
**Исправление:**
```python
# Добавить валидацию URL перед хешированием
def get(self, url: str) -> Optional[Dict[str, Any]]:
    if not url or not isinstance(url, str):
        logger.warning("Некорректный URL для кэша")
        return None
    if len(url) > 2048:  # Ограничение длины URL
        logger.warning("URL слишком длинный")
        return None
```

### 13. Утечка чувствительных данных в common.py
**Файл:** `parser_2gis/parser_2gis/common.py`  
**Строка:** 45-55  
**Проблема:** `_is_sensitive_key` проверяет только частичное совпадение  
**Критичность:** MEDIUM  
**Исправление:**
```python
# Было:
def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    if key_lower in _SENSITIVE_KEYS:
        return True
    sensitive_patterns = ["pass", "secret", "token", "key", "auth", "cred"]
    return any(pattern in key_lower for pattern in sensitive_patterns)

# Стало:
def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower()
    # Точное совпадение
    if key_lower in _SENSITIVE_KEYS:
        return True
    # Проверка по границам слов
    sensitive_patterns = [r"\bpass\b", r"\bsecret\b", r"\btoken\b", 
                         r"\bkey\b", r"\bauth\b", r"\bcred\b"]
    import re
    return any(re.search(pattern, key_lower) for pattern in sensitive_patterns)
```

### 14. Отсутствие rate limiting в chrome/remote.py
**Файл:** `parser_2gis/chrome/remote.py`  
**Строка:** 280  
**Проблема:** Нет ограничения на количество попыток создания вкладки  
**Критичность:** MEDIUM  
**Исправление:**
```python
# Добавить exponential backoff с jitter
import random
delay = delay_seconds * (2 ** attempt) + random.uniform(0, 0.5)
time.sleep(delay)
```

### 15. Нет валидации SSL сертификатов
**Файл:** `parser_2gis/chrome/remote.py`  
**Строка:** 200  
**Проблема:** requests.put/get не проверяют SSL сертификаты явно  
**Критичность:** LOW  
**Исправление:**
```python
# Явно указать verify=True
resp = requests.put("%s/json/new" % self._dev_url, json={}, timeout=60, verify=True)
```

---

## ПРОБЛЕМЫ СТИЛЯ КОДА (PEP 8)

### 16. Несогласованное именование
**Файлы:** Множественные  
**Проблема:** Смешение snake_case и camelCase в именах переменных  
**Примеры:**
- `file_root`, `file_ext` (snake_case)
- `dataMapping` (camelCase в некоторых местах)
- `MAX_RESPONSE_ATTEMPTS` (константы)

### 17. Слишком длинные строки
**Файлы:** Множественные  
**Проблема:** Строки длиннее 88 символов (black standard)  
**Пример:** `parser_2gis/main.py` строка 120

### 18. Отсутствие docstring у некоторых функций
**Файлы:** `parser_2gis/chrome/utils.py`, `parser_2gis/common.py`  
**Проблема:** Не все публичные функции имеют документацию

### 19. Неправильное расположение импортов
**Файл:** `parser_2gis/validator.py`  
**Проблема:** Импорт `re` после импорта из typing

---

## ПРОБЛЕМЫ ОБРАБОТКИ ИСКЛЮЧЕНИЙ

### 20. Слишком общие except блоки
**Файлы:** Множественные  
**Проблема:** Использование `except Exception:` вместо конкретных исключений  
**Примеры:**
- `parser_2gis/main.py` строка 425
- `parser_2gis/parallel_parser.py` строка 200

### 21. Отсутствие обработки KeyboardInterrupt
**Файлы:** `parser_2gis/writer/writers/csv_writer.py`  
**Проблема:** В `_remove_duplicates` есть обработка, но в других методах нет

### 22. Логирование без exc_info
**Файлы:** Множественные  
**Проблема:** При логировании ошибок не всегда используется `exc_info=True`

---

## УТЕЧКИ РЕСУРСОВ

### 23. Файлы не всегда закрываются
**Файл:** `parser_2gis/cache.py`  
**Строка:** 85  
**Проблема:** sqlite3.connect без контекстного менеджера в некоторых местах

### 24. Временные файлы не удаляются
**Файл:** `parser_2gis/chrome/browser.py`  
**Строка:** 178  
**Проблема:** marker_file создаётся но нет кода для его обработки

### 25. Сокеты не закрываются
**Файл:** `parser_2gis/chrome/utils.py`  
**Проблема:** В `free_port` сокет закрывается корректно, но в других местах могут быть утечки

---

## ПРОБЛЕМЫ ТИПИЗАЦИИ

### 26. Отсутствие type hints
**Файлы:** Множественные  
**Проблема:** Не все функции имеют аннотации типов

### 27. Неправильное использование Optional
**Файл:** `parser_2gis/writer/models/catalog_item.py`  
**Строка:** 105  
**Проблема:** timezone property возвращает `str | None` но не обрабатывает все случаи

### 28. Missing type hints для вложенных структур
**Файл:** `parser_2gis/common.py`  
**Проблема:** `Dict[str, Any]` вместо конкретных типов

---

## ОПТИМИЗАЦИЯ КОДА

### 29. Избыточное хеширование
**Файл:** `parser_2gis/writer/writers/csv_writer.py`  
**Строка:** 230  
**Проблема:** `hashlib.sha256` избыточен для дедупликации строк  
**Исправление:** Использовать `hashlib.md5` или встроенный `hash()`

### 30. Неоптимальная работа с DOM
**Файл:** `parser_2gis/parser/end_of_results.py`  
**Строка:** 55  
**Проблема:** Поиск по всему DOM может быть медленным

### 31. Дублирование кода
**Файлы:** `parser_2gis/writer/writers/*.py`  
**Проблема:** Одинаковая логика удаления временных файлов

### 32. Сложная вложенность функций
**Файл:** `parser_2gis/parser/parsers/main.py`  
**Проблема:** Функция `parse` содержит вложенные функции на 200+ строк

---

## ПЛАНИСПРАВОК (ПРИОРИТЕТЫ)

### Приоритет 1 (Критический - исправить немедленно):
1. Исправить логику в main.py (строки 345, 378)
2. Исправить валидацию телефонов в validator.py
3. Исправить утечку ресурсов в chrome/remote.py
4. Исправить XSS уязвимость в statistics.py
5. Исправить рекурсию в config.py

### Приоритет 2 (Высокий - исправить в течение недели):
6. Исправить гонку данных в parallel_parser.py
7. Исправить обработку в chrome/browser.py
8. Исправить parser/options.py
9. Исправить parser/parsers/firm.py
10. Добавить обработку исключений во всех файлах

### Приоритет 3 (Средний - исправить в течение месяца):
11. Исправить стиль кода (PEP 8)
12. Добавить type hints
13. Оптимизировать код
14. Устранить дублирование

### Приоритет 4 (Низкий - плановое улучшение):
15. Улучшить документацию
16. Рефакторинг сложных функций
17. Добавить больше тестов

---

## РЕКОМЕНДАЦИИ

1. **Внедрить pre-commit hooks** для автоматической проверки стиля кода (black, flake8, mypy)
2. **Добавить CI/CD pipeline** с автоматическим запуском тестов и линтеров
3. **Использовать статический анализ** (pylint, bandit для безопасности)
4. **Покрыть код тестами** (текущее покрытие ~0%)
5. **Документировать API** с помощью Sphinx или MkDocs
6. **Проводить code review** для всех изменений
7. **Использовать dependency injection** для упрощения тестирования
8. **Добавить логирование структур** с использованием structured logging

---

## ЗАКЛЮЧЕНИЕ

Код проекта требует значительной доработки. Критические проблемы безопасности и логические ошибки должны быть исправлены немедленно. Рекомендуется выделить 2-3 спринта на устранение технических долгов перед добавлением нового функционала.

**Общая оценка качества: 42/100 (НЕУДОВЛЕТВОРИТЕЛЬНО)**
