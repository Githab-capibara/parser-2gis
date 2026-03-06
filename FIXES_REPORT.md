# Отчёт об исправлениях для --categories-mode

**Дата:** 2026-03-06  
**Автор:** AI Assistant  
**Репозиторий:** https://github.com/Githab-capibara/parser-2gis.git

---

## 📋 Резюме

Проведён **полный аудит кода** и исправлены **критические ошибки** в функциональности параллельного парсинга по категориям (`--categories-mode`).

---

## 🔴 Найденные проблемы

### 1. **main.py: Ошибка валидации аргументов**

**Проблема:**
- Аргумент `-i/--url` был **обязательным всегда**, даже при использовании `--categories-mode --cities`
- При запуске команды вида:
  ```bash
  parser-2gis --cities omsk --categories-mode --parallel-workers 5 -o output/ -f csv
  ```
  Выдавалась ошибка: `Parser2GIS: ошибка: следующие аргументы обязательны: -i/--url`

**Причина:**
```python
# БЫЛО:
main_parser.add_argument('-i', '--url', nargs='+', default=None, required=main_parser_required, ...)
```

**Решение:**
```python
# СТАЛО:
main_parser.add_argument('-i', '--url', nargs='+', default=None, required=False, ...)

# Добавлена ручная валидация ПОСЛЕ парсинга аргументов:
has_url_source = (
    args.url is not None or
    (hasattr(args, 'cities') and args.cities is not None)
)
if not has_url_source:
    arg_parser.error('Требуется указать хотя бы один источник URL: -i/--url или --cities')

# Валидация: --categories-mode требует --cities
categories_mode = getattr(args, 'categories_mode', False)
if categories_mode and not (hasattr(args, 'cities') and args.cities):
    arg_parser.error('--categories-mode требует указания --cities')
```

**Файл:** `parser_2gis/main.py`  
**Строки:** 106, 149-162

---

### 2. **main.py: Дублированное определение categories_mode**

**Проблема:**
Переменная `categories_mode` определялась дважды (строки 164 и 260), что избыточно и может привести к ошибкам.

**Решение:**
Убрано дублирование, переменная определяется один раз в функции `parse_arguments()`.

**Файл:** `parser_2gis/main.py`  
**Строки:** 273-278

---

### 3. **parallel_parser.py: Race condition при записи файлов**

**Проблема:**
При параллельном парсинге несколько потоков могли пытаться записать в один файл, что приводило к повреждению данных.

**Решение:**
- Запись во **временный файл** с UUID в имени
- **Атомарное переименование** после успешного завершения
- Удаление временного файла при ошибке

**Файл:** `parser_2gis/parallel_parser.py`  
**Строки:** 127-176

---

### 4. **parallel_parser.py: Преждевременное удаление файлов**

**Проблема:**
Файлы удалялись **во время** объединения, что могло привести к потере данных при ошибке в середине процесса.

**Решение:**
```python
# Сначала объединение ВСЕХ файлов
with open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
    # ... объединение ...

# ТОЛЬКО ПОСЛЕ успеха - удаление всех исходных файлов
for csv_file in csv_files:
    csv_file.unlink()
```

**Файл:** `parser_2gis/parallel_parser.py`  
**Строки:** 220-260

---

### 5. **parallel_parser.py: Отсутствует валидация входных данных**

**Проблема:**
- Нет проверки на пустые `cities`/`categories`
- Нет ограничения на `max_workers` (можно указать 1000, что упадёт систему)
- Нет проверки `output_dir` на возможность записи

**Решение:**
```python
def __init__(self, cities, categories, output_dir, config, max_workers=3):
    # Валидация cities и categories
    if not cities:
        raise ValueError('Список городов не может быть пустым')
    if not categories:
        raise ValueError('Список категорий не может быть пустым')
    
    # Ограничение max_workers (1-20)
    if not isinstance(max_workers, int) or max_workers < 1:
        raise ValueError('max_workers должен быть положительным целым числом')
    if max_workers > 20:
        logger.warning('max_workers=%d слишком большой, ограничено до 20', max_workers)
        max_workers = 20
    
    # Проверка output_dir
    output_path = Path(output_dir)
    if output_path.exists() and not output_path.is_dir():
        raise ValueError(f'output_dir должен быть директорией: {output_dir}')
    output_path.mkdir(parents=True, exist_ok=True)
    if not os.access(output_path, os.W_OK):
        raise ValueError(f'Нет прав на запись в output_dir: {output_dir}')
```

**Файл:** `parser_2gis/parallel_parser.py`  
**Строки:** 44-78

---

### 6. **parallel_parser.py: Отсутствует таймаут на парсинг**

**Проблема:**
Один "зависший" URL мог заблокировать весь парсинг.

