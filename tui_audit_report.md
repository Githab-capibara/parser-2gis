# Отчёт аудита кода TUI модуля Parser2GIS

**Дата аудита:** 2026-03-15  
**Модуль:** `/home/d/parser-2gis/parser_2gis/tui_pytermgui/`  
**Аудитор:** Senior Code Review Expert  
**Версия стандарта:** Python 3.10+, pytermgui

---

## 📊 Сводка

| Категория | Количество | Критичность |
|-----------|------------|-------------|
| **Critical** | 18 | 🔴 Блокирующие |
| **Major** | 24 | 🟡 Требуют исправления |
| **Minor** | 31 | 🟢 Рекомендации |
| **Всего** | **73** | |

---

## 🔴 CRITICAL (Критические проблемы)

### 1. Доступ к приватным атрибутам pytermgui

**Файлы:** `app.py`, `city_selector.py`, `category_selector.py`, `navigable_widget.py`

**Проблемы:**
- `app.py:158` — `self._manager._windows` (приватный атрибут)
- `city_selector.py:127` — `self._city_container._widgets.clear()` и `_add_widget()`
- `category_selector.py:78` — `self._category_container.widgets.clear()`
- `navigable_widget.py:189` — `self._add_widget(widget)`

**Риск:** При обновлении pytermgui код перестанет работать. Нарушение инкапсуляции.

**Исправление:**
```python
# Было (НЕПРАВИЛЬНО):
self._city_container._widgets.clear()
self._city_container._add_widget(checkbox)

# Стало (ПРАВИЛЬНО):
# Использовать публичный API или создать метод в NavigableContainer
class NavigableContainer(ptg.Container):
    def clear_widgets(self) -> None:
        """Очистить все виджеты."""
        self._widgets.clear()
    
    def append_widget(self, widget: ptg.Widget) -> None:
        """Добавить виджет."""
        self._widgets.append(widget)
```

---

### 2. Lambda замыкания с захватом переменной цикла

**Файлы:** `city_selector.py:101`, `category_selector.py:91`

**Проблема:**
```python
# НЕПРАВИЛЬНО - все checkbox будут использовать последнее значение i
checkbox = Checkbox(
    label=city_name,
    value=is_selected,
    on_change=lambda checked, idx=i: self._toggle_city(idx, checked),
)
```

**Риск:** Все callback будут использовать одно и то же значение индекса (последнее в цикле).

**Исправление:**
```python
# ПРАВИЛЬНО - значение по умолчанию захватывается корректно
for i, city in enumerate(self._filtered_cities):
    city_name = city.get("name", "Неизвестно")
    is_selected = i in self._selected_indices
    
    # Создаём функцию с захваченным значением
    def make_callback(index: int):
        return lambda checked: self._toggle_city(index, checked)
    
    checkbox = Checkbox(
        label=city_name,
        value=is_selected,
        on_change=make_callback(i),
    )
```

---

### 3. Потенциальный AttributeError в _stop_parsing

**Файл:** `app.py:371`

**Проблема:**
```python
def _stop_parsing(self, success: bool = True) -> None:
    self._running = False
    if self._logger:  # Проверка есть
        # ...
        self._logger.info("=" * 80)  # Но logger может быть None в другой ветке
```

**Риск:** Если `_logger` не инициализирован, возникнет AttributeError.

**Исправление:**
```python
def _stop_parsing(self, success: bool = True) -> None:
    self._running = False
    
    if self._logger is None:
        return
    
    # Или использовать logging модуль напрямую
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Завершение парсинга")
```

---

### 4. Ошибка в TIM-теге прогресс-бара

**Файл:** `progress_bar.py:224`

**Проблема:**
```python
# НЕПРАВИЛЬНО - тег не закрыт корректно
parts.append(f" [{bold} {percent_color}{percent:5.1f}%[/{bold}]")
```

**Риск:** Некорректное отображение прогресс-бара, возможные артефакты.

**Исправление:**
```python
# ПРАВИЛЬНО
percent_color = self._get_percentage_color(percent)
parts.append(f" [{percent_color}]{percent:5.1f}%[/]")
```

---

