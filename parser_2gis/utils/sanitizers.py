"""Модуль санитаризации данных для parser-2gis.

Содержит функции для очистки чувствительных данных из структур:
- _is_sensitive_key: проверка ключа на чувствительность
- _check_value_type_and_sensitivity: проверка типа и чувствительности
- _sanitize_value: основная функция санитаризации

Пример использования:
    >>> from parser_2gis.utils.sanitizers import _sanitize_value
    >>> data = {"password": "secret", "name": "test"}
    >>> sanitized = _sanitize_value(data)
    >>> sanitized
    {'password': '<REDACTED>', 'name': 'test'}
"""

from __future__ import annotations

import logging
import re
from functools import cache
from typing import Any

from parser_2gis.constants import MAX_COLLECTION_SIZE, MAX_DATA_DEPTH, MAX_DATA_SIZE

# =============================================================================
# ЛОГГЕР
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# ПРОВЕРКА ЧУВСТВИТЕЛЬНЫХ КЛЮЧЕЙ
# =============================================================================

# Чувствительные ключи сгруппированы по категориям для лучшей организации
# и поддержки списка

# Пароли и аутентификация
_SENSITIVE_KEYS_PASSWORDS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "root_password",
        "admin_password",
        "db_password",
        "database_password",
    },
)

# Токены доступа и сессии
_SENSITIVE_KEYS_TOKENS: frozenset[str] = frozenset(
    {
        "token",
        "api_key",
        "apikey",
        "api-key",
        "access_token",
        "refresh_token",
        "session_id",
        "session_token",
        "auth_token",
        "bearer_token",
        "accesskey",
        "access-key",
        "secret_token",
    },
)

# Секретные ключи и криптография
_SENSITIVE_KEYS_SECRETS: frozenset[str] = frozenset(
    {
        "secret",
        "secret_key",
        "secretkey",
        "api_secret",
        "apisecret",
        "api-secret",
        "private_key",
        "privatekey",
        "private-key",
        "signing_key",
        "encryption_key",
        "master_key",
        "client_secret",
    },
)

# Аутентификация и авторизация
_SENSITIVE_KEYS_AUTH: frozenset[str] = frozenset(
    {"auth", "authorization", "credential", "bearer", "jwt", "oauth", "oauth_token"},
)

# Ключи доступа к сервисам
_SENSITIVE_KEYS_SERVICE_KEYS: frozenset[str] = frozenset(
    {
        "client_id",
        "github_token",
        "gitlab_token",
        "ssh_key",
        "sshkey",
        "ssh-private-key",
        "gpg_key",
        "pgp_key",
    },
)

# Сертификаты и SSL
_SENSITIVE_KEYS_CERTIFICATES: frozenset[str] = frozenset(
    {"certificate", "cert_key", "ssl_key", "tls_key"},
)

# Подключения к базам данных
_SENSITIVE_KEYS_DATABASE: frozenset[str] = frozenset({"connection_string", "conn_string"})

# Объединённый набор всех чувствительных ключей
# БЕЗОПАСНОСТЬ: Расширенный список для предотвращения утечки чувствительных данных
_SENSITIVE_KEYS: frozenset[str] = (
    _SENSITIVE_KEYS_PASSWORDS
    | _SENSITIVE_KEYS_TOKENS
    | _SENSITIVE_KEYS_SECRETS
    | _SENSITIVE_KEYS_AUTH
    | _SENSITIVE_KEYS_SERVICE_KEYS
    | _SENSITIVE_KEYS_CERTIFICATES
    | _SENSITIVE_KEYS_DATABASE
)

# Компилированный regex паттерн для проверки чувствительных ключей
_SENSITIVE_KEY_PATTERN = re.compile(
    r"(^|[_\-])(pass|secret|token|key|auth|cred|bearer|jwt|oauth|"
    r"sign|encrypt|master|admin|db|database|conn)([_\-]|$)",
    re.IGNORECASE,
)


@cache
def _is_sensitive_key(key: str) -> bool:
    """Проверяет, является ли ключ чувствительным.

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


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def _check_value_type_and_sensitivity(
    current_value: Any,
    current_key: str | None,
    parent: Any | None,
    parent_key: Any | None,
    results: dict[int, Any],
) -> tuple[bool, Any]:
    """Проверяет тип значения и обрабатывает простые случаи.

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
        result = "<REDACTED>" if current_key and _is_sensitive_key(current_key) else current_value
        if parent is not None and parent_key is not None:
            if isinstance(parent, (dict, list)):
                parent[parent_key] = result
        else:
            results[id(current_value)] = result
        return True, result

    return False, None


# =============================================================================
# ОСНОВНАЯ ФУНКЦИЯ САНИТАРИЗАЦИИ
# =============================================================================


