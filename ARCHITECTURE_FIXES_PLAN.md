# ПЛАН ИСПРАВЛЕНИЯ АРХИТЕКТУРНЫХ ПРОБЛЕМ

## 🔴 CRITICAL (1 проблема) - Исправить немедленно

### C1: Расхождение констант MAX_DATA_DEPTH
- **Файлы:** constants.py:23, common.py:71, cache.py:236
- **Проблема:** В constants.py и cache.py = 15, в common.py = 100
- **Решение:** Унифицировать все значения до 15, импортировать из constants.py
- **Файл для исправления:** common.py (строка 71)
- **Трудозатраты:** 30 минут

---

## 🟠 HIGH (11 проблем) - Исправить в течение 2 недель

### H1: Множество файлов в корне пакета
- **Файлы:** parser_2gis/*.py (15+ файлов)
- **Решение:** 
  - Переместить cache.py → parser_2gis/cache/
  - Переместить common.py → parser_2gis/utils/
  - Переместить validation.py, validator.py → parser_2gis/validation/
  - Переместить parallel*.py → parser_2gis/parallel/
  - Переместить statistics.py → parser_2gis/statistics/
  - Переместить signal_handler.py → parser_2gis/handlers/
  - Переместить paths.py → parser_2gis/utils/
  - Переместить pydantic_compat.py → parser_2gis/utils/
- **Трудозатраты:** 4 часа

### H2: Дублирование модулей параллелизма
- **Файлы:** parallel_parser.py, parallel_optimizer.py, parallel_helpers.py, parallel/
- **Решение:** 
  - Объединить parallel_parser.py с parallel/
  - Интегрировать parallel_optimizer.py в parallel/optimizer.py
  - parallel_helpers.py → parallel/helpers.py
- **Трудозатраты:** 6 часов

### H3: common.py имеет множественную ответственность
- **Файл:** common.py (1189 строк)
- **Решение:** Разделить на модули:
  - sanitizer.py - _sanitize_value, _check_value_type_and_sensitivity
  - polling.py - wait_until_finished, async_wait_until_finished
  - url_generator.py - generate_city_urls, generate_category_url
  - validators.py - _validate_city, _validate_category
  - dict_utils.py - unwrap_dot_dict, report_from_validation_error
- **Трудозатраты:** 4 часа

### H4: ParallelCityParser слишком сложный
- **Файл:** parallel_parser.py (2213 строк)
- **Решение:** 
  - Выделить FileMerger в отдельный сервис
  - Выделить ProgressTracker в отдельный сервис
  - Выделить TempFileManager в отдельный сервис
  - Оставить только оркестрацию в ParallelCityParser
- **Трудозатраты:** 8 часов

### H5: Дублирование констант параллелизма
- **Файлы:** constants.py, parallel_parser.py
- **Решение:** Удалить дубликаты из parallel_parser.py, импортировать из constants.py
- **Трудозатраты:** 1 час

### H6: Дублирование буферных констант
- **Файлы:** constants.py, common.py, parallel_helpers.py
- **Решение:** Удалить дубликаты, импортировать из constants.py
- **Трудозатраты:** 1 час

### H7: Идентичная логика исключений
- **Файлы:** chrome/exceptions.py, parser/exceptions.py, writer/exceptions.py, exceptions.py
- **Решение:** 
  - Создать BaseContextualException в root exceptions.py
  - Наследовать все исключения от него
  - Удалить дублирование кода
- **Трудозатраты:** 2 часа

### H8: main.py зависит от 15+ модулей
- **Файл:** main.py
- **Решение:** Использовать Facade паттерн:
  - Создать ApplicationFacade
  - Сгруппировать зависимости
- **Трудозатраты:** 3 часа

### H9: Смешение бизнес-логики и инфраструктуры
- **Файл:** parallel_parser.py
- **Решение:** 
  - Выделить инфраструктуру в InfrastructureService
  - Оставить бизнес-логику в ParallelCityParser
- **Трудозатраты:** 4 часа

### H10: Фабрики жёстко закодированы
- **Файлы:** parser/factory.py, writer/factory.py
- **Решение:** 
  - Создать ParserRegistry с декоратором @register_parser
  - Создать WriterRegistry с декоратором @register_writer
- **Трудозатраты:** 4 часа

### H11: Монолитный ParallelCityParser
- **Файл:** parallel_parser.py
- **Решение:** Декомпозиция на сервисы (см. H4)
- **Трудозатраты:** 8 часов

---

## 🟡 MEDIUM (12 проблем) - Исправить в течение 1-2 месяцев

### M1: Дублирование валидации
- **Файлы:** validation.py, validator.py
- **Решение:** Удалить validator.py или сделать тонкой обёрткой
- **Трудозатраты:** 2 часа

### M2: Отсутствие разделения на слои
- **Файлы:** Все модули
- **Решение:** 
  - Domain layer: парсеры, модели данных
  - Application layer: сервисы
  - Infrastructure layer: БД, браузер, файлы
- **Трудозатраты:** 16 часов

### M3: Configuration содержит бизнес-логику
- **Файл:** config.py
- **Решение:** Вынести merge логику в ConfigurationMerger
- **Трудозатраты:** 3 часа

### M4: Прямые зависимости от реализаций
- **Файл:** main.py и другие
- **Решение:** Dependency injection через конструктор
- **Трудозатраты:** 6 часов

### M5: Жёсткая зависимость от Chrome
- **Файлы:** parser/parsers/*.py
- **Решение:** Создать абстракцию IBrowser
- **Трудозатраты:** 6 часов

### M6: Избыточно сложная _sanitize_value
- **Файл:** common.py
- **Решение:** Упростить или лучше документировать
- **Трудозатраты:** 3 часа

### M7: Сложная merge логика
- **Файл:** config.py
- **Решение:** Упростить или вынести (см. M3)
- **Трудозатраты:** 3 часа

### M8: parallel_optimizer.py не используется
- **Файл:** parallel_optimizer.py
- **Решение:** Интегрировать в parallel/ или удалить
- **Трудозатраты:** 2 часа

### M9: constants.py слишком большой
- **Файл:** constants.py (279 строк)
- **Решение:** Разделить на подмодули:
  - constants/security.py
  - constants/cache.py
  - constants/parallel.py
  - constants/buffering.py
  - constants/validation.py
- **Трудозатраты:** 2 часа

### M10: Logger используется повсеместно
- **Файлы:** Все файлы
- **Решение:** Dependency injection
- **Трудозатраты:** 8 часов

### M11: Статический пул соединений
- **Файл:** cache.py
- **Решение:** Реализовать динамический пул
- **Трудозатраты:** 6 часов

### M12: Глобальное состояние в statistics
- **Файл:** statistics.py
- **Решение:** Изолировать состояние через класс
- **Трудозатраты:** 2 часа

---

## 🟢 LOW (7 проблем) - Исправить по возможности

### L1-L7: Низкоприоритетные проблемы
- **Трудозатраты:** 8 часов суммарно

---

## ИТОГО

| Приоритет | Количество | Трудозатраты |
|-----------|------------|--------------|
| Critical | 1 | 0.5 часа |
| High | 11 | 45 часов |
| Medium | 12 | 61 час |
| Low | 7 | 8 часов |
| **ВСЕГО** | **31** | **~115 часов** |

---

## КРИТЕРИИ ГОТОВНОСТИ

### Phase 1 (Critical + High) - 2 недели
- [ ] Все константы унифицированы
- [ ] common.py разделён
- [ ] Исключения унифицированы
- [ ] ParallelCityParser декомпозирован

### Phase 2 (Medium) - 1-2 месяца
- [ ] Слоистая архитектура внедрена
- [ ] Dependency injection используется
- [ ] Фабрики используют реестры

### Phase 3 (Low) - по возможности
- [ ] Все низкоприоритетные проблемы исправлены

---

**Создано:** 2026-03-23  
**На основе:** audit-report.md
