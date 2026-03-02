from __future__ import annotations

import functools
import sys
import time
import warnings
from typing import Any, Callable

from pydantic import ValidationError

try:
    import PySimpleGUI
    del PySimpleGUI
    GUI_ENABLED = True
except ImportError as e:
    if e.name != 'PySimpleGUI':
        # GUI was installed, but failed to load
        # due to tkinter missing or other dependencies.
        warnings.warn('Failed to load GUI: %s' % e.msg)
    GUI_ENABLED = False


def running_linux() -> bool:
    """Determine if current OS is Linux-based."""
    return sys.platform.startswith('linux')


def running_windows() -> bool:
    """Determine if current OS is Windows."""
    return sys.platform.startswith('win')


def running_mac() -> bool:
    """Determine if current OS is MacOS."""
    return sys.platform.startswith('darwin')


def wait_until_finished(timeout: int | None = None,
                        finished: Callable[[Any], bool] | None = None,
                        throw_exception: bool = True,
                        poll_interval: float = 0.1) -> Callable[..., Callable[..., Any]]:
    """Декоратор опрашивает обёрнутую функцию до истечения времени или пока
    предикат `finished` не вернёт `True`.

    Args:
        timeout: Максимальное время ожидания.
        finished: Предикат для успешного результата обёрнутой функции.
        throw_exception: Выбрасывать ли `TimeoutError`.
        poll_interval: Интервал опроса результата обёрнутой функции.
    """
    def outer(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def inner(*args, timeout: int | None = timeout,
                  finished: Callable[[Any], bool] | None = finished,
                  throw_exception: bool = throw_exception,
                  poll_interval: float = poll_interval, **kwargs):
            # Перемещаем lambda в тело функции для избежания изменяемого аргумента по умолчанию
            if finished is None:
                finished = lambda x: bool(x)
            
            call_time = time.time()
            while True:
                ret = func(*args, **kwargs)
                if finished(ret):
                    return ret

                # Переименовываем внутренний параметр для избежания путаницы
                inner_timeout = timeout
                if inner_timeout is not None:
                    if time.time() - call_time > inner_timeout:
                        if throw_exception:
                            raise TimeoutError(func)
                        return ret

                time.sleep(poll_interval)
        return inner
    return outer


def report_from_validation_error(ex: ValidationError,
                                 d: dict | None = None) -> dict:
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
    """
    values = {}
    for error in ex.errors():
        msg = error['msg']
        loc = error['loc']
        attribute_path = '.'.join([str(location) for location in loc])

        if d:
            value = d
            for field in loc:
                if field == '__root__':
                    break
                if field in value:
                    value = value[field]
                else:
                    value = '<No value>'  # type: ignore
                    break

            values[attribute_path] = {
                'invalid_value': value,
                'error_message': msg,
            }
        else:
            values[attribute_path] = {
                'error_message': msg,
            }

    return values


def unwrap_dot_dict(d: dict) -> dict:
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
    """
    output: dict = {}
    for key, value in d.items():
        path = key.split('.')
        target = functools.reduce(lambda d, k: d.setdefault(k, {}), path[:-1], output)
        target[path[-1]] = value
    return output


def floor_to_hundreds(arg: int | float) -> int:
    """Округляет число вниз до ближайшей сотни."""
    return int(arg // 100 * 100)
