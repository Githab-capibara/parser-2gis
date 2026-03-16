# Отчёт ревью кода TUI Parser2GIS

**Дата:** 2026-03-16  
**Область проверки:** /home/d/parser-2gis/parser_2gis/tui_pytermgui/  
**Проверено файлов:** 27

## Сводка

| Категория | Количество |
|-----------|------------|
| Critical | 8 |
| High | 12 |
| Medium | 15 |
| Low | 11 |
| **Всего** | **46** |

---

## Критические проблемы (Critical)

### 1. Неправильное использование Checkbox в city_list.py и category_list.py

**Файл:** `parser_2gis/tui_pytermgui/widgets/city_list.py`  
**Строка:** 44-48  
**Описание:** Используется `ptg.Checkbox` вместо кастомного `Checkbox` виджета из проекта. Это вызовет ошибку импорта или неправильное поведение.

```python
checkbox = ptg.Checkbox(
    label=f"{city_name} ({country})",
    value=is_selected,
    on_change=lambda checked, idx=i: self._toggle_city(idx, checked),
)
```

**Рекомендация:** Заменить на кастомный `Checkbox` из `..widgets`:
```python
from .checkbox import Checkbox

checkbox = Checkbox(
    label=f"{city_name} ({country})",
    value=is_selected,
    on_change=lambda checked, idx=i: self._toggle_city(idx, checked),
)
```

**Критичность:** Critical

---

### 2. Неправильное использование Checkbox в category_list.py

**Файл:** `parser_2gis/tui_pytermgui/widgets/category_list.py`  
**Строка:** 44-48  
**Описание:** Аналогичная проблема с `ptg.Checkbox` вместо кастомного виджета.

**Рекомендация:** Импортировать и использовать кастомный `Checkbox`.

**Критичность:** Critical

---

### 3. Отсутствие обработки ошибок в app.py при запуске парсинга

**Файл:** `parser_2gis/tui_pytermgui/app.py`  
**Строка:** 258-270  
**Описание:** В методе `_start_parsing` нет обработки случая, когда `self._screen_manager` или `self._manager` равны None после проверки.

```python
if not selected_cities_data:
    self._add_log_to_parsing_screen("Ошибка: не выбраны города", "ERROR")
    return
```

**Рекомендация:** Добавить полноценную обработку ошибок с возвратом в главное меню.

**Критичность:** Critical

---

### 4. Потенциальная утечка памяти в ParsingScreen

**Файл:** `parser_2gis/tui_pytermgui/screens/parsing_screen.py`  
**Строка:** 117-120  
**Описание:** Метод `_start_auto_update` использует `ptg.Monitor`, но нет кода для остановки монитора при завершении парсинга.

```python
def _start_auto_update(self) -> None:
    if hasattr(ptg, 'Monitor'):
        monitor = ptg.Monitor().start()
        monitor.attach(self._update_display, period=0.5)
```

**Рекомендация:** Сохранять ссылку на монитор и останавливать его в `_stop_parsing`.

**Критичность:** Critical

---

### 5. Неправильная работа с FileManager в cache_viewer.py

**Файл:** `parser_2gis/tui_pytermgui/screens/cache_viewer.py`  
**Строка:** 44-65  
**Описание:** При загрузке кэша используется `json.load` без обработки исключений для повреждённых файлов.

```python
with open(cache_file, "r", encoding="utf-8") as f:
    cache_data = json.load(f)
```

**Рекомендация:** Обернуть в try-except для обработки `json.JSONDecodeError`.

**Критичность:** Critical

---

### 6. Отсутствие валидации в parser_settings.py

**Файл:** `parser_2gis/tui_pytermgui/screens/parser_settings.py`  
**Строка:** 174-188  
**Описание:** Метод `_save` преобразует значения в int без обработки ValueError после валидации.

```python
max_records = int(self._fields["max_records"].value)  # type: ignore
```

**Рекомендация:** Добавить try-except блок для обработки ошибок преобразования.

**Критичность:** Critical

---

### 7. Проблема с замыканием в category_selector.py