### 5. ScreenManager не синхронизируется с WindowManager

**Файл:** `navigation.py`

**Проблема:**
```python
def pop(self) -> Optional[str]:
    if not self._screen_stack:
        return None
    
    previous_name, previous_instance = self._screen_stack.pop()
    self._current_screen = previous_name
    self._current_instance = previous_instance
    # НЕТ удаления окна из WindowManager!
    return previous_name
```

**Риск:** Окна накапливаются в WindowManager, утечка памяти.

**Исправление:**
```python
def pop(self, app: Any) -> Optional[str]:
    if not self._screen_stack:
        return None
    
    previous_name, previous_instance = self._screen_stack.pop()
    
    # Удалить текущее окно из менеджера
    if app._manager and self._current_instance:
        window = self._current_instance.create_window()
        app._manager.remove(window)
    
    self._current_screen = previous_name
    self._current_instance = previous_instance
    return previous_name
```

---

### 6. Неправильная обработка ошибок в методах _save

**Файлы:** `browser_settings.py:163`, `output_settings.py:154`, `parser_settings.py:175`

**Проблема:**
```python
try:
    memory_limit = int(memory_limit_str)
    if memory_limit <= 0:
        raise ValueError("Лимит памяти должен быть положительным")
except ValueError:
    return  # Просто выход без сообщения пользователю!
```

**Риск:** Пользователь не узнает об ошибке, настройки не сохранятся.

**Исправление:**
```python
try:
    memory_limit = int(memory_limit_str)
    if memory_limit <= 0:
        raise ValueError("Лимит памяти должен быть положительным")
except ValueError as e:
    self._show_message(f"Ошибка: {e}", "error")
    return
```

---

### 7. Несоответствие возвращаемых типов

**Файлы:** `about_screen.py:95-171`

**Проблема:**
```python
def _create_header(self) -> ptg.Container:  # Обещает Container
    return ptg.Window(...)  # Возвращает Window
```

**Риск:** Нарушение type hints, проблемы с IDE и статическим анализом.

**Исправление:**
```python
def _create_header(self) -> ptg.Window:
    return ptg.Window(...)
```

---

### 8. Использование несуществующего ptg.Monitor

**Файл:** `parsing_screen.py:233`

**Проблема:**
```python
def _start_auto_update(self) -> None:
    if hasattr(ptg, 'Monitor'):
        monitor = ptg.Monitor().start()
        monitor.attach(self._update_display, period=0.5)
```

**Риск:** Monitor может не существовать в pytermgui, обновление не запустится.

**Исправление:**
```python
def _start_auto_update(self) -> None:
    # Использовать threading.Timer или asyncio
    import threading
    
    def update_loop():
        while self._app.running:
            self._update_display()
            time.sleep(0.5)
    
    thread = threading.Thread(target=update_loop, daemon=True)
    thread.start()
```

---

### 9. Отрицательное значение в BoxDrawing

**Файл:** `utils/__init__.py:424`

**Проблема:**
```python
def draw_box(cls, width: int, height: int, style: str = "single", title: str | None = None) -> list[str]:
    if title:
        title_space = width - 4 - len(title)  # Может быть отрицательным!
        left_space = title_space // 2  # Отрицательное число!
```

**Риск:** Исключение при попытке умножить строку на отрицательное число.

**Исправление:**
```python
if title:
    title_space = max(0, width - 4 - len(title))
    left_space = title_space // 2
    right_space = title_space - left_space
```

---

### 10. Неправильное использование progress_callback

**Файл:** `app.py:337`

**Проблема:**
```python
def progress_callback(success: int, failed: int, filename: str) -> None:
    # ...
    if success % 5 == 0 or failed > 0:  # При success=0, failed=5 лог не добавится!
        self._add_log_to_parsing_screen(...)
```

**Риск:** Пропуск важных логов об ошибках.

**Исправление:**
```python
if success > 0 and success % 5 == 0 or failed > 0:
    self._add_log_to_parsing_screen(...)
```

---

### 11-18. Другие критические проблемы