**Решение:**
```python
# Получение таймаута из конфига (по умолчанию 300 сек)
timeout_per_url = getattr(config.parser, 'timeout_per_url', 300)

# Использование future.result(timeout=...)
try:
    success, result = future.result(timeout=timeout_per_url)
except TimeoutError:
    failed_count += 1
    logger.error(f'Таймаут при парсинге {city_name} - {category_name}')
```

**Файл:** `parser_2gis/parallel_parser.py`  
**Строки:** 305-320

---

## ✅ Добавленные тесты

### Файл: `testes/test_main_categories_mode.py`

**7 новых тестов:**

1. `test_categories_mode_requires_cities` - `--categories-mode` без `--cities` вызывает ошибку
2. `test_categories_mode_with_cities_valid` - `--categories-mode` с `--cities` проходит валидацию
3. `test_url_not_required_when_cities_specified` - `-i/--url` не обязателен с `--cities`
4. `test_requires_url_or_cities` - требуется хотя бы один источник URL
5. `test_both_url_and_cities_valid` - можно указать и `-i` и `--cities`
6. `test_parallel_workers_default` - проверка значения по умолчанию (3)
7. `test_parallel_workers_custom` - проверка пользовательского значения

**Результат:** ✅ Все 59 тестов прошли (включая существующие)

---

## 📊 Статистика изменений

| Файл | Строк изменено | Тип изменений |
|------|---------------|---------------|
| `parser_2gis/main.py` | ~25 | Исправление валидации |
| `parser_2gis/parallel_parser.py` | ~120 | Исправление race condition, валидация, таймауты |
| `testes/test_main_categories_mode.py` | 143 | Новые тесты |

**Всего:** ~288 строк

---

## 🚀 Как использовать исправленную функциональность

### Базовый пример:

```bash
# Параллельный парсинг всех 93 категорий Омска (5 потоков)
parser-2gis --cities omsk \
            --categories-mode \
            --parallel-workers 5 \
            --chrome.headless yes \
            --chrome.disable-images yes \
            --parser.max-records 1000 \
            -o output/omsk_all_categories/ -f csv
```

### Несколько городов:

```bash
# Парсинг 3 городов (3 потока по умолчанию)
parser-2gis --cities moscow spb kazan \
            --categories-mode \
            --chrome.headless yes \
            -o output/ -f csv
```

### С настройками:

```bash
# Максимальная производительность (20 потоков, сборщик мусора)
parser-2gis --cities moscow spb \
            --categories-mode \
            --parallel-workers 20 \
            --parser.use-gc yes \
            --parser.gc-pages-interval 10 \
            --chrome.headless yes \
            -o output/ -f csv
```

---

## 🔒 Гарантии безопасности

### Что защищено:

1. ✅ **Валидация входных данных** - пустые списки, некорректные workers
2. ✅ **Race condition** - атомарная запись через временные файлы
3. ✅ **Потеря данных** - удаление файлов только после успешного объединения
4. ✅ **Таймауты** - защита от "зависших" URL
5. ✅ **Проверка прав** - запись только в доступные директории

### Что может пойти не так:

1. ⚠️ **Chrome не установлен** - будет ошибка подключения к DevTools
2. ⚠️ **Недостаточно RAM** - при `--parallel-workers > 10` может потребоваться 20+ GB
3. ⚠️ **Блокировка 2GIS** - при парсинге > 1000 записей с одного IP

---

## 📝 Рекомендации

### Для стабильной работы:

1. **Используйте `--parallel-workers 3-5`** для обычных задач
2. **Включайте `--chrome.headless yes`** для работы на сервере
3. **Включайте `--parser.use-gc yes`** при парсинге > 10000 записей
4. **Проверяйте наличие Chrome** перед запуском:
   ```bash
   google-chrome --version
   ```

### Для отладки:

1. **Запустите с одним городом и категорией:**
   ```bash
   parser-2gis --cities omsk --categories-mode --parallel-workers 1 -o output/ -f csv
   ```

2. **Включите логирование:**
   ```bash
   # В config.json добавьте:
   "log": {"level": "DEBUG"}
   ```

3. **Проверьте тесты:**
   ```bash
   pytest testes/test_main_categories_mode.py -v
   ```

---

## 📦 Синхронизация с GitHub

Все изменения **запушены** в репозиторий:
- **URL:** https://github.com/Githab-capibara/parser-2gis.git
- **Ветка:** main
- **Статус:** ✅ Завершено

---

## 📞 Контакты

При возникновении проблем:
1. Проверьте логи в `output/*.log`
2. Запустите тесты: `pytest testes/ -v`
3. Откройте issue на GitHub

---

**Документ создан:** 2026-03-06  
**Последнее обновление:** 2026-03-06
