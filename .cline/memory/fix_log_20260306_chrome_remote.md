# Лог исправлений: parser_2gis/chrome/remote.py

**Дата:** 2026-03-06  
**Файл:** `/home/d/parser-2gis/parser_2gis/chrome/remote.py`

## Проблема

При запуске параллельного парсинга с несколькими workers Chrome не успевает запуститься до попытки подключения. Ошибка:
```
Ошибка Chrome при подключении к DevTools Protocol: Не удалось создать вкладку: HTTPConnectionPool(host='127.0.0.1', port=XXXX): Max retries exceeded with url: /json/new
```

## Внесённые исправления

### 1. Добавлены новые импорты
- `import socket` - для проверки доступности порта
- `import time` - для задержек между попытками

### 2. Новая функция `_check_port_available()`
**Строки:** 64-84

Проверяет доступность порта через TCP socket перед подключением.

```python
def _check_port_available(port: int, timeout: float = 0.5) -> bool:
    """Проверяет доступность порта для подключения."""
```

### 3. Исправлен метод `_create_tab()`
**Строки:** 197-237

**Изменения:**
- Добавлены повторные попытки (max 10 попыток)
- Задержка между попытками: 1.5 секунды
- Увеличен timeout с 30 до 60 секунд
- Добавлено детальное логирование для отладки

**Было:**
```python
def _create_tab(self) -> pychrome.Tab:
    try:
        resp = requests.put('%s/json/new' % (self._dev_url), json=True, timeout=30)
        resp.raise_for_status()
        return pychrome.Tab(**resp.json())
    except (RequestException, ValueError, KeyError) as e:
        raise ChromeException(f'Не удалось создать вкладку: {e}')
```

**Стало:**
```python
def _create_tab(self) -> pychrome.Tab:
    max_attempts = 10
    delay_seconds = 1.5
    
    for attempt in range(max_attempts):
        try:
            logger.debug('Попытка %d/%d: создание вкладки...', attempt + 1, max_attempts)
            resp = requests.put(
                '%s/json/new' % (self._dev_url),
                json=True,
                timeout=60  # Увеличенный timeout для стабильности
            )
            resp.raise_for_status()
            logger.debug('Вкладка успешно создана')
            return pychrome.Tab(**resp.json())
        except (RequestException, ValueError, KeyError) as e:
            if attempt < max_attempts - 1:
                logger.warning('Не удалось создать вкладку (попытка %d): %s. Повторная попытка через %.1f сек...',
                             attempt + 1, e, delay_seconds)
                time.sleep(delay_seconds)
            else:
                raise ChromeException(f'Не удалось создать вкладку после {max_attempts} попыток: {e}')
```

### 4. Исправлен метод `start()`
**Строки:** 166-195

**Изменения:**
- Добавлена начальная задержка 0.5 сек после создания ChromeBrowser
- Добавлена проверка доступности порта перед подключением
- Добавлено логирование процесса запуска

**Ключевые изменения:**
```python
# Начальная задержка для запуска Chrome (даём время на старт)
logger.debug('Ожидание запуска Chrome (%.1f сек)...', 0.5)
time.sleep(0.5)

# Проверка доступности порта перед подключением
if not _check_port_available(remote_port, timeout=1.0):
    logger.warning('Порт %d недоступен, ожидание...', remote_port)
    time.sleep(1.0)
    if not _check_port_available(remote_port, timeout=1.0):
        raise ChromeException(f'Порт {remote_port} недоступен для подключения')
```

### 5. Исправлен метод `_connect_interface()`
**Строки:** 111-164

**Изменения:**
- Добавлена проверка доступности порта перед подключением
- Добавлено детальное логирование каждого шага
- Извлечение порта из `self._dev_url` для проверки

**Ключевые изменения:**
```python
# Извлекаем порт из dev_url для проверки
port = int(self._dev_url.split(':')[-1])

# Проверка доступности порта перед подключением
if not _check_port_available(port, timeout=0.5):
    logger.warning('Порт %d недоступен при подключении к DevTools', port)
    return False

logger.debug('Подключение к Chrome DevTools Protocol по адресу: %s', self._dev_url)
self._chrome_interface = pychrome.Browser(url=self._dev_url)

logger.debug('Создание вкладки через _create_tab()...')
self._chrome_tab = self._create_tab()

logger.debug('Запуск вкладки...')
self._chrome_tab.start()
```

## Итоговая сводка изменений

| Метод/Функция | Изменения |
|--------------|-----------|
| `_check_port_available()` | **Новая функция** - проверка TCP доступности порта |
| `_create_tab()` | Retry logic (10 попыток, 1.5с задержка), timeout 60с, логирование |
| `start()` | Initial delay 0.5с, проверка порта, логирование |
| `_connect_interface()` | Проверка порта, детальное логирование шагов |

## API совместимость

✅ **API класса НЕ изменён** - все публичные методы сохранили сигнатуры  
✅ **Все комментарии на русском языке**  
✅ **Синтаксис корректен** - проверка `py_compile` пройдена

## Рекомендации по тестированию

1. Запустить параллельный парсинг с несколькими workers
2. Проверить логи на наличие сообщений о повторных попытках
3. Убедиться в отсутствии ошибок "Connection refused"
