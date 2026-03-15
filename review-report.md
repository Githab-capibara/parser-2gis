# Отчёт ревью кода проекта parser-2gis

**Дата:** 2026-03-15  
**Область проверки:** Основные файлы проекта: parser-2gis.py, parser_2gis/main.py, parser_2gis/parallel_parser.py  
**Проверенных файлов:** 99 Python файлов в директории parser_2gis/

## Сводка

| Категория | Количество |
|-----------|------------|
| Критические | 4 |
| Предупреждения | 7 |
| Рекомендации | 5 |
| **Всего** | **16** |

---

## Критические проблемы (Critical)

### 1. parallel_parser.py:660 - Использование logger в ParallelCityParserThread

**Файл:** `/home/d/parser-2gis/parser_2gis/parallel_parser.py`  
**Строка:** 660  
**Проблема:** В классе `ParallelCityParserThread` в методе `run()` используется `logger.error()`, но logger импортирован на уровне модуля. При определённых условиях импорта может возникнуть `NameError`.

```python
# Строка 660
logger.error("Ошибка в потоке паралсера: %s", e, exc_info=True)
```

**Рекомендация:** Добавить явный импорт logger в начало файла или использовать self.log() для логирования.

**Исправление:**
```python
# Вариант 1: Использовать self.log()
self.log(f"Ошибка в потоке паралсера: {e}", "error")

# Вариант 2: Добавить импорт в начало класса
from .logger import logger
```

---

### 2. main.py - Нет гарантии очистки ресурсов при KeyboardInterrupt

**Файл:** `/home/d/parser-2gis/parser_2gis/main.py`  
**Строки:** 580-650  
**Проблема:** В функции `main()` обработка `KeyboardInterrupt` не гарантирует очистку ресурсов браузера. Если пользователь прервёт выполнение во время парсинга, браузер может остаться запущенным.

```python
# Строки 630-650
try:
    cli_app(urls, output_path, output_format, command_line_config)
except KeyboardInterrupt:
    logger.info("Работа приложения прервана пользователем.")
    sys.exit(0)
```

**Рекомендация:** Использовать контекстные менеджеры или блок finally для гарантии очистки ресурсов.

**Исправление:**
```python
try:
    cli_app(urls, output_path, output_format, command_line_config)
except KeyboardInterrupt:
    logger.info("Работа приложения прервана пользователем.")
    # Гарантированная очистка ресурсов
    if 'parser' in locals() and hasattr(parser, 'close'):
        parser.close()
    sys.exit(0)
finally:
    # Очистка в любом случае
    cleanup_resources()
```

---

### 3. parallel_parser.py:413 - writer может быть None

**Файл:** `/home/d/parser-2gis/parser_2gis/parallel_parser.py`  
**Строки:** 408-415  
**Проблема:** В методе `merge_csv_files()` если все CSV файлы пустые или не имеют заголовков, `writer` остаётся `None`, что приведёт к `AttributeError` при попытке записи.

```python
# Строки 408-415
with open(temp_output, "w", encoding=output_encoding, newline="", buffering=32768) as outfile:
    writer = None
    # ...
    for csv_file in csv_files:
        # ...
        if not reader.fieldnames:
            continue  # writer так и останется None!
        
        if writer is None:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
```

**Рекомендация:** Добавить проверку на None перед использованием writer или инициализировать writer при создании файла.

**Исправление:**
```python
# После цикла проверить, был ли создан writer
if writer is None:
    self.log("Не удалось создать writer - все файлы пустые", "error")
    temp_output.unlink()
    return False
```

---

### 4. parallel_parser.py:239-242 - Утечка временных файлов при ошибке

**Файл:** `/home/d/parser-2gis/parser_2gis/parallel_parser.py`  
**Строки:** 237-242  
**Проблема:** При ошибке `temp_filepath.replace(filepath)` fallback на `shutil.move()` может оставить временный файл если и он завершится ошибкой.

```python
try:
    temp_filepath.replace(filepath)
except OSError:
    shutil.move(str(temp_filepath), str(filepath))  # Может выбросить исключение!
```

**Рекомендация:** Обернуть shutil.move в try-except и удалить временный файл при ошибке.

**Исправление:**
```python
try:
    temp_filepath.replace(filepath)
except OSError:
    try:
        shutil.move(str(temp_filepath), str(filepath))
    except (OSError, shutil.Error) as move_error:
        self.log(f"Не удалось переместить файл: {move_error}", "error")
        if temp_filepath.exists():
            temp_filepath.unlink()
        raise
```

