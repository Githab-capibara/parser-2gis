# История изменений

## [2.1.1] — 2026-03-15

### Исправлено

#### TUI (pytermgui)
- **Исправлена проблема с отображением [text]** — удалён неправильный стиль `value: "text"` для Label в `styles/default.py`
- **Исправлена ошибка `AttributeError: module 'pytermgui' has no attribute 'ScrollArea'`** — создан кастомный виджет `ScrollArea` на основе `ScrollableWidget`
- **Заменён `ptg.ScrollArea` на кастомный `ScrollArea`** во всех экранах (city_selector, category_selector, about_screen, cache_viewer)
- **Исправлена кривая правая рамка** — удалены `meta corner` из стилей Button и Window

#### Тесты
- **Обновлён тест `test_styles_yaml_structure`** — Label больше не требуется в конфигурации стилей
- **Добавлено 19 новых тестов** для выявления подобных ошибок:
  - `TestScrollAreaImport` — проверка импорта ScrollArea
  - `TestNoPtgScrollAreaUsage` — проверка отсутствия `ptg.ScrollArea` в коде
  - `TestNoTextTagInStyles` — проверка отсутствия тега `[text]`
  - `TestWindowWidthSpecification` — проверка указания ширины окон
  - `TestAllScreensImport` — проверка импорта всех экранов

### Изменено

#### Документация
- Обновлена информация о количестве тестов (376 passed)

### Технические детали

#### Новые файлы
- `parser_2gis/tui_pytermgui/widgets/scroll_area.py` — кастомный виджет ScrollArea
- `test_tui_new_tests.py` — новые тесты для TUI

#### Изменённые файлы
- `parser_2gis/tui_pytermgui/styles/default.py` — удалён стиль Label и meta corner
- `parser_2gis/tui_pytermgui/widgets/__init__.py` — добавлен экспорт ScrollArea
- `parser_2gis/tui_pytermgui/screens/city_selector.py` — заменён ptg.ScrollArea
- `parser_2gis/tui_pytermgui/screens/category_selector.py` — заменён ptg.ScrollArea
- `parser_2gis/tui_pytermgui/screens/about_screen.py` — заменён ptg.ScrollArea
- `parser_2gis/tui_pytermgui/screens/cache_viewer.py` — заменён ptg.ScrollArea
- `tests/test_dependencies.py` — обновлён тест стилей

---

## [2.1.0] — 2026-03-15

### Добавлено

#### Новые компоненты
- **AdaptiveLimits** (`parser/adaptive_limits.py`) — адаптивные лимиты для разных городов
  - Автоматическая классификация городов (small, medium, large, huge)
  - Адаптивные лимиты пустых страниц (2-7)
  - Адаптивные таймауты для навигации (30-120 сек)
  - Определение размера города на основе первых страниц
  
- **SmartRetryManager** (`parser/smart_retry.py`) — интеллектуальный retry механизм
  - Анализ типа ошибки (502, 503, 504, 404, 403, 500)
  - Учет контекста (количество записей, история попыток)
  - Экспоненциальная задержка между попытками
  - Лимит максимального количества попыток
  
- **EndOfResultsDetector** (`parser/end_of_results.py`) — детектор окончания результатов
  - Определение конца результатов на странице
  - Проверка наличия пагинации
  - Оптимизация времени парсинга
  
- **ParallelOptimizer** (`parallel_optimizer.py`) — оптимизатор параллельного парсинга
  - Приоритизация задач
  - Мониторинг использования памяти
  - Статистика выполнения
  - Оптимизация распределения задач
  
- **BrowserHealthMonitor** (`chrome/health_monitor.py`) — монитор здоровья браузера
  - Непрерывный мониторинг состояния
  - Автоматический перезапуск при критических ошибках
  - Статистика критических ошибок
  - Предотвращение зависаний

#### Новые аргументы CLI (v2.1)
- `--parser.stop-on-first-404` — немедленная остановка при первом 404
- `--parser.max-consecutive-empty-pages` — лимит подряд пустых страниц
- `--parser.max-retries` — максимальное количество повторных попыток
- `--parser.retry-on-network-errors` — retry при сетевых ошибках
- `--parser.retry-delay-base` — базовая задержка retry (сек)
- `--parser.memory-threshold` — порог памяти для очистки (МБ)

