from __future__ import annotations

import functools
import re
import sys
import time
import urllib.parse
import warnings
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Union

from pydantic import ValidationError

if TYPE_CHECKING:
    from .logger import Logger

# Кэшированный logger для избежания циклических зависимостей и накладных расходов
_logger: Optional['Logger'] = None


def _get_logger() -> 'Logger':
    """Получает logger для модуля common.
    
    Returns:
        Экземпляр logger из модуля logger.
    """
    global _logger
    if _logger is None:
        from .logger import logger
        _logger = logger
    return _logger


# Набор чувствительных ключей для фильтрации данных
_SENSITIVE_KEYS: Set[str] = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'api-key', 'auth', 'authorization', 'credential', 'private_key',
    'access_token', 'refresh_token', 'session_id', 'session_token'
}


def _is_sensitive_key(key: str) -> bool:
    """
    Проверяет, является ли ключ чувствительным.
    
    Args:
        key: Имя ключа для проверки.
        
    Returns:
        True если ключ чувствительный, False иначе.
    """
    key_lower = key.lower()
    # Прямая проверка
    if key_lower in _SENSITIVE_KEYS:
        return True
    # Проверка по паттерну (содержит чувствительное слово)
    sensitive_patterns = ['pass', 'secret', 'token', 'key', 'auth', 'cred']
    return any(pattern in key_lower for pattern in sensitive_patterns)


def _sanitize_value(value: Any, key: Optional[str] = None) -> Any:
    """
    Очищает чувствительные данные из значения.
    
    Args:
        value: Значение для очистки.
        key: Имя ключа (опционально).
        
    Returns:
        Очищенное значение или '<REDACTED>' для чувствительных данных.
    """
    if key and _is_sensitive_key(key):
        return '<REDACTED>'
    
    # Рекурсивная обработка словарей
    if isinstance(value, dict):
        return {k: _sanitize_value(v, k) for k, v in value.items()}
    
    # Рекурсивная обработка списков
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    
    return value


def running_linux() -> bool:
    """Определяет, является ли текущая ОС Linux Ubuntu.
    
    Returns:
        True - приложение работает только на Linux Ubuntu.
    """
    # Приложение поддерживает только Linux Ubuntu
    return sys.platform.startswith('linux')