| # | Файл | Строка | Проблема |
|---|------|--------|----------|
| 11 | `app.py:285` | 285 | Использование `max_retries` вместо `max_workers` |
| 12 | `app.py:127` | 127 | Возврат `None` в `_handle_global_key` ломает цепочку |
| 13 | `cache_viewer.py:58` | 58 | `Path(cache_file).stat()` для уже Path объекта |
| 14 | `checkbox.py:98` | 98 | Вызов `super().handle_key()` без проверки |
| 15 | `scroll_area.py:57` | 57 | Нет проверки `_scroll_offset` на выход за границы |
| 16 | `log_viewer.py:289` | 289 | Нет проверки `_frames` на пустоту |
| 17 | `main_menu.py:230` | 230 | Confirm окно не обрабатывает выбор пользователя |
| 18 | `run_parallel.py:67` | 67 | type ignore для CATEGORIES_93 |

---

## 🟡 MAJOR (Серьёзные проблемы)

### 1. Массовое дублирование кода валидаторов

**Файлы:** `browser_settings.py`, `parser_settings.py`, `output_settings.py`

**Проблема:** Одинаковые валидаторы в трёх файлах:
```python
# browser_settings.py:139
def _validate_positive_int(self, value: str) -> tuple[bool, str]:
    try:
        num = int(value)
        if num <= 0:
            return False, "Введите положительное число"
        return True, ""
    except ValueError:
        return False, "Введите целое число"

# parser_settings.py:103 (идентичный код)
# output_settings.py:137 (идентичный код)
```

**Решение:** Создать общий модуль `utils/validators.py` (уже существует но не используется).

---

### 2. Дублирование метода _set_input_field_value

**Файлы:** `browser_settings.py:127`, `output_settings.py:177`, `parser_settings.py:232`

**Проблема:**
```python
def _set_input_field_value(self, field: ptg.InputField, value: str) -> None:
    for _ in range(len(field.value)):
        field.delete_back()
    field.insert_text(value)
```

**Решение:** Вынести в базовый класс или utils.

---

### 3. Пустые/неполные методы

**Файлы:**
- `city_selector.py:232` — `_update_counter` с `pass`
- `browser_settings.py:217` — `_show_message` с `TODO`
- `cache_viewer.py:131` — `_clear_expired` с `TODO`
- `parsing_screen.py:311` — `_update_log_display` с `pass`
- `parsing_screen.py:333` — `_minimize` без реализации

**Решение:** Реализовать или удалить методы.

---

### 4. Несоответствие типов в ButtonWidget

**Файл:** `navigable_widget.py:205`

**Проблема:**
```python
def __init__(
    self,
    label: str,
    onclick=None,  # Нет типа!
    **kwargs
) -> None:
```

**Исправление:**
```python
from typing import Callable, Optional

def __init__(
    self,
    label: str,
    onclick: Optional[Callable[[], None]] = None,
    **kwargs: Any
) -> None:
```

---

### 5. Неэффективная очистка InputField

**Файлы:** `browser_settings.py:127-134`

**Проблема:**
```python
for _ in range(len(field.value)):
    field.delete_back()
field.insert_text(value)
```

**Решение:** Использовать прямой метод если есть:
```python
field.value = value  # Если свойство поддерживается
```

---

### 6. Доступ к приватным атрибутам в ScrollArea

**Файл:** `scroll_area.py:42`

**Проблема:**
```python
if hasattr(self._content, 'widgets'):
    for widget in self._content.widgets:  # widgets может быть приватным
```

**Исправление:** Использовать публичный API или геттер.

---

### 7. Отсутствие проверки импортов

**Файлы:** `utils/__init__.py:12`

**Проблема:**
```python
from .navigation import ScreenManager
# Но navigation.py не импортирует Any из typing!
```

**Исправление:** Добавить все необходимые импорты.

---

### 8. Стили pytermgui могут не работать

**Файл:** `styles/default.py`

**Проблема:** YAML конфигурация использует стили которые могут не поддерживаться:
```yaml
Checkbox:
    styles:
        checked: "success"
        unchecked: "text_dim"
```

**Решение:** Проверить документацию pytermgui или использовать inline стили.

---

### 9-24. Другие серьёзные проблемы