#### Тесты
- Добавлено 37 новых тестов для покрытия функций v2.1
- Тесты для AdaptiveLimits
- Тесты для SmartRetryManager
- Тесты для EndOfResultsDetector
- Тесты для ParallelOptimizer
- Тесты для BrowserHealthMonitor
- Тесты для новых аргументов CLI

### Исправлено

#### Безопасность
- Исправлена XSS уязвимость в `chrome/remote.py`
- Улучшена валидация JavaScript выражений
- Добавлена санитизация subprocess вызовов
- Обновлены уязвимые зависимости (Jinja2, Pillow, tqdm, urllib3, setuptools, wheel)

#### Производительность
- Оптимизация кэширования в SQLite (пул соединений, пакетные операции)
- Кэширование часто вызываемых функций (lru_cache)
- Оптимизация проверок памяти (кэширование psutil.Process)
- Улучшена эффективность сборки мусора
- Буферизация записи CSV (пакетная запись)

#### Ошибки
- Исправлены ошибки типизации (float/int, Optional типы)
- Исправлена типизация Pydantic (model_validate_json)
- Исправлены импорты (ParallelParser → ParallelCityParser)
- Исправлена инициализация `_current_instance` в ScreenManager
- Исправлена типизация категорий в `get_categories()`
- Исправлены глобальные переменные в tui_pytermgui
- Добавлены отсутствующие аргументы CLI в argparse
- Исправлена ошибка запуска `run.sh`

### Изменено

#### Конфигурация по умолчанию
- Увеличен порог памяти по умолчанию (500 → 2048 МБ)
- Увеличено количество тестов (293 → 330)

#### Документация
- Обновлена документация README.md (актуализирована структура проекта)
- Исправлены ссылки на отчеты о качестве кода
- Убрано упоминание несуществующего GUI в пользу TUI
- Обновлены требования к Python (3.8→3.10)
- Исправлено название logger/file_logger.py на logger/file_handler.py
- Убраны упоминания runner/gui.py (не существует)
- Обновлены бейджи в README.md

#### Унификация
- Унифицированы ссылки на репозиторий GitHub (Githab-capibara)
- Улучшена структура документации

---

## [2.0.0] — 2026-03-14

### Исправлено
- Исправлена совместимость с Pydantic v2 (замена `.dict()` на `.model_dump()`)
- Улучшена обработка ошибок в скриптах обновления данных
- Переведены комментарии в скриптах на русский язык
- Улучшена читаемость кода и документация
- Обновлена документация README.md (таблицы, примеры, FAQ)

### Изменено
- Унифицированы ссылки на репозиторий GitHub (Githab-capibara)
- Улучшена структура документации

---

## [1.2.2] - 2026-03-12

### Исправления
- Исправлена логическая ошибка в декораторе wait_until_finished
- Устранена потенциальная XSS уязвимость в chrome/remote.py
- Исправлено обращение к несуществующему атрибуту timeout
- Исправлен стиль кода в validator.py
- Переведены комментарии на русский язык
- Удалён неиспользуемый код из common.py

### Улучшения
- Добавлена валидация JavaScript кода
- Улучшена обработка ошибок
- Оптимизирована работа с памятью
- Улучшена типизация

---

## [1.2.1] — 14-03-2024