**Файл:** `parser_2gis/tui_pytermgui/screens/category_selector.py`  
**Строка:** 124-128  
**Описание:** Factory функция для замыкания может привести к захвату неправильного индекса.

```python
def make_callback(cat_index: int):
    return lambda checked: self._toggle_category(cat_index, checked)
```

**Рекомендация:** Использовать `functools.partial` или передавать индекс напрямую.

**Критичность:** Critical

---

### 8. Проблема с замыканием в city_selector.py

**Файл:** `parser_2gis/tui_pytermgui/screens/city_selector.py`  
**Строка:** 157-161  
**Описание:** Аналогичная проблема с замыканием.

**Рекомендация:** Использовать `functools.partial`.

**Критичность:** Critical

---

## Проблемы высокой важности (High)

### 1. Неправильный доступ к виджетам в ScrollArea

**Файл:** `parser_2gis/tui_pytermgui/widgets/scroll_area.py`  
**Строка:** 38-50  
**Описание:** Используется `getattr(self._content, 'widgets', [])` для доступа к виджетам, что может не работать со всеми типами контейнеров.

**Рекомендация:** Использовать публичный API pytermgui для доступа к дочерним элементам.

**Критичность:** High

---

### 2. Отсутствие обработки None в app.go_back()

**Файл:** `parser_2gis/tui_pytermgui/app.py`  
**Строка:** 223-235  
**Описание:** При возврате назад может возникнуть ошибка если `self._screen_manager.current_instance` равен None.

**Рекомендация:** Добавить дополнительную проверку перед вызовом `create_window()`.

**Критичность:** High

---

### 3. Неправильное использование ButtonWidget в main_menu.py

**Файл:** `parser_2gis/tui_pytermgui/screens/main_menu.py`  
**Строка:** 127-129  
**Описание:** Кнопки создаются с callback, но callback принимает аргументы которые не используются.

```python
button = ButtonWidget(button_text, onclick=callback)
```

**Рекомендация:** Унифицировать сигнатуры callback функций.

**Критичность:** High

---

### 4. Отсутствие обновления UI в city_selector._update_counter()

**Файл:** `parser_2gis/tui_pytermgui/screens/city_selector.py`  
**Строка:** 230-237  
**Описание:** Метод только устанавливает флаг `force_full_redraw`, но не обновляет фактическое значение счётчика.

**Рекомендация:** Обновлять текст label напрямую.

**Критичность:** High

---

### 5. Неполная реализация _stop_parsing в app.py

**Файл:** `parser_2gis/tui_pytermgui/app.py`  
**Строка:** 393-411  
**Описание:** Метод проверяет `self._logger is None` но logger никогда не инициализируется в коде.

**Рекомендация:** Инициализировать logger в `__init__` или убрать проверку.

**Критичность:** High

---

### 6. Отсутствие обработки ошибок в browser_settings._save()

**Файл:** `parser_2gis/tui_pytermgui/screens/browser_settings.py`  
**Строка:** 168-185  
**Описание:** При ошибке валидации метод просто возвращает None без уведомления пользователя.

```python
except ValueError:
    # Показать ошибку
    return
```

**Рекомендация:** Реализовать отображение ошибки пользователю.

**Критичность:** High

---

### 7. Неправильное использование InputField в parser_settings.py

**Файл:** `parser_2gis/tui_pytermgui/screens/parser_settings.py`  
**Строка:** 254-260  
**Описание:** Метод `_set_input_field_value` использует `delete_back()` в цикле, что может не работать корректно.

**Рекомендация:** Использовать публичный API для установки значения.

**Критичность:** High

---

### 8. Неправильное использование InputField в output_settings.py

**Файл:** `parser_2gis/tui_pytermgui/screens/output_settings.py`  
**Строка:** 199-206  
**Описание:** Аналогичная проблема с `_set_input_field_value`.

**Критичность:** High

---

### 9. Отсутствие импорта в output_settings.py

**Файл:** `parser_2gis/tui_pytermgui/screens/output_settings.py`  
**Строка:** 211-212  
**Описание:** Импортируются `CSVOptions, WriterOptions` из `...writer.options`, но путь может быть неверным.

**Рекомендация:** Проверить корректность пути импорта.