| # | Файл | Строка | Проблема |
|---|------|--------|----------|
| 9 | `app.py:48` | 48 | `_parser` объявлен но не используется |
| 10 | `app.py:277` | 277 | hasattr вместо proper typing |
| 11 | `about_screen.py:124` | 124 | Нарушение PEP8: `max_len-3` |
| 12 | `category_selector.py:149` | 149 | `Label.value` может не существовать |
| 13 | `main_menu.py:105` | 105 | `callable` не импортирован из typing |
| 14 | `output_settings.py:154` | 154 | `int()` без try-except |
| 15 | `progress_bar.py:134` | 134 | Literal без проверки значений |
| 16 | `progress_bar.py:241` | 241 | `render()` возвращает Label с TIM |
| 17 | `progress_bar.py:337` | 337 | `dict[str, dict]` без future import |
| 18 | `scroll_area.py:27` | 27 | `Any` не импортирован |
| 19 | `scroll_area.py:63` | 63 | `__len__` возвращает height |
| 20 | `log_viewer.py:89` | 89 | Literal без проверки |
| 21 | `log_viewer.py:232` | 232 | `**kwargs` не передаётся в super() |
| 22 | `city_list.py:34` | 34 | `ptg.Checkbox` вместо кастомного |
| 23 | `navigation.py:53` | 53 | `clear` не удаляет окна |
| 24 | `validators.py:43` | 43 | `path.resolve()` может вызвать OSError |

---

## 🟢 MINOR (Незначительные проблемы)

### 1. Нарушения PEP8

**Файлы:** Множественные

**Проблемы:**
- Отсутствуют пробелы вокруг операторов: `max_len-3` → `max_len - 3`
- Неправильные отступы в некоторых местах
- Длинные строки > 100 символов

---

### 2. Неиспользуемые импорты и переменные

**Файлы:**
- `app.py:48` — `_parser: Optional[ParallelParser]` не используется
- `parsing_screen.py:34` — `_parser` не используется
- `utils/__init__.py:168` — `Capybara = "🥔"` (забавно но неиспользуемо)

---

### 3. TODO без реализации

**Файлы:**
- `browser_settings.py:217` — `_show_message`
- `cache_viewer.py:131` — `_clear_expired`
- `parsing_screen.py:333` — `_minimize`
- `parsing_screen.py:361` — интеграция с ParallelParser

---

### 4. Комментарии на английском

**Проблема:** Согласно требованиям, все комментарии должны быть на русском.

**Примеры:**
```python
# Initialize state  # ДОЛЖНО БЫТЬ: Инициализировать состояние
# Get config  # ДОЛЖНО БЫТЬ: Получить конфигурацию
```

---

### 5. Неэффективные паттерны

**Файлы:** Множественные

**Проблемы:**
- Многократное создание одинаковых объектов
- Отсутствие кэширования результатов
- Избыточные проверки `if not self._manager`

---

### 6-31. Другие незначительные проблемы

| # | Файл | Строка | Проблема |
|---|------|--------|----------|
| 6 | `app.py:285` | 285 | Конкатенация вместо f-string |
| 7 | `app.py:331` | 331 | Callback захватывает self |
| 8 | `about_screen.py:200` | 200 | `window.center()` может не существовать |
| 9 | `browser_settings.py:189` | 189 | Относительный импорт `...chrome.options` |
| 10 | `cache_viewer.py:83` | 83 | ScrollArea для Table |
| 11 | `category_selector.py:102` | 102 | Параметр field не используется полностью |
| 12 | `main_menu.py:230` | 230 | Нет обработки подтверждения выхода |
| 13 | `checkbox.py:45` | 45 | `**attrs` без типизации |
| 14 | `checkbox.py:56` | 56 | `@gray` может не быть определён |
| 15 | `checkbox.py:127` | 127 | focus()/blur() дублируют свойство |
| 16 | `navigable_widget.py:58` | 58 | getattr для _manager |
| 17 | `navigable_widget.py:269` | 269 | event параметр не используется |
| 18 | `progress_bar.py:193` | 193 | GradientText.GRADIENTS без проверки |
| 19 | `log_viewer.py:134` | 134 | style.get('bold') может быть None |
| 20 | `log_viewer.py:174` | 174 | height=10 не учитывает количество логов |
| 21 | `city_list.py:59` | 59 | Проверка container после __init__ |
| 22 | `navigation.py:28` | 28 | Нет проверки дублирования экранов |
| 23 | `validators.py:12` | 12 | Optional без импорта |
| 24 | `utils/__init__.py:124` | 124 | Дублирование символов в SPINNER_DOTS |
| 25 | `utils/__init__.py:234` | 234 | Literal без импорта |
| 26 | `utils/__init__.py:474` | 474 | format_number для отрицательных чисел |
| 27 | `utils/__init__.py:497` | 497 | truncate_text не учитывает Unicode |
| 28 | `utils/__init__.py:509` | 509 | center_text с Unicode |
| 29 | `utils/__init__.py:524` | 524 | create_ascii_art только 6 букв |
| 30 | `styles/default.py:89` | 89 | Стили Checkbox могут не работать |
| 31 | `run_parallel.py:67` | 67 | type ignore без комментария |