def wait_until_finished(timeout: Optional[int] = None,
                        finished: Optional[Callable[[Any], bool]] = None,
                        throw_exception: bool = True,
                        poll_interval: float = 0.1) -> Callable[..., Callable[..., Any]]:
    """Декоратор опрашивает обёрнутую функцию до истечения времени или пока
    предикат `finished` не вернёт `True`.

    Args:
        timeout: Максимальное время ожидания в секундах.
        finished: Предикат для успешного результата обёрнутой функции.
        throw_exception: Выбрасывать ли `TimeoutError`.
        poll_interval: Интервал опроса результата обёрнутой функции в секундах.
        
    Returns:
        Декоратор для функции с ожиданием завершения.
    """
    def outer(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def inner(*args: Any,
                  timeout: Optional[int] = timeout,
                  finished: Optional[Callable[[Any], bool]] = finished,
                  throw_exception: bool = throw_exception,
                  poll_interval: float = poll_interval,
                  **kwargs: Any) -> Any:
            # Инициализируем finished внутри функции для избежания изменяемого аргумента по умолчанию
            inner_finished = finished if finished is not None else bool

            call_time = time.time()
            while True:
                try:
                    ret = func(*args, **kwargs)
                    if inner_finished(ret):
                        return ret
                except Exception as e:
                    # Логирование ошибок выполнения функции
                    logger = _get_logger()
                    logger.warning('Ошибка при выполнении функции %s: %s', func.__name__, e)
                    # Проверяем таймаут даже при ошибках
                    if timeout is not None and time.time() - call_time > timeout:
                        if throw_exception:
                            raise TimeoutError(f'Превышено время ожидания для {func.__name__}')
                        return None
                    time.sleep(poll_interval)
                    continue

                # Проверяем таймаут
                if timeout is not None:
                    if time.time() - call_time > timeout:
                        if throw_exception:
                            raise TimeoutError(f'Превышено время ожидания для {func.__name__}')
                        return ret

                time.sleep(poll_interval)
        return inner
    return outer


def report_from_validation_error(ex: ValidationError,
                                 d: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Генерирует отчёт об ошибке валидации для `BaseModel` из `ValidationError`.

    Note:
        Удобно использовать при попытке инициализации модели с предопределённым
        словарём. Например:

        class TestModel(BaseModel):
            test_int: int

        try:
            d = {'test_int': '_12'}
            m = TestModel(**d)
        except ValidationError as ex:
            print(report_from_validation_error(ex, d))

    Args:
        d: Словарь аргументов.
        ex: Выброшенное Pydantic ValidationError.

    Returns:
        Словарь с информацией об ошибках валидации.
        {
            'полный_путь_неверного_атрибута': {
                'неверное_значение': ...,
                'сообщение_об_ошибке': ...,
            },
            ...
        }

    Примечание безопасности:
        Функция автоматически фильтрует чувствительные данные (пароли, токены, ключи API)
        и заменяет их на '<REDACTED>' для предотвращения утечки конфиденциальной информации.
    """
    values: Dict[str, Any] = {}
    for error in ex.errors():
        msg = error['msg']
        loc = error['loc']
        attribute_path = '.'.join([str(location) for location in loc])

        if d:
            value: Any = d
            last_key: Optional[str] = None
            for field in loc:
                if field == '__root__':
                    break
                if field in value:
                    last_key = field if isinstance(value, dict) else None
                    value = value[field]
                else:
                    value = '<No value>'
                    last_key = None
                    break

            # Очищаем чувствительные данные перед возвратом
            sanitized_value = _sanitize_value(value, last_key)
            
            values[attribute_path] = {
                'invalid_value': sanitized_value,
                'error_message': msg,
            }
        else:
            values[attribute_path] = {
                'error_message': msg,
            }

    return values


def unwrap_dot_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Разворачивает плоский словарь с ключами в виде точечного пути к значениям.

    Example:
        Вход:
            {
                'full.path.fieldname': 'value1',
                'another.fieldname': 'value2',
            }

        Выход:
            {
                'full': {
                    'path': {
                        'filedname': 'value1',
                    },
                },
                'another': {
                    'fieldname': 'value2',
                },
            }
            
    Args:
        d: Плоский словарь с ключами в виде точечного пути.
        
    Returns:
        Вложенный словарь с развёрнутой структурой.
    """
    output: Dict[str, Any] = {}
    for key, value in d.items():
        path = key.split('.')
        target = functools.reduce(lambda d, k: d.setdefault(k, {}), path[:-1], output)
        target[path[-1]] = value
    return output


def floor_to_hundreds(arg: Union[int, float]) -> int:
    """Округляет число вниз до ближайшей сотни.
    
    Args:
        arg: Число для округления.
        
    Returns:
        Округлённое вниз число до ближайшей сотни.
    """
    return int(arg // 100 * 100)


def generate_city_urls(cities: List[Dict[str, Any]], 
                       query: str, 
                       rubric: Optional[Dict[str, Any]] = None) -> List[str]:
    """Генерирует URL для парсинга по списку городов.

    Args:
        cities: Список словарей городов с полями name, code, domain, country_code.
        query: Поисковый запрос (например, "Аптеки", "Рестораны").
        rubric: Словарь рубрики с полями code, label (опционально).

    Returns:
        Список URL для парсинга.
        
    Примечание:
        Функция автоматически пропускает города с отсутствующими обязательными полями
        и логирует предупреждения для каждого такого случая.
    """
    urls: List[str] = []
    logger = _get_logger()

    for city in cities:
        try:
            # Валидация данных города
            if not isinstance(city, dict):
                logger.warning('Элемент cities не является словарём: %s', city)
                continue
                
            if not all(key in city for key in ('code', 'domain')):
                logger.warning('Город не содержит обязательные поля (code, domain): %s', city)
                continue

            # Проверка типов полей
            if not isinstance(city['code'], str) or not isinstance(city['domain'], str):
                logger.warning('Поля code и domain должны быть строками: %s', city)
                continue

            base_url = f'https://2gis.{city["domain"]}/{city["code"]}'
            rest_url = f'/search/{url_query_encode(query)}'

            if rubric and 'code' in rubric:
                rest_url += f'/rubricId/{rubric["code"]}'

            rest_url += '/filters/sort=name'
            url = base_url + rest_url
            urls.append(url)
            
        except Exception as e:
            # Логирование непредвиденных ошибок при обработке города
            logger.error('Ошибка при генерации URL для города %s: %s', city, e)
            continue

    return urls


def _is_safe_char(char: str) -> bool:
    """
    Проверяет, является ли символ безопасным для URL (не требует кодирования).
    
    Безопасные символы:
    - Кириллица (а-я, А-Я, ё, Ё)
    - Пробел
    
    Args:
        char: Символ для проверки.
        
    Returns:
        True если символ безопасный, False иначе.
    """
    char_code = ord(char)
    # Диапазоны кириллических символов
    cyrillic_lower_start = 0x0430  # 1072 - 'а'
    cyrillic_lower_end = 0x044F    # 1103 - 'я'
    cyrillic_upper_start = 0x0410  # 1040 - 'А'
    cyrillic_upper_end = 0x042F    # 1071 - 'Я'
    io_lower = 0x0451                # 1105 - 'ё'
    io_upper = 0x0401                # 1025 - 'Ё'
    space = 0x20                     # 32 - пробел
    
    return (
        cyrillic_lower_start <= char_code <= cyrillic_lower_end or
        cyrillic_upper_start <= char_code <= cyrillic_upper_end or
        char_code == io_lower or
        char_code == io_upper or
        char_code == space
    )


def url_query_encode(query: str) -> str:
    """Кодирует строку запроса для URL.

    Args:
        query: Исходная строка запроса.

    Returns:
        Закодированная строка для использования в URL.

    Примечание:
        Кириллические символы и пробелы остаются без изменений для читаемости URL.
        Все остальные символы (латиница, цифры, спецсимволы) кодируются в UTF-8.
    """
    # Используем генератор списка для лучшей читаемости и производительности
    return ''.join(
        char if _is_safe_char(char) else urllib.parse.quote(char, safe='')
        for char in query
    )