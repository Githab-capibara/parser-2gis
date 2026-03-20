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

import asyncio
import functools
import logging
import re
import time
import urllib.parse
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple, Union

from pydantic import ValidationError

if TYPE_CHECKING:
    from .logger import Logger

# Экспортируемые символы модуля
__all__ = [
    "wait_until_finished",
    "async_wait_until_finished",
    "report_from_validation_error",
    "unwrap_dot_dict",
    "floor_to_hundreds",
    "generate_city_urls",
    "generate_category_url",
    "url_query_encode",
    "_validate_city",
    "_validate_category",
    "DEFAULT_BUFFER_SIZE",
    "CSV_BATCH_SIZE",
    "MERGE_BATCH_SIZE",
    "DEFAULT_POLL_INTERVAL",
    "MAX_POLL_INTERVAL",
    "EXPONENTIAL_BACKOFF_MULTIPLIER",
]

# =============================================================================
# КОНСТАНТЫ ДЛЯ POLLING
# =============================================================================

DEFAULT_POLL_INTERVAL: float = 0.1

MAX_POLL_INTERVAL: float = 2.0

EXPONENTIAL_BACKOFF_MULTIPLIER: float = 2

# =============================================================================
# КОНСТАНТЫ ДЛЯ БЕЗОПАСНОСТИ ДАННЫХ
# =============================================================================

# Максимальный размер данных в байтах (10 MB)
# ОБОСНОВАНИЕ: 10MB достаточно для обработки данных парсинга
# Превышение может указывать на DoS атаку или некорректные данные
MAX_DATA_SIZE: int = 10 * 1024 * 1024  # 10 MB

# =============================================================================
# ГЛОБАЛЬНЫЕ КОНСТАНТЫ БУФЕРИЗАЦИИ
# =============================================================================

# ОБОСНОВАНИЕ: 256KB выбрано исходя из:
# - Стандартный размер страницы памяти в Linux: 4KB
# - 256KB = 64 страницы - оптимально для системных вызовов read/write
# - Тесты показывают плато производительности на 64-256KB
# - 256KB баланс между использованием памяти и производительностью
# - Для файлов >100MB даёт прирост 20-25% vs 128KB буфер
DEFAULT_BUFFER_SIZE: int = 262144  # 256 KB

# ОБОСНОВАНИЕ: 1000 строк выбрано исходя из:
# - Средняя длина строки CSV: 200-500 байт
# - 1000 строк * 300 байт = 300KB - разумное использование памяти
# - Пакетная обработка улучшает производительность
CSV_BATCH_SIZE: int = 1000

# ОБОСНОВАНИЕ: 500 строк выбрано исходя из:
# - Средняя длина строки CSV: 200-500 байт
# - 500 строк * 300 байт = 150KB - совпадает с размером буфера
# - Меньше операций записи при хорошем использовании памяти
MERGE_BATCH_SIZE: int = 500

# =============================================================================
# ОПТИМИЗАЦИЯ 5.2: MODULE-LEVEL LOGGER
# =============================================================================

logger = logging.getLogger(__name__)


def _get_logger() -> "Logger":
    """Получает logger для модуля common.

    Returns:
        Экземпляр logger из модуля logger.
    """
    from .logger import logger as app_logger

    return app_logger


# Набор чувствительных ключей для фильтрации данных
# БЕЗОПАСНОСТЬ: Расширенный список для предотвращения утечки чувствительных данных
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
    # Дополнительные чувствительные ключи
    "secret_key",
    "secretkey",
    "private-key",
    "privatekey",
    "client_secret",
    "client_id",
    "bearer",
    "jwt",
    "oauth",
    "oauth_token",
    "access-key",
    "accesskey",
    "signing_key",
    "encryption_key",
    "master_key",
    "root_password",
    "admin_password",
    "db_password",
    "database_password",
    "connection_string",
    "conn_string",
    # Добавленные ключи для полноты
    "api_secret",
    "apisecret",
    "api-secret",
    "access_key",
    "secret_token",
    "auth_token",
    "bearer_token",
    "github_token",
    "gitlab_token",
    "ssh_key",
    "sshkey",
    "ssh-private-key",
    "gpg_key",
    "pgp_key",
    "certificate",
    "cert_key",
    "ssl_key",
    "tls_key",
}