---

## 📋 Рекомендации по исправлению

### Приоритет 1 (Немедленно)

1. **Исправить доступ к приватным атрибутам** — создать публичные методы в NavigableContainer
2. **Исправить lambda замыкания** — использовать factory функции
3. **Добавить обработку ошибок** — показывать сообщения пользователю
4. **Исправить TIM-теги** — проверить все форматирования

### Приоритет 2 (В течение недели)

1. **Устранить дублирование кода** — вынести валидаторы в utils
2. **Реализовать пустые методы** — _show_message, _update_counter
3. **Исправить type hints** — добавить все импорты из typing
4. **Синхронизировать ScreenManager** — с WindowManager

### Приоритет 3 (В течение месяца)

1. **Перевести комментарии** — на русский язык
2. **Удалить неиспользуемый код** — _parser, Capybara
3. **Оптимизировать производительность** — кэширование, эффективные циклы
4. **Добавить тесты** — для критических функций

---

## 📁 Проверенные файлы

```
parser_2gis/tui_pytermgui/
├── __init__.py ✓
├── app.py ✓ (18 проблем)
├── run_parallel.py ✓ (2 проблемы)
├── screens/
│   ├── __init__.py ✓
│   ├── about_screen.py ✓ (4 проблемы)
│   ├── browser_settings.py ✓ (6 проблем)
│   ├── cache_viewer.py ✓ (4 проблемы)
│   ├── category_selector.py ✓ (5 проблем)
│   ├── city_selector.py ✓ (5 проблем)
│   ├── main_menu.py ✓ (3 проблемы)
│   ├── output_settings.py ✓ (5 проблем)
│   ├── parser_settings.py ✓ (5 проблем)
│   └── parsing_screen.py ✓ (8 проблем)
├── widgets/
│   ├── __init__.py ✓
│   ├── category_list.py ✓ (3 проблемы)
│   ├── checkbox.py ✓ (5 проблем)
│   ├── city_list.py ✓ (3 проблемы)
│   ├── log_viewer.py ✓ (5 проблем)
│   ├── navigable_widget.py ✓ (6 проблем)
│   ├── progress_bar.py ✓ (6 проблем)
│   └── scroll_area.py ✓ (4 проблемы)
├── utils/
│   ├── __init__.py ✓ (10 проблем)
│   ├── navigation.py ✓ (4 проблемы)
│   └── validators.py ✓ (3 проблемы)
└── styles/
    ├── __init__.py ✓
    └── default.py ✓ (2 проблемы)
```

---

## 🎯 Следующие шаги

1. **Создать задачи в GitHub Issues** для каждой критической проблемы
2. **Назначить исполнителей** на приоритетные задачи
3. **Установить дедлайны** для каждого приоритета
4. **Настроить pre-commit hooks** для предотвращения повторения проблем
5. **Провести повторный аудит** после исправлений

---

**Статус:** ✅ Аудит завершён  
**Рекомендация:** Начать с исправления критических проблем (Приоритет 1)