**Критичность:** High

---

### 10. Отсутствие импорта в parser_settings.py

**Файл:** `parser_2gis/tui_pytermgui/screens/parser_settings.py`  
**Строка:** 241-242  
**Описание:** Импортируется `ParserOptions` из `...parser.options`, но путь может быть неверным.

**Критичность:** High

---

### 11. Неправильная работа с окнами в main_menu._exit()

**Файл:** `parser_2gis/tui_pytermgui/screens/main_menu.py`  
**Строка:** 204-224  
**Описание:** Создаётся `InputField` для подтверждения выхода, но логика обработки Enter/Esc не реализована.

**Рекомендация:** Использовать модальное окно с правильной обработкой клавиш.

**Критичность:** High

---

### 12. Отсутствие обработки в parsing_screen._minimize()

**Файл:** `parser_2gis/tui_pytermgui/screens/parsing_screen.py`  
**Строка:** 391-393  
**Описание:** Метод просто выводит сообщение о разработке функции.

**Рекомендация:** Либо реализовать функцию, либо убрать кнопку.

**Критичность:** High

---

## Проблемы средней важности (Medium)

### 1. Дублирование кода в checkbox.py

**Файл:** `parser_2gis/tui_pytermgui/widgets/checkbox.py`  
**Строка:** 94-100, 118-124  
**Описание:** Методы `toggle()` и `on_left_click()` дублируют логику переключения значения.

**Рекомендация:** Вызывать `toggle()` из `on_left_click()`.

**Критичность:** Medium

---

### 2. Неиспользуемый параметр height в CityList

**Файл:** `parser_2gis/tui_pytermgui/widgets/city_list.py`  
**Строка:** 28  
**Описание:** Параметр `height` принимается но не используется.

**Критичность:** Medium

---

### 3. Неиспользуемый параметр height в CategoryList

**Файл:** `parser_2gis/tui_pytermgui/widgets/category_list.py`  
**Строка:** 28  
**Описание:** Параметр `height` принимается но не используется.

**Критичность:** Medium

---

### 4. Отсутствие документации в ButtonWidget

**Файл:** `parser_2gis/tui_pytermgui/widgets/navigable_widget.py`  
**Строка:** 238-280  
**Описание:** Метод `get_lines` не имеет документации.

**Критичность:** Medium

---

### 5. Магические числа в progress_bar.py

**Файл:** `parser_2gis/tui_pytermgui/widgets/progress_bar.py`  
**Строка:** 144-149  
**Описание:** Использование магических чисел для процентов (75, 50).

**Рекомендация:** Вынести в константы.

**Критичность:** Medium

---

### 6. Отсутствие кэширования в ProgressBar._render_text()

**Файл:** `parser_2gis/tui_pytermgui/widgets/progress_bar.py`  
**Строка:** 171-208  
**Описание:** `_cached_text` объявлен но не используется для кэширования.

**Критичность:** Medium

---

### 7. Неполная реализация MultiProgressBar.render_label()

**Файл:** `parser_2gis/tui_pytermgui/widgets/progress_bar.py`  
**Строка:** 328-338  
**Описание:** Использует `box="EMPTY_VERTICAL"` который может не существовать.

**Критичность:** Medium

---

### 8. Отсутствие обработки в LogViewer.render()

**Файл:** `parser_2gis/tui_pytermgui/widgets/log_viewer.py`  
**Строка:** 180-195  
**Описание:** При пустых логах создаётся Container с фиксированной высотой 10.

**Рекомендация:** Сделать высоту настраиваемой.

**Критичность:** Medium

---

### 9. Дублирование стилей в LogViewer

**Файл:** `parser_2gis/tui_pytermgui/widgets/log_viewer.py`  
**Строка:** 44-70  
**Описание:** Стили дублируются для каждого уровня лога.

**Рекомендация:** Использовать наследование стилей.

**Критичность:** Medium

---

### 10. Отсутствие обработки в navigation.py

**Файл:** `parser_2gis/tui_pytermgui/utils/navigation.py`  
**Строка:** 44-56  
**Описание:** Метод `clear()` пытается удалить окно, но может вызвать ошибку.