---

## Предупреждения (Warnings)

### 5. main.py:174-186 - Дублирование кода валидации URL

**Файл:** `/home/d/parser-2gis/parser_2gis/main.py`  
**Строки:** 174-186  
**Проблема:** Код валидации URL дублируется в нескольких местах функции `parse_arguments()`.

**Рекомендация:** Вынести валидацию в отдельную функцию или использовать декоратор.

---

### 6. config.py:68-93 - Рекурсивное объединение конфигурации

**Файл:** `/home/d/parser-2gis/parser_2gis/config.py`  
**Строки:** 68-93  
**Проблема:** Метод `_merge_models()` использует рекурсию с ограничением глубины 10, но при глубокой вложенности может возникнуть `RecursionError`.

**Рекомендация:** Переписать на итеративный подход с использованием стека.

---

### 7. parallel_parser.py:372-374 - Извлечение категории из имени файла

**Файл:** `/home/d/parser-2gis/parser_2gis/parallel_parser.py`  
**Строки:** 370-376  
**Проблема:** Логика извлечения категории из имени файла может дать неверный результат для файлов со сложными именами.

```python
last_underscore_idx = stem.rfind("_")
if last_underscore_idx > 0:
    category_name = stem[last_underscore_idx + 1:].replace("_", " ")
else:
    category_name = stem.replace("_", " ")  # Потеря структуры имени
```

**Рекомендация:** Использовать более надёжный формат имён файлов или хранить метаданные отдельно.

---

### 8. main.py:470-490 - Обработка ошибок загрузки городов

**Файл:** `/home/d/parser-2gis/parser_2gis/main.py`  
**Строки:** 470-490  
**Проблема:** При ошибке загрузки файла городов приложение завершается с исключением, но ресурсы не освобождаются.

**Рекомендация:** Использовать контекстный менеджер для работы с файлами.

---

### 9. parallel_parser.py:102-112 - Проверка прав на запись

**Файл:** `/home/d/parser-2gis/parser_2gis/parallel_parser.py`  
**Строки:** 100-115  
**Проблема:** Проверка прав на запись через создание тестового файла может создать файл, который не будет удалён при ошибке.

**Рекомендация:** Гарантировать удаление тестового файла в блоке finally.

---

### 10. chrome/browser.py:72-78 - Установка прав на профиль

**Файл:** `/home/d/parser-2gis/parser_2gis/chrome/browser.py`  
**Строки:** 72-78  
**Проблема:** При ошибке `os.chmod()` профиль остаётся с небезопасными правами.

```python
try:
    os.chmod(self._profile_path, 0o700)
except OSError as e:
    logger.debug("Не удалось установить права 0o700 на профиль: %s", e)
    # Профиль остаётся с правами по умолчанию!
```

**Рекомендация:** Выбрасывать исключение или удалять профиль при ошибке установки прав.

---

### 11. common.py:230-250 - Обработка циклических ссылок

**Файл:** `/home/d/parser-2gis/parser_2gis/common.py`  
**Строки:** 230-250  
**Проблема:** Функция `_sanitize_value()` отслеживает циклические ссылки через id объектов, но может пропустить некоторые случаи.

**Рекомендация:** Использовать `weakref.WeakSet` для автоматической очистки.

---

## Рекомендации (Recommendations)

### 12. TODO комментарии в tui_pytermgui

**Файлы:**
- `parser_2gis/tui_pytermgui/screens/cache_viewer.py:211,226`
- `parser_2gis/tui_pytermgui/screens/output_settings.py:239`
- `parser_2gis/tui_pytermgui/screens/parsing_screen.py:316,324`
- `parser_2gis/tui_pytermgui/screens/browser_settings.py:230`
- `parser_2gis/tui_pytermgui/screens/parser_settings.py:295`

**Проблема:** 7 TODO комментариев указывают на нереализованную функциональность.

**Рекомендация:** Реализовать отложенную функциональность или создать задачи в трекере.

---

### 13. Использование print() вместо logger

**Файлы:**
- `parser_2gis/tui/app.py:137-144`
- `parser_2gis/tui/logger.py:67`
- `parser_2gis/cli/progress.py:182`
- `parser_2gis/logger/visual_logger.py:215-344`