### Добавлено
- ✅ Поддержка парсинга остановок. Fix [issue](https://github.com/Githab-capibara/parser-2gis/issues/52)
- Генератор ссылок добавляет в URL сортировку по алфавиту для исключения повторений поисковой выдачи при навигации по страницам
- Обновлён список рубрик

---

## [1.2.0] — 08-02-2024

### Добавлено
- Небольшой багфикс схемы ответов сервера
- Поддержка ссылок организаций `https://2gis.ru/<city>/firm/<firm_id>`
- Обновлён список рубрик и городов

---

## [1.1.2] — 08-03-2023

### Добавлено
- Поддержка Chrome v111
- Новый город Басра (Ирак)
- Обновлён список рубрик и городов

---

## [1.1.1] — 03-02-2023

### Добавлено
- Обновлён список рубрик и городов
- Добавлены поля контактов: **Telegram**, **Viber**, **WhatsApp**

---

## [1.1.0] — 05-01-2023

### Добавлено
- Обновлён список рубрик и городов
- Добавлены поля: **Рейтинг** и **Количество отзывов**
- Добавлена возможность записи результата в Excel таблицу (XLSX)
- Добавлена автоматическая навигация к странице, если в URL есть параметр `/page/<номер_страницы>`

---

## [0.1.10] — 25-10-2022

### Добавлено
- Обновлён список рубрик и городов

### Исправлено
- ⚠️ Отключен скрытый режим парсинга по умолчанию

---

## [0.1.9] — 18-08-2022

### Добавлено
- Новые рубрики: *Клубы настольного тенниса*, *Атрибутика для болельщиков*, *Полицейские станции*
- Поддержка парсинга ссылок "В здании". Fix [issue](https://github.com/Githab-capibara/parser-2gis/issues/13), см. [wiki](https://github.com/Githab-capibara/parser-2gis/wiki/URLs)

---

## [0.1.8] — 10-08-2022

### Добавлено
- Совместимость с Windows 7, Windows 8

---

## [0.1.7] — 19-07-2022

### Исправлено
- ⚠️ Возможная [ошибка](https://github.com/Githab-capibara/parser-2gis/issues/9) во время получения нового ключа авторизации
- ⚠️ [Баг](https://github.com/Githab-capibara/parser-2gis/issues/7), связанный с остановкой парсера и непереходом к следующей ссылке при возникновении ошибки

### Добавлено
- Новые рубрики: *Прокат компьютеров / ноутбуков*, *Буккроссинг*, *Пляжные принадлежности*, *Администрация города/посёлка/села*

---

## [0.1.6] — 03-07-2022

### Исправлено
- ⚠️ Исправлен релиз под Linux
- ⚠️ Пропуск [некорректных ответов](https://github.com/Githab-capibara/parser-2gis/issues/4#issuecomment-1172172691) сервера (JSON expected)

### Добавлено
- Новая страна: **Кувейт**
- Новые рубрики: *Купальники*, *Мебель для салонов красоты*, *Дневные детские лагеря*

---

## [0.1.5] — 25-05-2022

### Исправлено
- ⚠️ Исправлен баг с редкой ошибкой чтения ответа сервера при парсинге CSV

### Добавлено
- Колонка "**Часовой пояс**" в CSV

---

## [0.1.4] — 24-05-2022

### Исправлено
- ⚠️ Исправлен баг с неполным удалением временного профиля браузера

---

## [0.1.3] — 23-05-2022

### Исправлено
- ⚠️ CSV: Исправлено название колонки `Веб сайт` → `Веб-сайт`
- ⚠️ Usage: Убрана ошибочно влезшая версия конфигурации

---

## [0.1.2] — 22-05-2022

### Добавлено
- ⚠️ Предупреждение при неудачной попытке загрузки GUI

---

## [0.1.1] — 22-05-2022

### Исправлено
- ⚠️ Ссылка на репозиторий внутри модуля и в манифесте

---

## [0.1.0] — 22-05-2022

### Добавлено
- ✅ Первый релиз

---

## Ссылки

[2.1.0]: https://github.com/Githab-capibara/parser-2gis/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/Githab-capibara/parser-2gis/compare/v1.2.2...v2.0.0
[1.2.2]: https://github.com/Githab-capibara/parser-2gis/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/Githab-capibara/parser-2gis/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/Githab-capibara/parser-2gis/compare/v1.1.2...v1.2.0
[1.1.2]: https://github.com/Githab-capibara/parser-2gis/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/Githab-capibara/parser-2gis/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.10...v1.1.0
[0.1.10]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.9...v0.1.10
[0.1.9]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Githab-capibara/parser-2gis/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Githab-capibara/parser-2gis/releases/tag/v0.1.0