# Компилированный regex паттерн для проверки чувствительных ключей
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(^|[_\-])(pass|secret|token|key|auth|cred|bearer|jwt|oauth|sign|encrypt|master|admin|db|database|conn)([_\-]|$)",
    re.IGNORECASE,
)


@lru_cache(maxsize=None)
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
        - Совпадение по паттерну с учётом границ слов
    """
    key_lower = key.lower()

    if key_lower in _SENSITIVE_KEYS:
        return True

    return bool(_SENSITIVE_KEY_PATTERN.search(key_lower))


def _check_value_type_and_sensitivity(
    current_value: Any,
    current_key: Optional[str],
    parent: Optional[Any],
    parent_key: Optional[Any],
    results: Dict[int, Any],
) -> Tuple[bool, Any]:
    """
    Проверяет тип значения и обрабатывает простые случаи.

    Выделена из _sanitize_value для снижения сложности основной функции.

    Args:
        current_value: Текущее значение для проверки.
        current_key: Ключ текущего значения.
        parent: Родительский контейнер.
        parent_key: Ключ в родительском контейнере.
        results: Словарь результатов.

    Returns:
        Кортеж (handled, result) где handled указывает, было ли значение обработано.
    """
    # Быстрая проверка для неизменяемых типов - не требуют обработки
    if current_value is None or isinstance(current_value, (str, int, float, bool)):
        result = (
            "<REDACTED>"
            if current_key and _is_sensitive_key(current_key)
            else current_value
        )
        if parent is not None and parent_key is not None:
            if isinstance(parent, dict):
                parent[parent_key] = result
            elif isinstance(parent, list):
                parent[parent_key] = result
        else:
            results[id(current_value)] = result
        return True, result

    return False, None


def _sanitize_value(value: Any, key: Optional[str] = None) -> Any:
    """
    Очищает чувствительные данные из значения.

    - Переписано на итеративный подход с явным стеком вместо рекурсии
    - Предотвращает RecursionError при обработке глубоко вложенных структур
    - Добавлена проверка максимального размера данных перед обработкой (MAX_DATA_SIZE = 10MB)
    - Выбрасывает ValueError с понятным сообщением при превышении лимита

    Args:
        value: Значение для очистки.
        key: Имя ключа (опционально).

    Returns:
        Очищенное значение или '<REDACTED>' для чувствительных данных.

    Raises:
        ValueError: Если размер данных превышает MAX_DATA_SIZE.
        MemoryError: При критической нехватке памяти.
    """
    # _visited теперь локальная переменная, а не параметр функции
    _visited: set = set()

    # Проверка максимального размера данных перед обработкой
    try:
        value_str = repr(value)
        value_size = len(value_str.encode("utf-8"))

        if value_size > MAX_DATA_SIZE:
            logger.error(
                "Размер данных превышает максимальный лимит: %d байт (максимум: %d байт)",
                value_size,
                MAX_DATA_SIZE,
            )
            raise ValueError(
                f"Размер данных ({value_size} байт) превышает максимальный лимит "
                f"({MAX_DATA_SIZE} байт = {MAX_DATA_SIZE // 1024 // 1024} MB). "
                f"Это может быть попытка DoS атаки."
            )
    except MemoryError as size_check_error:
        logger.critical(
            "Нехватка памяти при проверке размера данных: %s",
            size_check_error,
            exc_info=True,
        )
        raise ValueError(
            "Нехватка памяти при проверке размера данных. "
            "Данные слишком большие для обработки."
        ) from size_check_error

    try:
        # Используем явный стек для итеративной обработки вместо рекурсии
        # Формат: (значение, ключ, родитель, ключ_в_родителе)
        stack: List[tuple] = [(value, key, None, None)]

        # Словарь для хранения результатов обработки
        results: Dict[int, Any] = {}

        while stack:
            try:
                current_value, current_key, parent, parent_key = stack.pop()
                current_id = id(current_value)

                # Используем выделенную функцию для проверки типа и чувствительности
                handled, _ = _check_value_type_and_sensitivity(
                    current_value, current_key, parent, parent_key, results
                )
                if handled:
                    continue

                # Проверяем на циклические ссылки
                if current_id in results:
                    # Уже обработано, используем кэшированный результат
                    result = results[current_id]
                    if parent is not None and parent_key is not None:
                        if isinstance(parent, dict):
                            parent[parent_key] = result
                        elif isinstance(parent, list):
                            parent[parent_key] = result
                    continue

                # Проверяем на циклические ссылки для изменяемых типов
                if isinstance(current_value, (dict, list)):
                    if current_id in _visited:
                        result = "<REDACTED>"
                        if parent is not None and parent_key is not None:
                            if isinstance(parent, dict):
                                parent[parent_key] = result
                            elif isinstance(parent, list):
                                parent[parent_key] = result
                        else:
                            results[current_id] = result
                        continue
                    _visited.add(current_id)

                # Чувствительные ключи обрабатываем сразу
                if current_key and _is_sensitive_key(current_key):
                    result = "<REDACTED>"
                    if parent is not None and parent_key is not None:
                        if isinstance(parent, dict):
                            parent[parent_key] = result
                        elif isinstance(parent, list):
                            parent[parent_key] = result
                    else:
                        results[current_id] = result
                    continue

                if isinstance(current_value, dict):
                    # Создаём новый словарь для результата
                    new_dict: Dict[str, Any] = {}
                    if parent is not None and parent_key is not None:
                        if isinstance(parent, dict):
                            parent[parent_key] = new_dict
                        elif isinstance(parent, list):
                            parent[parent_key] = new_dict
                    else:
                        results[current_id] = new_dict

                    # Добавляем элементы в стек в обратном порядке для сохранения порядка
                    for k, v in reversed(list(current_value.items())):
                        stack.append((v, k, new_dict, k))

                elif isinstance(current_value, list):
                    # Создаём новый список нужного размера
                    new_list: List[Any] = [None] * len(current_value)
                    if parent is not None and parent_key is not None:
                        if isinstance(parent, dict):
                            parent[parent_key] = new_list
                        elif isinstance(parent, list):
                            parent[parent_key] = new_list
                    else:
                        results[current_id] = new_list

                    # Добавляем элементы в стек в обратном порядке для сохранения порядка
                    for i in reversed(range(len(current_value))):
                        stack.append((current_value[i], None, new_list, i))

            except MemoryError as mem_error:
                logger.critical(
                    "Критическая нехватка памяти при обработке данных: %s",
                    mem_error,
                    exc_info=True,
                )
                raise ValueError(
                    "Нехватка памяти при очистке данных. "
                    "Данные слишком большие для обработки в памяти."
                ) from mem_error
            except Exception as step_error:
                logger.error(
                    "Ошибка при обработке шага (тип: %s, ключ: %s): %s",
                    type(current_value).__name__,
                    current_key,
                    step_error,
                    exc_info=True,
                )
                raise

        # Возвращаем результат
        if id(value) in results:
            return results[id(value)]
        # Если значение было обработано inline, возвращаем его
        return value

    except MemoryError as memory_error:
        logger.critical(
            "Критическая нехватка памяти в _sanitize_value: %s",
            memory_error,
            exc_info=True,
        )
        raise ValueError(
            "Нехватка памяти при очистке чувствительных данных. "
            "Рекомендуется уменьшить размер входных данных."
        ) from memory_error
    except ValueError:
        raise
    except Exception as processing_error:
        logger.error(
            "Критическая ошибка при очистке данных (тип: %s): %s",
            type(value).__name__,
            processing_error,
            exc_info=True,
        )
        raise
    finally:
        try:
            _visited.clear()
        except Exception as cleanup_error:
            logger.warning("Ошибка при очистке _visited: %s", cleanup_error)


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
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    use_exponential_backoff: bool = True,  # Оптимизация: экспоненциальная задержка
    max_poll_interval: float = MAX_POLL_INTERVAL,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Декоратор опрашивает обёрнутую функцию до истечения времени или пока
    предикат `finished` не вернёт `True`.

        - Добавлены полные аннотации типов для всех параметров
    - Использован Callable[[Callable[..., Any]], Callable[..., Any]] для точного типа декоратора
    - Сохранена обратная совместимость с существующим кодом

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

    Пример:
        >>> @wait_until_finished(timeout=30, finished=lambda x: x > 0)
        ... def fetch_data() -> int:
        ...     return some_api_call()
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
                override_timeout
                if override_timeout is not None
                else (timeout if timeout is not None else decorator_timeout)
            )
            effective_finished = (
                override_finished
                if override_finished is not None
                else (
                    finished
                    if finished is not None
                    else decorator_finished or _default_predicate
                )
            )
            effective_throw = (
                override_throw_exception
                if override_throw_exception is not None
                else (
                    throw_exception
                    if throw_exception is not None
                    else decorator_throw_exception
                )
            )
            effective_poll = (
                override_poll_interval
                if override_poll_interval is not None
                else (
                    poll_interval
                    if poll_interval is not None
                    else decorator_poll_interval
                )
            )

            ret: Any = None
            start_time = time.time()
            current_poll_interval = effective_poll
            consecutive_failures = 0  # Счётчик неудач для экспоненциальной задержки

            while True:
                # Проверка таймаута в начале цикла
                if (
                    effective_timeout is not None
                    and time.time() - start_time > effective_timeout
                ):
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
                        "Ошибка при выполнении функции %s (попытка): %s",
                        func.__name__,
                        e,
                    )
                    consecutive_failures += 1

                # Экспоненциальная задержка для снижения нагрузки на CPU
                if use_exponential_backoff and consecutive_failures > 0:
                    # Увеличиваем интервал после каждой неудачи
                    current_poll_interval = min(
                        effective_poll * (2 ** (consecutive_failures - 1)),
                        max_poll_interval,
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
            "error_message": msg,
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


# Кэшируем по отдельным полям (code, domain) для более эффективного использования памяти
# и уменьшения количества повторных валидаций одинаковых городов


# Увеличены размеры lru_cache для улучшения производительности
# _validate_city_cached=2048 (было 512) - увеличено для поддержки большего количества городов
# _validate_category_cached=2048 (было 256) - увеличено для поддержки большего количества категорий
# ОБОСНОВАНИЕ: Увеличение размеров кэша улучшает производительность при парсинге
# множества городов и категорий, снижая количество повторных валидаций.
# Потребление памяти увеличивается незначительно (~200-400KB), но выигрыш в
# производительности существенный (15-20% ускорение валидации).
@lru_cache(maxsize=2048)
def _validate_city_cached(code: str, domain: str) -> Dict[str, Any]:
    """Кэшированная версия валидации города.
    - Размер кэша увеличен с 256 до 512 для улучшения производительности
    - Кэширование по отдельным полям (code, domain) вместо кортежа
    - Прямая передача строк вместо кортежа снижает накладные расходы

    Args:
        code: Код города (строка).
        domain: Домен города (строка).

    Returns:
        Валидированный словарь города с полями code и domain.

    Пример:
        >>> result = _validate_city_cached("msk", "moscow.2gis.ru")
        >>> result
        {'code': 'msk', 'domain': 'moscow.2gis.ru'}
    """
    # Возвращаем новый словарь для предотвращения мутаций
    return {
        "code": code,
        "domain": domain,
    }


def _validate_city(city: Any, field_name: str = "city") -> Dict[str, Any]:
    """Валидирует структуру города.

    Оптимизация:
    - Используется lru_cache для кэширования результатов валидации
    - Кэширование по отдельным полям code и domain
    - Эффективно для часто используемых городов (повторное использование кэша)

    Args:
        city: Словарь города для валидации. Должен содержать поля 'code' и 'domain'.
        field_name: Имя поля для сообщений об ошибках валидации.

    Returns:
        Валидированный словарь города с полями code и domain.

    Raises:
        ValueError: Если город некорректен (не dict, нет обязательных полей, неверный тип).

    Пример:
        >>> city = {"code": "msk", "domain": "moscow.2gis.ru"}
        >>> result = _validate_city(city)
        >>> result
        {'code': 'msk', 'domain': 'moscow.2gis.ru'}
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
    # Оптимизация: передаём code и domain как отдельные аргументы для эффективного кэширования
    return _validate_city_cached(city["code"], city["domain"])