**Проблема:** В некоторых файлах используется `print()` вместо `logger`, что усложняет управление выводом.

**Рекомендация:** Заменить print() на logger для консистентности.

---

### 14. Отсутствие asyncio для I/O операций

**Файл:** Все файлы проекта  
**Проблема:** Проект использует `threading` для параллельных I/O операций (сеть, файлы), что менее эффективно чем `asyncio`.

**Рекомендация:** Рассмотреть миграцию на asyncio для улучшения производительности.

---

### 15. Нет проверок типов для некоторых функций

**Файлы:** `parser_2gis/common.py`, `parser_2gis/validator.py`  
**Проблема:** Некоторые функции не имеют аннотаций типов для всех параметров и возвращаемых значений.

**Рекомендация:** Добавить полные аннотации типов для улучшения читаемости и IDE поддержки.

---

### 16. potential SQL injection паттерны не найдены

**Статус:** ✅ Не найдено  
**Примечание:** В проекте не используется SQL, поэтому уязвимости SQL injection отсутствуют.

---

## Файлы проверены

### Основные файлы:
- ✅ `/home/d/parser-2gis/parser-2gis.py`
- ✅ `/home/d/parser-2gis/parser_2gis/main.py` (699 строк)
- ✅ `/home/d/parser-2gis/parser_2gis/parallel_parser.py` (666 строк)

### Дополнительные файлы:
- ✅ `/home/d/parser-2gis/parser_2gis/config.py`
- ✅ `/home/d/parser-2gis/parser_2gis/common.py`
- ✅ `/home/d/parser-2gis/parser_2gis/chrome/browser.py`
- ✅ `/home/d/parser-2gis/parser_2gis/parser/parsers/main.py`
- ✅ `/home/d/parser-2gis/parser_2gis/writer/factory.py`
- ✅ `/home/d/parser-2gis/parser_2gis/tui/parallel.py`

### Всего проверено: 99 Python файлов

---

## Следующие шаги

### Приоритет 1 (Критические проблемы):
1. **Исправить parallel_parser.py:660** - Добавить обработку logger в ParallelCityParserThread
2. **Исправить main.py** - Добавить гарантированную очистку ресурсов при KeyboardInterrupt
3. **Исправить parallel_parser.py:413** - Добавить проверку writer на None
4. **Исправить parallel_parser.py:239-242** - Добавить обработку ошибок shutil.move

### Приоритет 2 (Предупреждения):
5. Рефакторинг валидации URL в main.py
6. Переписать рекурсивное объединение конфигурации на итеративный подход
7. Улучшить извлечение категории из имени файла
8. Добавить контекстные менеджеры для работы с файлами
9. Гарантировать удаление тестовых файлов
10. Улучшить обработку ошибок установки прав на профиль

### Приоритет 3 (Рекомендации):
11. Реализовать TODO функциональность в tui_pytermgui
12. Заменить print() на logger
13. Рассмотреть миграцию на asyncio
14. Добавить аннотации типов

---

## Методология проверки

### Использованные инструменты:
- **Синтаксический анализ:** `python3 -m py_compile`
- **Поиск паттернов:** Grep search для TODO, FIXME, XXX, HACK
- **Проверка безопасности:** Поиск eval(), exec(), system(), password, secret, api_key, token
- **Анализ импортов:** Проверка корректности импортов logger
- **Проверка потокобезопасности:** Анализ использования threading.Lock

### Паттерны для поиска проблем:
- `TODO|FIXME|XXX|HACK` - технические долги
- `password|secret|api_key|token` - потенциальные утечки
- `eval\(|exec\(|system\(` - опасные функции
- `console\.log\(|print\(` - вывод в продакшен коде
- `\.replace\(|\.unlink\(|shutil\.move` - работа с файлами
- `\.lock\(\)|_lock|threading\.Lock` - потокобезопасность

---

## Заключение

Код проекта находится в хорошем состоянии. Найдено 4 критические проблемы, требующие немедленного исправления, 7 предупреждений для улучшения стабильности и 5 рекомендаций для долгосрочного улучшения архитектуры.

**Общий рейтинг качества:** 7.5/10

**Рекомендуемые действия:**
1. Немедленно исправить критические проблемы (приоритет 1)
2. Запланировать исправление предупреждений на следующую итерацию
3. Рассмотреть рекомендации для улучшения архитектуры
