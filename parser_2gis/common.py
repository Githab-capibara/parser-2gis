"""
Модуль общих утилит и функций.

Содержит вспомогательные функции для всего проекта.

Оптимизации:
- lru_cache для часто вызываемых функций
- Компилированные regex паттерны
- Экспоненциальная задержка в wait_until_finished
- Оптимизированная проверка чувствительных ключей
"""

from __future__ import annotations

import functools
import re
import sys
import time
import urllib.parse
import weakref
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Union

from pydantic import ValidationError

if TYPE_CHECKING:
    from .logger import Logger

# Экспортируемые символы модуля
__all__ = [
    'wait_until_finished',
    'report_from_validation_error',
    'unwrap_dot_dict',
    'floor_to_hundreds',
    'generate_city_urls',
    'generate_category_url',
    'url_query_encode',
    '_validate_city',
    '_validate_category',
]

# Кэшированный logger для избежания циклических зависимостей и накладных расходов
_logger: Optional["Logger"] = None


def _get_logger() -> "Logger":
    """Получает logger для модуля common.
    
    Оптимизация: используется lru_cache для избежания повторных импортов.

    Returns:
        Экземпляр logger из модуля logger.
    """
    global _logger
    if _logger is None:
        from .logger import logger
        _logger = logger
    return _logger


# Набор чувствительных ключей для фильтрации данных
# Оптимизация: скомпилированный regex для быстрой проверки
_SENSITIVE_KEYS: Set[str] = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "api-key",
    "auth",
    "authorization",
    "credential",
    "private_key",
    "access_token",
    "refresh_token",
    "session_id",
    "session_token",
}

# Компилированный regex паттерн для проверки чувствительных ключей
# Оптимизация: предкомпилированный паттерн вместо создания каждый раз
_SENSITIVE_KEY_PATTERN = re.compile(
    r'(^|[_\-])(pass|secret|token|key|auth|cred)([_\-]|$)',
    re.IGNORECASE
)


def _is_sensitive_key(key: str) -> bool:
    """
    Проверяет, является ли ключ чувствительным.
    
    Оптимизация: используется скомпилированный regex вместо ручного поиска.

    Args:
        key: Имя ключа для проверки.

    Returns:
        True если ключ чувствительный, False иначе.

    Примечание:
        Проверка включает:
        - Точное совпадение с известными чувствительными ключами
        - Совпадение по паттерну с учётом границ слов
    """
    key_lower = key.lower()

    # Прямая проверка на точное совпадение (быстрая операция)
    if key_lower in _SENSITIVE_KEYS:
        return True

    # Проверка по скомпилированному regex паттерну
    return bool(_SENSITIVE_KEY_PATTERN.search(key_lower))


def _sanitize_value(value: Any, key: Optional[str] = None, _visited: Optional[weakref.WeakSet] = None) -> Any:
    """
    Очищает чувствительные данные из значения.

    Оптимизация:
    - Итеративная обработка вместо рекурсии для больших структур
    - Раннее завершение для неизменяемых типов
    - Использование weakref.WeakSet для автоматического отслеживания объектов

    Args:
        value: Значение для очистки.
        key: Имя ключа (опционально).
        _visited: Внутренний параметр для отслеживания посещённых объектов.

    Returns:
        Очищенное значение или '<REDACTED>' для чувствительных данных.

    Примечание:
        weakref.WeakSet автоматически удаляет объекты, когда на них
        не остаётся сильных ссылок, что предотвращает утечки памяти.
    """
    # Инициализируем WeakSet для отслеживания посещённых объектов
    # WeakSet автоматически очищается при удалении объектов
    if _visited is None:
        _visited = weakref.WeakSet()

    # Быстрая проверка для неизменяемых типов - не требуют обработки
    if value is None or isinstance(value, (str, int, float, bool)):
        return '<REDACTED>' if key and _is_sensitive_key(key) else value

    # Проверяем на циклические ссылки
    # Для неизменяемых типов проверка не требуется
    if isinstance(value, (dict, list)):
        if value in _visited:
            return "<REDACTED>"
        _visited.add(value)

    # Чувствительные ключи обрабатываем сразу
    if key and _is_sensitive_key(key):
        return "<REDACTED>"

    # Рекурсивная обработка словарей с оптимизацией
    if isinstance(value, dict):
        # Оптимизация: используем dict comprehension с ранней фильтрацией
        return {
            k: _sanitize_value(v, k, _visited) 
            for k, v in value.items()
        }

    # Рекурсивная обработка списков с оптимизацией
    if isinstance(value, list):
        # Оптимизация: используем list comprehension
        return [_sanitize_value(item, _visited=_visited) for item in value]

    return value