**Критичность:** Medium

---

### 11. Неполная валидация в validators.py

**Файл:** `parser_2gis/tui_pytermgui/utils/validators.py`  
**Строка:** 48-74  
**Описание:** `validate_path` не проверяет права доступа к файлу.

**Критичность:** Medium

---

### 12. Отсутствие типов в SpinnerAnimation

**Файл:** `parser_2gis/tui_pytermgui/utils/__init__.py`  
**Строка:** 220-280  
**Описание:** Некоторые методы не имеют полной типизации.

**Критичность:** Medium

---

### 13. Магические числа в GradientText

**Файл:** `parser_2gis/tui_pytermgui/utils/__init__.py`  
**Строка:** 328-340  
**Описание:** Индексы цветов используются без констант.

**Критичность:** Medium

---

### 14. Неиспользуемый параметр в BoxDrawing.draw_box()

**Файл:** `parser_2gis/tui_pytermgui/utils/__init__.py`  
**Строка:** 416-450  
**Описание:** Параметр `title` обрабатывается но может обрезаться неправильно.

**Критичность:** Medium

---

### 15. Отсутствие обработки в app._clear_all_windows()

**Файл:** `parser_2gis/tui_pytermgui/app.py`  
**Строка:** 207-218  
**Описание:** Исключения игнорируются без логирования.

**Рекомендация:** Логировать ошибки удаления окон.

**Критичность:** Medium

---

## Проблемы низкой важности (Low)

### 1. TODO комментарии в cache_viewer.py

**Файл:** `parser_2gis/tui_pytermgui/screens/cache_viewer.py`  
**Строка:** 212, 227  
**Описание:** Нереализованные функции.

**Критичность:** Low

---

### 2. TODO комментарии в output_settings.py

**Файл:** `parser_2gis/tui_pytermgui/screens/output_settings.py`  
**Строка:** 260  
**Описание:** Нереализованное всплывающее сообщение.

**Критичность:** Low

---

### 3. TODO комментарии в parser_settings.py

**Файл:** `parser_2gis/tui_pytermgui/screens/parser_settings.py`  
**Строка:** 326  
**Описание:** Нереализованное всплывающее сообщение.

**Критичность:** Low

---

### 4. TODO комментарии в browser_settings.py

**Файл:** `parser_2gis/tui_pytermgui/screens/browser_settings.py`  
**Строка:** 249  
**Описание:** Нереализованное всплывающее сообщение.

**Критичность:** Low

---

### 5. TODO комментарии в parsing_screen.py

**Файл:** `parser_2gis/tui_pytermgui/screens/parsing_screen.py`  
**Строка:** 404  
**Описание:** Нереализованная интеграция с ParallelParser.

**Критичность:** Low

---

### 6. Отсутствует type hint в NavigableWidget.__init__

**Файл:** `parser_2gis/tui_pytermgui/widgets/navigable_widget.py`  
**Строка:** 34-42  
**Описание:** Используются `*args, **kwargs` без типизации.

**Критичность:** Low

---

### 7. Отсутствует type hint в NavigableContainer.__init__

**Файл:** `parser_2gis/tui_pytermgui/widgets/navigable_widget.py`  
**Строка:** 118-126  
**Описание:** Используются `*widgets, **kwargs` без типизации.

**Критичность:** Low

---

### 8. Избыточный комментарий в checkbox.py

**Файл:** `parser_2gis/tui_pytermgui/widgets/checkbox.py`  
**Строка:** 56-58  
**Описание:** Комментарий о синтаксисе TIM-тегов избыточен.

**Критичность:** Low

---

### 9. Неиспользуемый импорт в app.py

**Файл:** `parser_2gis/tui_pytermgui/app.py`  
**Строка:** 24  
**Описание:** Импорт `Optional` используется, но можно упростить.

**Критичность:** Low

---

### 10. Отсутствует __all__ в navigation.py

**Файл:** `parser_2gis/tui_pytermgui/utils/navigation.py`  
**Строка:** 1  
**Описание:** Модуль не экспортирует явно публичный API.

**Критичность:** Low

---

### 11. Отсутствует __all__ в validators.py

