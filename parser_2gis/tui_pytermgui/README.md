# TUI модуль Parser2GIS на pytermgui

Современный интерактивный TUI интерфейс для Parser2GIS, написанный на библиотеке **pytermgui**.

## Возможности

### Основные экраны:

1. **Главное меню** - центральная точка навигации по приложению
2. **Выбор городов** - поиск и множественный выбор из 204 городов
3. **Выбор категорий** - поиск и выбор из 93 категорий парсинга
4. **Настройки браузера** - конфигурация Chrome (headless, память, и т.д.)
5. **Настройки парсера** - параметры парсинга (retry, лимиты, и т.д.)
6. **Настройки вывода** - форматирование CSV/XLSX/JSON
7. **Просмотр кэша** - управление кэшем и статистика
8. **Экран парсинга** - прогресс-бары, статистика и логи в реальном времени
9. **О программе** - информация о версии и возможностях

### Виджеты:

- **ProgressBar** - кастомные прогресс-бары
- **LogViewer** - просмотр логов с цветовой дифференциацией
- **CityList** - список городов с чекбоксами
- **CategoryList** - список категорий с чекбоксами

### Утилиты:

- **Validators** - валидация числовых полей и путей
- **Navigation** - менеджер навигации между экранами

### Стили:

- **Цветовая схема**: cyan (#00FFFF), green (#00FF00), accent (#FFD700)
- **Тёмная тема** по умолчанию
- **YAML конфигурация** стилей

## Установка

```bash
# Создать виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установить pytermgui
pip install pytermgui
```

## Запуск

```bash
# Через тестовый скрипт
python test_tui_pytermgui.py

# Или напрямую из Python
from parser_2gis.tui_pytermgui import Parser2GISTUI

app = Parser2GISTUI()
app.run()
```

## Структура модуля

```
parser_2gis/tui_pytermgui/
├── __init__.py              # Экспорт компонентов
├── app.py                   # Главное приложение
├── screens/
│   ├── __init__.py
│   ├── main_menu.py         # Главное меню
│   ├── city_selector.py     # Выбор городов
│   ├── category_selector.py # Выбор категорий
│   ├── browser_settings.py  # Настройки браузера
│   ├── parser_settings.py   # Настройки парсера
│   ├── output_settings.py   # Настройки вывода
│   ├── parsing_screen.py    # Экран парсинга
│   ├── cache_viewer.py      # Просмотр кэша
│   └── about_screen.py      # О программе
├── widgets/
│   ├── __init__.py
│   ├── progress_bar.py      # Прогресс-бар
│   ├── log_viewer.py        # Просмотр логов
│   ├── city_list.py         # Список городов
│   └── category_list.py     # Список категорий
├── styles/
│   ├── __init__.py
│   └── default.py           # Стиль по умолчанию
└── utils/
    ├── __init__.py
    ├── validators.py        # Валидаторы форм
    └── navigation.py        # Навигация между экранами
```

## Навигация

- **Tab / Shift+Tab** - переключение между элементами
- **Enter** - активация элемента (кнопки, чекбокса)
- **Esc** - назад / отмена
- **Ctrl+C** - выход
- **Мышь** - поддержка кликов по кнопкам и чекбоксам

## Интеграция с парсером

Для полноценной интеграции с параллельным парсером необходимо:

1. В файле `parsing_screen.py` реализовать запуск `ParallelParser`
2. Подключить обновление прогресс-баров из callback'ов парсера
3. Реализовать обработку ошибок парсера в UI

Пример интеграции:

```python
from ..parallel_parser import ParallelParser

def _start_parsing(self) -> None:
    """Запустить парсинг."""
    self._parser = ParallelParser(
        cities=self._app.selected_cities,
        categories=self._app.selected_categories,
        config=self._app.get_config(),
    )
    
    # Запустить в отдельном потоке
    threading.Thread(target=self._run_parser).start()

def _run_parser(self) -> None:
    """Запустить парсер в фоне."""
    for result in self._parser.run():
        # Обновить UI
        self.update_progress(
            url_completed=result.url_completed,
            page_completed=result.page_completed,
            record_completed=result.record_completed,
        )
```

## Отличия от старого TUI (rich)

| Характеристика | Старый TUI (rich) | Новый TUI (pytermgui) |
|----------------|-------------------|----------------------|
| Интерактивность | Нет (только лог) | Да (кнопки, формы) |
| Навигация | Нет | Многоэкранная |
| Выбор городов | Через CLI | Через UI с поиском |
| Выбор категорий | Через CLI | Через UI с поиском |
| Настройки | Через CLI / конфиг | Через UI формы |
| Прогресс-бары | Текстовые | Графические |
| Поддержка мыши | Нет | Да |

## Будущие улучшения

- [ ] Полная интеграция с ParallelParser
- [ ] Всплывающие уведомления (toast messages)
- [ ] Поддержка светлой темы
- [ ] Горячие клавиши для всех действий
- [ ] История последних запусков
- [ ] Импорт/экспорт конфигурации
- [ ] Многоязычная поддержка (i18n)

## Известные ограничения

- Нет встроенной прокрутки для длинных списков (ограничение pytermgui)
- SelectMenu заменён на InputField с подсказкой
- TextBox заменён на Container с Label

## Лицензия

Лицензия аналогична основному проекту Parser2GIS.
