"""
Валидаторы для форм TUI.
"""

import pathlib
from typing import Optional, Tuple

def validate_number(
    value: str,
    min_val: Optional[int] = None,
    max_val: Optional[int] = None,
    allow_empty: bool = False,
) -> Tuple[bool, str]:
    """
    Проверяет, является ли строка корректным числом в заданном диапазоне.

    Args:
        value: Строка для проверки
        min_val: Минимальное значение (None = без ограничений)
        max_val: Максимальное значение (None = без ограничений)
        allow_empty: Разрешить пустую строку

    Returns:
        Кортеж (успешно, сообщение об ошибке)
    """
    if not value:
        if allow_empty:
            return True, ""
        return False, "Поле не может быть пустым"

    try:
        num = int(value)
    except ValueError:
        return False, "Введите целое число"

    if min_val is not None and num < min_val:
        return False, f"Минимальное значение: {min_val}"

    if max_val is not None and num > max_val:
        return False, f"Максимальное значение: {max_val}"

    return True, ""

def validate_path(
    value: str,
    must_exist: bool = False,
    file_type: str = "file",
) -> Tuple[bool, str]:
    """
    Проверяет корректность пути к файлу или директории.

    Args:
        value: Путь для проверки
        must_exist: Должен ли путь существовать
        file_type: Тип пути ("file" или "dir")

    Returns:
        Кортеж (успешно, сообщение об ошибке)
    """
    if not value:
        return False, "Путь не может быть пустым"

    path = pathlib.Path(value)

    if must_exist and not path.exists():
        return False, f"Путь не существует: {value}"

    if file_type == "file" and path.exists() and not path.is_file():
        return False, "Ожидается файл, а не директория"

    if file_type == "dir" and path.exists() and not path.is_dir():
        return False, "Ожидается директория, а не файл"

    # Проверка на допустимые символы
    try:
        path.resolve()
    except (OSError, RuntimeError):
        return False, "Недопустимые символы в пути"

    return True, ""