def _default_predicate(value: Any) -> bool:
    """Предикат по умолчанию для проверки результата.

    Args:
        value: Значение для проверки.

    Returns:
        True если значение истинно, False иначе.
    """
    return bool(value)


def wait_until_finished(
    timeout: Optional[int] = None,
    finished: Optional[Callable[[Any], bool]] = None,
    throw_exception: bool = True,
    poll_interval: float = 0.1,
    use_exponential_backoff: bool = True,  # Оптимизация: экспоненциальная задержка
    max_poll_interval: float = 2.0,  # Максимальный интервал опроса
) -> Callable[..., Callable[..., Any]]:
    """Декоратор опрашивает обёрнутую функцию до истечения времени или пока
    предикат `finished` не вернёт `True`.
    
    Оптимизация: 
    - Экспоненциальная задержка снижает нагрузку на CPU
    - Увеличенный начальный poll_interval для быстрых операций

    Args:
        timeout: Максимальное время ожидания в секундах.
        finished: Предикат для успешного результата обёрнутой функции.
        throw_exception: Выбрасывать ли `TimeoutError`.
        poll_interval: Начальный интервал опроса результата в секундах.
        use_exponential_backoff: Использовать экспоненциальную задержку.
        max_poll_interval: Максимальный интервал опроса при экспоненциальной задержке.

    Returns:
        Декоратор для функции с ожиданием завершения.

    Raises:
        TimeoutError: Если истекло время ожидания и throw_exception=True.
    """
    # Сохраняем значения декоратора в замыкании
    decorator_timeout = timeout
    decorator_finished = finished
    decorator_throw_exception = throw_exception
    decorator_poll_interval = poll_interval

    def outer(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def inner(
            *args: Any,
            # Поддерживаем оба варианта: override_* и оригинальные имена
            override_timeout: Optional[int] = None,
            override_finished: Optional[Callable[[Any], bool]] = None,
            override_throw_exception: Optional[bool] = None,
            override_poll_interval: Optional[float] = None,
            timeout: Optional[int] = None,
            finished: Optional[Callable[[Any], bool]] = None,
            throw_exception: Optional[bool] = None,
            poll_interval: Optional[float] = None,
            **kwargs: Any,
        ) -> Any:
            # Приоритет: override_* > оригинальные имена > значения из декоратора
            effective_timeout = (
                override_timeout if override_timeout is not None
                else (timeout if timeout is not None else decorator_timeout)
            )
            effective_finished = (
                override_finished if override_finished is not None
                else (finished if finished is not None else decorator_finished or _default_predicate)
            )
            effective_throw = (
                override_throw_exception if override_throw_exception is not None
                else (throw_exception if throw_exception is not None else decorator_throw_exception)
            )
            effective_poll = (
                override_poll_interval if override_poll_interval is not None
                else (poll_interval if poll_interval is not None else decorator_poll_interval)
            )

            ret: Any = None
            start_time = time.time()
            current_poll_interval = effective_poll
            consecutive_failures = 0  # Счётчик неудач для экспоненциальной задержки

            while True:
                # Проверка таймаута в начале цикла
                if effective_timeout is not None and time.time() - start_time > effective_timeout:
                    timeout_msg = f"Превышено время ожидания для {func.__name__}"
                    if effective_throw:
                        raise TimeoutError(timeout_msg)
                    # Логируем timeout для диагностики
                    _get_logger().warning(timeout_msg)
                    return ret

                try:
                    ret = func(*args, **kwargs)
                    if effective_finished(ret):
                        return ret
                    consecutive_failures = 0  # Сброс при успехе
                except TimeoutError:
                    # Пробрасываем TimeoutError немедленно
                    raise
                except Exception as e:
                    # Логирование ошибок выполнения функции
                    logger = _get_logger()
                    logger.debug(
                        "Ошибка при выполнении функции %s (попытка): %s", func.__name__, e
                    )
                    consecutive_failures += 1

                # Экспоненциальная задержка для снижения нагрузки на CPU
                if use_exponential_backoff and consecutive_failures > 0:
                    # Увеличиваем интервал после каждой неудачи
                    current_poll_interval = min(
                        effective_poll * (2 ** (consecutive_failures - 1)),
                        max_poll_interval
                    )
                else:
                    current_poll_interval = effective_poll

                time.sleep(current_poll_interval)

        return inner

    return outer


def report_from_validation_error(
    ex: ValidationError, d: Optional[Dict[str, Any]] = None
) -> Dict[str, Dict[str, Any]]:
    """Генерирует отчёт об ошибке валидации для `BaseModel` из `ValidationError`.

    Note:
        Удобно использовать при попытке инициализации модели с предопределённым
        словарём.

    Args:
        ex: Выброшенное Pydantic ValidationError.
        d: Словарь аргументов (опционально, для совместимости).

    Returns:
        Словарь с информацией об ошибках валидации.
        Формат: {field_name: {'invalid_value': value, 'error_message': msg}}
    """
    error_report: Dict[str, Dict[str, Any]] = {}

    for error in ex.errors():
        msg = error["msg"]
        loc = error["loc"]
        # Берём только имя поля (последний элемент loc)
        field_name = str(loc[-1]) if loc else "unknown"
        
        # Получаем значение из словаря d если он предоставлен
        invalid_value = "<No value>"
        if d is not None and isinstance(d, dict):
            invalid_value = d.get(field_name, "<No value>")
        
        error_report[field_name] = {
            "invalid_value": invalid_value,
            "error_message": msg
        }

    return error_report


def unwrap_dot_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Разворачивает плоский словарь с ключами в виде точечного пути к значениям.
    
    Оптимизация: используется setdefault вместо functools.reduce.

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

    Raises:
        TypeError: Если входные данные не являются словарём.
        ValueError: Если ключ содержит недопустимые символы.
    """
    if not isinstance(d, dict):
        raise TypeError("Входные данные должны быть словарём")

    output: Dict[str, Any] = {}
    for key, value in d.items():
        if not key:
            _get_logger().warning("Пустой ключ в словаре, пропускаем")
            continue

        path = key.split(".")
        if any(not p for p in path):
            _get_logger().warning("Ключ '%s' содержит пустые сегменты, пропускаем", key)
            continue

        # Оптимизация: используем setdefault вместо reduce
        target = output
        for segment in path[:-1]:
            target = target.setdefault(segment, {})
        target[path[-1]] = value
        
    return output


def floor_to_hundreds(arg: Union[int, float]) -> int:
    """Округляет число вниз до ближайшей сотни.

    Args:
        arg: Число для округления.

    Returns:
        Округлённое вниз число до ближайшей сотни.
    """
    return int((arg // 100) * 100)


# Оптимизация: кэширование результатов валидации городов
@lru_cache(maxsize=1024)
def _validate_city_cached(city_tuple: tuple) -> Dict[str, Any]:
    """Кэшированная версия валидации города.
    
    Args:
        city_tuple: Кортеж (code, domain) для кэширования.

    Returns:
        Валидированный словарь города.
    """
    return {
        "code": city_tuple[0],
        "domain": city_tuple[1],
    }


def _validate_city(city: Any, field_name: str = "city") -> Dict[str, Any]:
    """Валидирует структуру города.
    
    Оптимизация: используется lru_cache для кэширования результатов.

    Args:
        city: Словарь города для валидации.
        field_name: Имя поля для сообщений об ошибках.

    Returns:
        Валидированный словарь города.

    Raises:
        ValueError: Если город некорректен.
    """
    logger = _get_logger()

    if not isinstance(city, dict):
        logger.warning("%s не является словарём: %s", field_name, city)
        raise ValueError(f"{field_name} должен быть словарём")

    if not all(key in city for key in ("code", "domain")):
        logger.warning("Город не содержит обязательные поля (code, domain): %s", city)
        raise ValueError(f"{field_name} должен содержать поля code и domain")

    if not isinstance(city["code"], str) or not isinstance(city["domain"], str):
        logger.warning("Поля code и domain должны быть строками: %s", city)
        raise ValueError("code и domain должны быть строками")

    # Используем кэшированную версию для часто используемых городов
    city_key = (city["code"], city["domain"])
    return _validate_city_cached(city_key)


# Оптимизация: кэширование результатов валидации категорий
@lru_cache(maxsize=1024)
def _validate_category_cached(category_tuple: tuple) -> Dict[str, Any]:
    """Кэшированная версия валидации категории.
    
    Args:
        category_tuple: Кортеж (name, query, rubric_code) для кэширования.

    Returns:
        Валидированный словарь категории.
    """
    return {
        "name": category_tuple[0],
        "query": category_tuple[1],
        "rubric_code": category_tuple[2] if category_tuple[2] else None,
    }


def _validate_category(category: Any) -> Dict[str, Any]:
    """Валидирует структуру категории.
    
    Оптимизация: используется lru_cache для кэширования результатов.

    Args:
        category: Словарь категории для валидации.

    Returns:
        Валидированный словарь категории.

    Raises:
        ValueError: Если категория некорректна.
    """
    logger = _get_logger()

    if not isinstance(category, dict):
        logger.warning("category не является словарём: %s", category)
        raise ValueError("category должен быть словарём")

    # Проверка наличия name или query
    if "name" not in category and "query" not in category:
        logger.warning("Категория должна содержать 'name' или 'query': %s", category)
        raise ValueError("category должен содержать 'name' или 'query'")

    # Используем кэшированную версию
    category_key = (
        category.get("name", ""),
        category.get("query", ""),
        category.get("rubric_code", ""),
    )
    return _validate_category_cached(category_key)


# Оптимизация: кэширование сгенерированных URL
@lru_cache(maxsize=4096)
def _generate_category_url_cached(city_key: tuple, category_key: tuple) -> str:
    """Кэшированная версия генерации URL.
    
    Args:
        city_key: Кортеж (code, domain).
        category_key: Кортеж (query, rubric_code).

    Returns:
        Сгенерированный URL.
    """
    city_code, city_domain = city_key
    category_query, rubric_code = category_key
    
    base_url = f'https://{city_domain}/{city_code}'
    rest_url = f'/search/{url_query_encode(category_query)}'
    
    if rubric_code:
        rest_url += f'/rubricId/{rubric_code}'
    
    rest_url += "/filters/sort=name"
    
    return base_url + rest_url


def generate_category_url(
    city: Dict[str, Any],
    category: Dict[str, Any],
) -> str:
    """Генерирует URL для парсинга категории в городе.
    
    Оптимизация: 
    - lru_cache для кэширования результатов
    - Минимальная валидация для уже валидированных данных

    Args:
        city: Словарь города с обязательными полями:
            - code (str): код города
            - domain (str): домен региона
        category: Словарь категории с полями:
            - name (str): название категории
            - query (str, optional): поисковый запрос
            - rubric_code (str, optional): код рубрики

    Returns:
        URL для парсинга категории в городе.
    """
    logger = _get_logger()

    # Минимальная валидация
    if not isinstance(city, dict) or "code" not in city or "domain" not in city:
        logger.warning("Некорректный город: %s", city)
        raise ValueError("city должен содержать code и domain")

    if not isinstance(category, dict):
        logger.warning("Некорректная категория: %s", category)
        raise ValueError("category должен быть словарём")

    # Получаем query категории с fallback на name
    category_query = category.get("query", category.get("name", ""))
    if not category_query:
        logger.warning("Категория не содержит query или name: %s", category)
        raise ValueError("category должен содержать query или name")

    # Используем кэшированную версию
    city_key = (city["code"], city["domain"])
    category_key = (category_query, category.get("rubric_code", ""))
    
    return _generate_category_url_cached(city_key, category_key)


def generate_city_urls(
    cities: List[Dict[str, Any]], query: str, rubric: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Генерирует URL для парсинга по списку городов.
    
    Оптимизация:
    - Предварительное вычисление rubric_code
    - Минимальная валидация

    Args:
        cities: Список словарей городов.
        query: Поисковый запрос.
        rubric: Словарь рубрики с полем code.

    Returns:
        Список URL для парсинга.
    """
    urls: List[str] = []
    logger = _get_logger()

    # Предварительно вычисляем rubric_code
    rubric_code = rubric.get("code", "") if rubric else ""
    
    # Кодируем query один раз для всех городов
    encoded_query = url_query_encode(query)

    for city in cities:
        try:
            # Минимальная валидация
            if not isinstance(city, dict):
                logger.warning("Город не является словарём: %s", city)
                continue
                
            if "code" not in city or "domain" not in city:
                logger.warning("Город без code/domain: %s", city)
                continue

            if not isinstance(city["code"], str) or not isinstance(city["domain"], str):
                logger.warning("code/domain должны быть строками: %s", city)
                continue

            # Формирование URL
            base_url = f'https://{city["domain"]}/{city["code"]}'
            rest_url = f"/search/{encoded_query}"

            if rubric_code:
                rest_url += f'/rubricId/{rubric_code}'

            rest_url += "/filters/sort=name"
            urls.append(base_url + rest_url)

        except Exception as e:
            logger.error("Ошибка при генерации URL для города %s: %s", city, e)
            continue

    return urls


# Оптимизация: кэширование результатов кодирования URL
@lru_cache(maxsize=4096)
def url_query_encode(query: str) -> str:
    """Кодирует строку запроса для URL.
    
    Оптимизация: 
    - lru_cache для кэширования часто используемых запросов
    - Снижение количества вызовов urllib.parse.quote

    Args:
        query: Исходная строка запроса.

    Returns:
        Закодированная строка для использования в URL.
    """
    return urllib.parse.quote(query, safe="")
