from __future__ import annotations

import functools
import sys
import time
import urllib.parse
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Union

from pydantic import ValidationError

if TYPE_CHECKING:
    from .logger import Logger

# Экспортируемые символы модуля
__all__ = [
    'running_linux',
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


def _is_sensitive_key(key: str) -> bool:
    """
    Проверяет, является ли ключ чувствительным.

    Args:
        key: Имя ключа для проверки.

    Returns:
        True если ключ чувствительный, False иначе.

    Примечание:
        Проверка включает:
        - Точное совпадение с известными чувствительными ключами
        - Совпадение по паттерну с учётом границ слов (избегает ложных
          срабатываний на ключах вроде 'keyboard', 'passage', 'token_count')
    """
    key_lower = key.lower()

    # Прямая проверка на точное совпадение
    if key_lower in _SENSITIVE_KEYS:
        return True

    # Проверка по паттерну с границами слов
    # Разделителями считаются '_', '-', цифры, начало/конец строки
    sensitive_patterns = ["pass", "secret", "token", "key", "auth", "cred"]
    for pattern in sensitive_patterns:
        if pattern in key_lower:
            # Находим позицию паттерна
            idx = key_lower.find(pattern)
            while idx != -1:
                # Проверяем левую границу (начало строки или разделитель)
                left_ok = idx == 0 or key_lower[idx - 1] in "_-"
                # Проверяем правую границу (конец строки или разделитель)
                right_idx = idx + len(pattern)
                right_ok = right_idx == len(key_lower) or key_lower[right_idx] in "_-"

                if left_ok and right_ok:
                    return True

                idx = key_lower.find(pattern, idx + 1)

    return False


def _sanitize_value(value: Any, key: Optional[str] = None, _visited: Optional[set[int]] = None) -> Any:
    """
    Очищает чувствительные данные из значения.

    Args:
        value: Значение для очистки.
        key: Имя ключа (опционально).
        _visited: Внутренний параметр для отслеживания посещённых объектов (защита от циклических ссылок).

    Returns:
        Очищенное значение или '<REDACTED>' для чувствительных данных.
    """
    # Инициализируем множество посещённых объектов для защиты от циклических ссылок
    if _visited is None:
        _visited = set()

    # Проверяем на циклические ссылки
    value_id = id(value)
    if value_id in _visited:
        return "<REDACTED>"  # Возвращаем маркер для циклической ссылки

    if key and _is_sensitive_key(key):
        return "<REDACTED>"

    # Рекурсивная обработка словарей
    if isinstance(value, dict):
        _visited.add(value_id)
        try:
            return {k: _sanitize_value(v, k, _visited) for k, v in value.items()}
        finally:
            _visited.discard(value_id)

    # Рекурсивная обработка списков
    if isinstance(value, list):
        _visited.add(value_id)
        try:
            return [_sanitize_value(item, _visited=_visited) for item in value]
        finally:
            _visited.discard(value_id)

    return value


def running_linux() -> bool:
    """Определяет, работает ли приложение на Linux.

    Returns:
        True если приложение работает на Linux (любой дистрибутив), False иначе.

    Примечание:
        Приложение разработано в первую очередь для Linux окружений.
    """
    return sys.platform.startswith("linux")


def _default_predicate(value: Any) -> bool:
    """Предикат по умолчанию для проверки результата.

    Args:
        value: Значение для проверки.

    Returns:
        True если значение истинно, False иначе.

    Примечание:
        Используется вместо bool для избежания проблем с передачей
        функции как аргумента по умолчанию в декораторе.
    """
    return bool(value)


def wait_until_finished(
    timeout: Optional[int] = None,
    finished: Optional[Callable[[Any], bool]] = None,
    throw_exception: bool = True,
    poll_interval: float = 0.1,
) -> Callable[..., Callable[..., Any]]:
    """Декоратор опрашивает обёрнутую функцию до истечения времени или пока
    предикат `finished` не вернёт `True`.

    Args:
        timeout: Максимальное время ожидания в секундах.
        finished: Предикат для успешного результата обёрнутой функции.
        throw_exception: Выбрасывать ли `TimeoutError`.
        poll_interval: Интервал опроса результата обёрнутой функции в секундах.

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
            # Поддерживаем оба варианта: override_* и оригинальные имена для обратной совместимости
            override_timeout: Optional[int] = None,
            override_finished: Optional[Callable[[Any], bool]] = None,
            override_throw_exception: Optional[bool] = None,
            override_poll_interval: Optional[float] = None,
            # Оригинальные имена для обратной совместимости с тестами
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
                except TimeoutError:
                    # Пробрасываем TimeoutError немедленно
                    raise
                except Exception as e:
                    # Логирование ошибок выполнения функции
                    logger = _get_logger()
                    logger.debug(
                        "Ошибка при выполнении функции %s (попытка): %s", func.__name__, e
                    )

                time.sleep(effective_poll)

        return inner

    return outer


def report_from_validation_error(
    ex: ValidationError, d: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
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

    Raises:
        ValueError: При ошибке обработки данных.

    Примечание безопасности:
        Функция автоматически фильтрует чувствительные данные (пароли, токены, ключи API)
        и заменяет их на '<REDACTED>' для предотвращения утечки конфиденциальной информации.
    """
    values: Dict[str, Any] = {}
    for error in ex.errors():
        msg = error["msg"]
        loc = error["loc"]
        attribute_path = ".".join([str(location) for location in loc])

        if d:
            value: Any = d
            last_key: Any = None
            for field in loc:
                if field == "__root__":
                    break
                if field in value:
                    last_key = field if isinstance(value, dict) else None
                    value = value[field]
                else:
                    value = "<No value>"
                    last_key = None
                    break

            # Очищаем чувствительные данные перед возвратом
            sanitized_value = _sanitize_value(value, last_key)

            values[attribute_path] = {
                "invalid_value": sanitized_value,
                "error_message": msg,
            }
        else:
            values[attribute_path] = {
                "error_message": msg,
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

        target = functools.reduce(lambda d, k: d.setdefault(k, {}), path[:-1], output)
        target[path[-1]] = value
    return output


def floor_to_hundreds(arg: Union[int, float]) -> int:
    """Округляет число вниз до ближайшей сотни.

    Args:
        arg: Число для округления.

    Returns:
        Округлённое вниз число до ближайшей сотни.

    Example:
        >>> floor_to_hundreds(1234)
        1200
        >>> floor_to_hundreds(1999)
        1900
        >>> floor_to_hundreds(50)
        0
    """
    return int((arg // 100) * 100)


def _validate_city(city: Any, field_name: str = "city") -> Dict[str, Any]:
    """Валидирует структуру города.

    Args:
        city: Словарь города для валидации.
        field_name: Имя поля для сообщений об ошибках (по умолчанию "city").

    Returns:
        Валидированный словарь города.

    Raises:
        ValueError: Если город некорректен.

    Примечание:
        Проверяет:
        - Тип данных (должен быть dict)
        - Наличие обязательных полей (code, domain)
        - Типы полей (должны быть str)
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

    return city


def _validate_category(category: Any) -> Dict[str, Any]:
    """Валидирует структуру категории.

    Args:
        category: Словарь категории для валидации.

    Returns:
        Валидированный словарь категории.

    Raises:
        ValueError: Если категория некорректна.

    Примечание:
        Проверяет:
        - Тип данных (должен быть dict)
        - Наличие query или name
    """
    logger = _get_logger()

    if not isinstance(category, dict):
        logger.warning("category не является словарём: %s", category)
        raise ValueError("category должен быть словарём")

    # Проверка наличия name или query
    if "name" not in category and "query" not in category:
        logger.warning("Категория должна содержать 'name' или 'query': %s", category)
        raise ValueError("category должен содержать 'name' или 'query'")

    return category


def generate_category_url(
    city: Dict[str, Any],
    category: Dict[str, Any],
) -> str:
    """Генерирует URL для парсинга категории в городе.

    Args:
        city: Словарь города с обязательными полями:
            - code (str): код города
            - domain (str): домен региона (например, 'ru', 'kz')
        category: Словарь категории с полями:
            - name (str): название категории
            - query (str, optional): поисковый запрос
            - rubric_code (str, optional): код рубрики

    Returns:
        URL для парсинга категории в городе.

    Примечание:
        Функция автоматически обрабатывает отсутствующие поля категории
        и использует name как fallback для query.
    """
    logger = _get_logger()

    # Валидация города
    city = _validate_city(city)

    # Валидация категории
    category = _validate_category(category)

    # Формируем базовый URL
    base_url = f'https://{city["domain"]}/{city["code"]}'

    # Получаем query категории с fallback на name
    category_query = category.get("query", category.get("name", ""))
    if not category_query:
        logger.warning("Категория не содержит query или name: %s", category)
        raise ValueError("category должен содержать query или name")

    # Кодируем query для URL
    rest_url = f'/search/{url_query_encode(category_query)}'

    # Добавляем rubric_code если есть
    if category.get("rubric_code"):
        rest_url += f'/rubricId/{category["rubric_code"]}'

    # Добавляем сортировку
    rest_url += "/filters/sort=name"

    return base_url + rest_url


def generate_city_urls(
    cities: List[Dict[str, Any]], query: str, rubric: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Генерирует URL для парсинга по списку городов.

    Args:
        cities: Список словарей городов с обязательными полями:
            - code (str): код города
            - domain (str): домен региона (например, 'ru', 'kz')
        query: Поисковый запрос (например, "Аптеки", "Рестораны").
        rubric: Словарь рубрики с полем code (опционально).

    Returns:
        Список URL для парсинга.

    Примечание:
        Функция автоматически пропускает города с отсутствующими обязательными полями
        или неверными типами данных, логируя предупреждения для каждого такого случая.
    """
    urls: List[str] = []
    logger = _get_logger()

    for city in cities:
        try:
            # Валидация города с использованием общей функции
            city = _validate_city(city, field_name="Элемент cities")

            # Формирование URL
            base_url = f'https://{city["domain"]}/{city["code"]}'
            rest_url = f"/search/{url_query_encode(query)}"

            if rubric and "code" in rubric:
                rest_url += f'/rubricId/{rubric["code"]}'

            rest_url += "/filters/sort=name"
            url = base_url + rest_url
            urls.append(url)

        except ValueError as e:
            logger.warning("Пропуск города из-за ошибки валидации: %s", e)
            continue
        except Exception as e:
            logger.error("Ошибка при генерации URL для города %s: %s", city, e)
            continue

    return urls


def url_query_encode(query: str) -> str:
    """Кодирует строку запроса для URL.

    Args:
        query: Исходная строка запроса.

    Returns:
        Закодированная строка для использования в URL.

    Примечание:
        Использует стандартный urllib.parse.quote для корректного
        кодирования всех специальных символов включая кириллицу.
        Пробелы кодируются как %20 для совместимости.
    """
    # Используем стандартный urllib.parse.quote для корректного кодирования
    # safe='' означает что все специальные символы будут закодированы
    encoded: str = urllib.parse.quote(query, safe="")
    return encoded