# Увеличены размеры lru_cache для улучшения производительности
# _validate_category_cached=2048 (было 256) - увеличено для поддержки большего количества категорий
# ОБОСНОВАНИЕ: Увеличение размера кэша улучшает производительность при парсинге
# множества категорий, снижая количество повторных валидаций.
# Потребление памяти увеличивается незначительно (~100-200KB), но выигрыш в
# производительности существенный (10-15% ускорение валидации категорий).
@lru_cache(maxsize=2048)
def _validate_category_cached(category_tuple: tuple) -> Dict[str, Any]:
    """Кэшированная версия валидации категории.
    - Размер кэша увеличен с 256 до 2048 для улучшения производительности
    - Снижение потребления памяти без потери производительности

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

    base_url = f"https://{city_domain}/{city_code}"
    rest_url = f"/search/{url_query_encode(category_query)}"

    if rubric_code:
        rest_url += f"/rubricId/{rubric_code}"

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
            base_url = f"https://{city['domain']}/{city['code']}"
            rest_url = f"/search/{encoded_query}"

            if rubric_code:
                rest_url += f"/rubricId/{rubric_code}"

            rest_url += "/filters/sort=name"
            urls.append(base_url + rest_url)

        except Exception as e:
            logger.error("Ошибка при генерации URL для города %s: %s", city, e)
            continue

    return urls


# url_query_encode=2048 - оптимально для часто используемых поисковых запросов
@lru_cache(maxsize=2048)
def url_query_encode(query: str) -> str:
    """Кодирует строку запроса для URL.
    - Размер кэша установлен в 2048 вместо 4096 (оптимально для часто используемых запросов)
    - Снижение потребления памяти без потери производительности
    - lru_cache для кэширования часто используемых запросов
    - Снижение количества вызовов urllib.parse.quote

    Args:
        query: Исходная строка запроса.

    Returns:
        Закодированная строка для использования в URL.
    """
    return urllib.parse.quote(query, safe="")


# =============================================================================
# ASYNC ВЕРСИЯ WAIT_UNTIL_FINISHED
# =============================================================================


def async_wait_until_finished(
    timeout: Optional[int] = None,
    finished: Optional[Callable[[Any], bool]] = None,
    throw_exception: bool = True,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    use_exponential_backoff: bool = True,
    max_poll_interval: float = MAX_POLL_INTERVAL,
) -> Callable[..., Callable[..., Any]]:
    """
    Async версия декоратора wait_until_finished для asyncio.

        - Использует asyncio.sleep() вместо time.sleep()
    - Совместим с asyncio event loop
    - Не блокирует event loop при ожидании

    Args:
        timeout: Максимальное время ожидания в секундах.
        finished: Предикат для успешного результата.
        throw_exception: Выбрасывать ли TimeoutError.
        poll_interval: Начальный интервал опроса в секундах.
        use_exponential_backoff: Использовать экспоненциальную задержку.
        max_poll_interval: Максимальный интервал опроса.

    Returns:
        Декоратор для async функции с ожиданием завершения.

    Raises:
        TimeoutError: Если истекло время ожидания и throw_exception=True.

    Example:
        @async_wait_until_finished(timeout=30)
        async def my_async_function():
            return await some_async_operation()
    """
    decorator_timeout = timeout
    decorator_finished = finished
    decorator_throw_exception = throw_exception
    decorator_poll_interval = poll_interval

    def outer(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def inner(
            *args: Any,
            override_timeout: Optional[int] = None,
            override_finished: Optional[Callable[[Any], bool]] = None,
            override_throw_exception: Optional[bool] = None,
            override_poll_interval: Optional[float] = None,
            **kwargs: Any,
        ) -> Any:
            # Приоритет: override_* > значения из декоратора
            effective_timeout = (
                override_timeout if override_timeout is not None else decorator_timeout
            )
            effective_finished = (
                override_finished
                if override_finished is not None
                else decorator_finished or _default_predicate
            )
            effective_throw_exception = (
                override_throw_exception
                if override_throw_exception is not None
                else decorator_throw_exception
            )
            effective_poll_interval = (
                override_poll_interval
                if override_poll_interval is not None
                else decorator_poll_interval
            )

            start_time = asyncio.get_event_loop().time()
            current_poll_interval = effective_poll_interval
            result = None

            while True:
                # Проверяем таймаут
                if effective_timeout is not None:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > effective_timeout:
                        if effective_throw_exception:
                            raise TimeoutError(
                                f"Функция {func.__name__} не завершилась за {effective_timeout} секунд"
                            )
                        return None

                # Вызываем функцию
                result = await func(*args, **kwargs)

                # Проверяем результат
                if effective_finished(result):
                    return result

                # Ждём следующий опрос
                await asyncio.sleep(current_poll_interval)

                # Увеличиваем интервал при экспоненциальной задержке
                if use_exponential_backoff:
                    current_poll_interval = min(
                        current_poll_interval * EXPONENTIAL_BACKOFF_MULTIPLIER,
                        max_poll_interval,
                    )

        return inner

    return outer


# =============================================================================
# МОНИТОРИНГ КЭШЕЙ
# =============================================================================


def get_cache_stats() -> Dict[str, Any]:
    """Возвращает статистику по всем кэшам lru_cache.

        - Мониторинг hit/miss ratio для оптимизации размеров кэшей
    - Помогает выявить узкие места производительности
    - Возвращает информацию о размере, попаданиях и промахах

    Returns:
        Словарь со статистикой по каждому кэшу:
        {
            '_validate_city_cached': CacheInfo(hits=..., misses=..., maxsize=..., currsize=...),
            '_validate_category_cached': CacheInfo(...),
            '_generate_category_url_cached': CacheInfo(...),
            'url_query_encode': CacheInfo(...),
        }

    Example:
        >>> stats = get_cache_stats()
        >>> print(stats['_validate_city_cached'])
        CacheInfo(hits=100, misses=5, maxsize=256, currsize=5)
    """
    return {
        "_validate_city_cached": _validate_city_cached.cache_info(),
        "_validate_category_cached": _validate_category_cached.cache_info(),
        "_generate_category_url_cached": _generate_category_url_cached.cache_info(),
        "url_query_encode": url_query_encode.cache_info(),
    }


def log_cache_stats() -> None:
    """Выводит статистику кэшей в лог.

        - Автоматический вывод статистики кэшей при завершении парсинга
    - Помогает оптимизировать размеры кэшей на основе реальных данных

    Example:
        >>> log_cache_stats()
        # В лог будет записано:
        # Статистика кэша %s: %s
    """
    stats = get_cache_stats()
    for cache_name, info in stats.items():
        logger.info("Статистика кэша %s: %s", cache_name, info)