def _sanitize_value(value: Any, key: str | None = None) -> Any:
    """Очищает чувствительные данные из значения.

    - Переписано на итеративный подход с явным стеком вместо рекурсии
    - Предотвращает RecursionError при обработке глубоко вложенных структур
    - Добавлена проверка максимального размера данных перед обработкой (MAX_DATA_SIZE = 10MB)
    - Добавлена проверка максимальной глубины вложенности (MAX_DATA_DEPTH = 100)
    - Добавлена проверка максимального размера коллекций (MAX_COLLECTION_SIZE = 100,000)
    - Выбрасывает ValueError с понятным сообщением при превышении лимитов
    - Обработка MemoryError добавлена во все критические секции

    Args:
        value: Значение для очистки.
        key: Имя ключа (опционально).

    Returns:
        Очищенное значение или '<REDACTED>' для чувствительных данных.

    Raises:
        ValueError: Если размер данных превышает MAX_DATA_SIZE или глубина превышает MAX_DATA_DEPTH.
        MemoryError: При критической нехватке памяти.

    """
    # _visited теперь локальная переменная, а не параметр функции
    _visited: set = set()

    # Проверка максимального размера данных перед обработкой
    # Ограничиваем размер repr() для предотвращения переполнения памяти
    try:
        # P0-8: Ограничиваем размер объекта перед вызовом repr для защиты от MemoryError
        # Для коллекций проверяем размер до вызова repr
        if isinstance(value, (dict, list, set, tuple)) and len(value) > MAX_COLLECTION_SIZE:
            logger.error(
                "Размер коллекции превышает максимальный лимит: %d элементов (максимум: %d)",
                len(value),
                MAX_COLLECTION_SIZE,
            )
            raise ValueError(
                "Размер данных слишком большой для обработки. Это может быть попытка DoS атаки.",
            )
        # Оптимизация: используем str() вместо repr() для меньшего потребления памяти
        # str() не создаёт полную репрезентацию объекта, а только строковое представление
        value_str = str(value)
        if len(value_str) > MAX_DATA_SIZE:
            logger.error(
                "Размер str() превышает максимальный лимит: %d символов (максимум: %d)",
                len(value_str),
                MAX_DATA_SIZE,
            )
            raise ValueError(
                "Размер данных слишком большой для обработки. Это может быть попытка DoS атаки.",
            )
    except MemoryError as size_check_error:
        logger.critical(
            "Нехватка памяти при проверке размера данных: %s", size_check_error, exc_info=True,
        )
        raise ValueError(
            "Нехватка памяти при проверке размера данных. Данные слишком большие для обработки.",
        ) from size_check_error

    try:
        # Используем явный стек для итеративной обработки вместо рекурсии
        # Формат: (значение, ключ, родитель, ключ_в_родителе, глубина)
        # Добавлена глубина для контроля вложенности
        stack: list[tuple] = [(value, key, None, None, 0)]

        # Словарь для хранения результатов обработки
        results: dict[int, Any] = {}

        # Счётчик обработанных элементов для защиты от чрезмерной обработки
        processed_count = 0

        while stack:
            try:
                current_value, current_key, parent, parent_key, current_depth = stack.pop()
                current_id = id(current_value)

                # Проверка максимальной глубины вложенности
                if current_depth > MAX_DATA_DEPTH:
                    logger.error(
                        "Глубина вложенности превышает максимальную: %d (максимум: %d)",
                        current_depth,
                        MAX_DATA_DEPTH,
                    )
                    raise ValueError(
                        f"Глубина вложенности данных ({current_depth}) превышает максимальную "
                        f"({MAX_DATA_DEPTH}). Это может указывать на циклические ссылки или атаку.",
                    )

                # Проверка количества обработанных элементов
                processed_count += 1
                if processed_count > MAX_COLLECTION_SIZE:
                    logger.error(
                        "Количество обработанных элементов превышает максимальное: %d (максимум: %d)",
                        processed_count,
                        MAX_COLLECTION_SIZE,
                    )
                    raise ValueError(
                        f"Количество обработанных элементов ({processed_count}) превышает "
                        f"максимальное ({MAX_COLLECTION_SIZE}). Это может указывать на атаку.",
                    )

                # Используем выделенную функцию для проверки типа и чувствительности
                handled, _ = _check_value_type_and_sensitivity(
                    current_value, current_key, parent, parent_key, results,
                )
                if handled:
                    continue

                # Проверяем на циклические ссылки
                if current_id in results:
                    result = results[current_id]
                    if parent is not None and parent_key is not None and isinstance(parent, (dict, list)):
                        parent[parent_key] = result
                    continue

                # Проверяем на циклические ссылки для изменяемых типов
                if isinstance(current_value, (dict, list)) and current_id in _visited:
                    result = "<REDACTED>"
                    if parent is not None and parent_key is not None:
                        if isinstance(parent, (dict, list)):
                            parent[parent_key] = result
                    else:
                        results[current_id] = result
                    continue

                if isinstance(current_value, (dict, list)):
                    _visited.add(current_id)

                # Чувствительные ключи обрабатываем сразу
                if current_key and _is_sensitive_key(current_key):
                    logger.warning(
                        "Обнаружен чувствительный ключ '%s' — данные будут частично обработаны "
                        "и заменены на '<REDACTED>'",
                        current_key,
                    )
                    result = "<REDACTED>"
                    if parent is not None and parent_key is not None:
                        if isinstance(parent, (dict, list)):
                            parent[parent_key] = result
                    else:
                        results[current_id] = result
                    continue

                if isinstance(current_value, dict):
                    # Проверка размера словаря
                    if len(current_value) > MAX_COLLECTION_SIZE:
                        logger.error(
                            "Размер словаря превышает максимальный: %d (максимум: %d)",
                            len(current_value),
                            MAX_COLLECTION_SIZE,
                        )
                        raise ValueError(
                            f"Размер словаря ({len(current_value)}) превышает максимальный "
                            f"({MAX_COLLECTION_SIZE}).",
                        )

                    # Создаём новый словарь для результата
                    new_dict: dict[str, Any] = {}
                    if parent is not None and parent_key is not None:
                        if isinstance(parent, (dict, list)):
                            parent[parent_key] = new_dict
                    else:
                        results[current_id] = new_dict

                    # Add items to stack in reverse order to preserve order
                    # Increment depth by 1
                    next_depth = current_depth + 1
                    for k, v in reversed(
                        current_value.items(),
                    ):  # FIX #18: Inefficient list comprehension
                        stack.append((v, k, new_dict, k, next_depth))

                elif isinstance(current_value, list):
                    # Проверка размера списка
                    if len(current_value) > MAX_COLLECTION_SIZE:
                        logger.error(
                            "Размер списка превышает максимальный: %d (максимум: %d)",
                            len(current_value),
                            MAX_COLLECTION_SIZE,
                        )
                        raise ValueError(
                            f"Размер списка ({len(current_value)}) превышает максимальный "
                            f"({MAX_COLLECTION_SIZE}).",
                        )

                    # Создаём новый список нужного размера
                    new_list: list[Any] = [None] * len(current_value)
                    if parent is not None and parent_key is not None:
                        if isinstance(parent, (dict, list)):
                            parent[parent_key] = new_list
                    else:
                        results[current_id] = new_list

                    # Добавляем элементы в стек в обратном порядке для сохранения порядка
                    # Увеличиваем глубину на 1
                    next_depth = current_depth + 1
                    for i in reversed(range(len(current_value))):
                        stack.append((current_value[i], None, new_list, i, next_depth))

            except MemoryError as mem_error:
                logger.critical(
                    "Критическая нехватка памяти при обработке данных: %s", mem_error, exc_info=True,
                )
                raise ValueError(
                    "Нехватка памяти при очистке данных. "
                    "Данные слишком большие для обработки в памяти.",
                ) from mem_error
            except ValueError:
                # Пробрасываем ValueError без изменений
                raise
            except (OSError, RuntimeError) as step_error:
                logger.error(
                    "Ошибка при обработке шага (тип: %s, ключ: %s, глубина: %s): %s",
                    type(current_value).__name__,
                    current_key,
                    current_depth,
                    step_error,
                    exc_info=True,
                )
                raise

        # Возвращаем результат
        if id(value) in results:
            result = results[id(value)]
            # ISSUE-003-#16: Очищаем results после обработки для освобождения памяти
            results.clear()
            return result
        # Если значение было обработано inline, возвращаем его
        return value

    except MemoryError as memory_error:
        logger.critical(
            "Критическая нехватка памяти в _sanitize_value: %s", memory_error, exc_info=True,
        )
        raise ValueError(
            "Нехватка памяти при очистке чувствительных данных. "
            "Рекомендуется уменьшить размер входных данных.",
        ) from memory_error
    except ValueError:
        # Пробрасываем ValueError без изменений
        raise
    except (OSError, RuntimeError) as processing_error:
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
        except (OSError, RuntimeError) as cleanup_error:
            logger.warning("Ошибка при очистке _visited: %s", cleanup_error)
        except MemoryError as mem_cleanup_error:
            logger.critical("Нехватка памяти при очистке _visited: %s", mem_cleanup_error)
        # Очищаем стек при MemoryError для освобождения памяти
        try:
            stack.clear()
        except (NameError, OSError, RuntimeError) as cleanup_error:
            logger.debug("Ошибка при очистке стека (игнорируется): %s", cleanup_error)
        except MemoryError as mem_cleanup_error:
            logger.critical("Нехватка памяти при очистке стека: %s", mem_cleanup_error)


# =============================================================================
# ЭКСПОРТ
# =============================================================================

# Все функции в модуле являются внутренними (начинаются с `_`),
# поэтому публичный API отсутствует. Модуль предназначен для импорта
# конкретных функций через `from parser_2gis.utils.sanitizers import _sanitize_value`.
__all__: list[str] = []