**Файл:** `parser_2gis/tui_pytermgui/utils/validators.py`  
**Строка:** 1  
**Описание:** Модуль не экспортирует явно публичный API.

**Критичность:** Low

---

## Файлы проверены

### Виджеты (9 файлов)
- ✅ `widgets/__init__.py`
- ✅ `widgets/scroll_area.py`
- ✅ `widgets/checkbox.py`
- ✅ `widgets/progress_bar.py`
- ✅ `widgets/log_viewer.py`
- ✅ `widgets/city_list.py`
- ✅ `widgets/category_list.py`
- ✅ `widgets/navigable_widget.py`

### Экраны (10 файлов)
- ✅ `screens/__init__.py`
- ✅ `screens/main_menu.py`
- ✅ `screens/cache_viewer.py`
- ✅ `screens/category_selector.py`
- ✅ `screens/city_selector.py`
- ✅ `screens/parser_settings.py`
- ✅ `screens/output_settings.py`
- ✅ `screens/parsing_screen.py`
- ✅ `screens/browser_settings.py`
- ✅ `screens/about_screen.py`

### Утилиты (3 файла)
- ✅ `utils/__init__.py`
- ✅ `utils/navigation.py`
- ✅ `utils/validators.py`

### Стили (2 файла)
- ✅ `styles/__init__.py`
- ✅ `styles/default.py`

### Основное (3 файла)
- ✅ `app.py`
- ✅ `__init__.py`
- ✅ `run_parallel.py`

---

## Следующие шаги

### Приоритет 1 (Critical) - Исправить немедленно:
1. Заменить `ptg.Checkbox` на кастомный `Checkbox` в city_list.py и category_list.py
2. Добавить обработку ошибок в app.py при запуске парсинга
3. Исправить утечку памяти в ParsingScreen с Monitor
4. Добавить обработку JSON ошибок в cache_viewer.py
5. Добавить валидацию в parser_settings.py
6. Исправить замыкания в category_selector.py и city_selector.py

### Приоритет 2 (High) - Исправить в ближайшем спринте:
1. Исправить доступ к виджетам в ScrollArea
2. Добавить обработку None в app.go_back()
3. Унифицировать callback в main_menu.py
4. Реализовать обновление UI в city_selector._update_counter()
5. Инициализировать logger в app.py
6. Реализовать отображение ошибок в browser_settings.py
7. Исправить работу с InputField в parser_settings.py и output_settings.py
8. Проверить импорты в parser_settings.py и output_settings.py
9. Исправить логику подтверждения выхода в main_menu.py
10. Реализовать или удалить функцию minimize в parsing_screen.py

### Приоритет 3 (Medium) - Запланировать рефакторинг:
1. Устранить дублирование кода в checkbox.py
2. Удалить неиспользуемые параметры height
3. Добавить документацию
4. Вынести магические числа в константы
5. Реализовать кэширование в ProgressBar
6. Улучшить обработку ошибок в navigation.py

### Приоритет 4 (Low) - Улучшения:
1. Реализовать TODO комментарии
2. Добавить type hints
3. Добавить __all__ в модули
4. Удалить избыточные комментарии

---

## Рекомендации по архитектуре

1. **Единый стиль обработки ошибок**: Создать базовый класс для экранов с общей обработкой ошибок
2. **Централизованное управление состоянием**: Вынести состояние приложения в отдельный класс State
3. **Система сообщений**: Реализовать полноценную систему всплывающих сообщений вместо TODO
4. **Тестирование**: Добавить unit-тесты для виджетов и экранов
5. **Документация**: Добавить docstrings для всех публичных методов

---

## Выводы

Код TUI имеет современную архитектуру с хорошей структурой, но содержит несколько критических проблем требующих немедленного исправления:

1. **Проблемы с импортами** - использование `ptg.Checkbox` вместо кастомного виджета
2. **Проблемы с замыканиями** - неправильный захват переменных в lambda
3. **Отсутствие обработки ошибок** -多处 отсутствуют try-except блоки
4. **Утечки памяти** - не останавливается Monitor при завершении

После исправления критических и высоких проблем код будет готов к продакшен использованию.
