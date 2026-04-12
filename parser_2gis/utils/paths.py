"""Модуль путей к ресурсам парсера parser-2gis.

Предоставляет функции для получения путей к данным, изображениям
и пользовательским директориям:
- resources_path: путь к ресурсам пакета
- data_path: путь к данным (устаревшая, используйте resources_path)
- user_path: пользовательский путь для конфигурации/данных
- image_path: путь к изображению
- image_data: данные изображения в base64
- cache_path: путь к директории кэша
- _is_relative_to: проверка относительности пути

Пример использования:
    >>> from parser_2gis.utils.paths import resources_path, image_path
    >>> res_path = resources_path()
    >>> img = image_path("logo", "png")
"""

from __future__ import annotations

import base64
import os
import pathlib
from functools import lru_cache

from parser_2gis.constants import FORBIDDEN_PATH_CHARS


def _is_relative_to(path: pathlib.Path, other: pathlib.Path) -> bool:
    """Проверяет, является ли путь относительным к другому пути.

    Универсальная реализация для обеспечения совместимости с Python <3.9 и >=3.9.

    Совместимость:
        - Python 3.9+: Используется встроенный метод pathlib.Path.is_relative_to()
        - Python <3.9: Используется os.path.realpath() + проверка префикса пути

    Args:
        path: Путь для проверки.
        other: Базовый путь для сравнения.

    Returns:
        True если path находится внутри other или совпадает с ним, False иначе.

    Note:
        Функция обрабатывает оба случая: когда path совпадает с other
        и когда path является вложенным путём внутри other.

    Example:
        >>> from pathlib import Path
        >>> _is_relative_to(Path("/foo/bar"), Path("/foo"))
        True
        >>> _is_relative_to(Path("/foo"), Path("/foo"))
        True
        >>> _is_relative_to(Path("/bar"), Path("/foo"))
        False

    """
    try:
        # Python 3.9+ - используем встроенный метод
        return path.is_relative_to(other)
    except AttributeError:
        # Python <3.9 - используем os.path.realpath + проверка префикса
        abs_path = os.path.realpath(str(path))
        abs_other = os.path.realpath(str(other))
        # Добавляем os.sep для предотвращения ложных совпадений
        # Например: /foo/bar и /foobar
        return abs_path == abs_other or abs_path.startswith(abs_other + os.sep)


def resources_path() -> pathlib.Path:
    """Получает путь к ресурсам пакета.

    Note:
        Эта функция заменяет устаревшую data_path().
        Ресурсы перемещены в parser_2gis/resources/ для устранения дублирования.

    """
    if "_MEIPASS2" in os.environ:
        here = os.environ["_MEIPASS2"]
    else:
        # Получаем путь к директории parser_2gis (родитель utils/)
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    path = os.path.join(here, "resources")
    return pathlib.Path(path)


def data_path() -> pathlib.Path:
    """Получает путь к данным пакета.

    Deprecated:
        Используйте resources_path() вместо data_path().
        Эта функция оставлена для обратной совместимости.
    """
    return resources_path()


def user_path(*, is_config: bool = True) -> pathlib.Path:
    """Получает пользовательский путь для Linux Ubuntu.

    Примечание:
        Расположение пути для Linux Ubuntu:
        * ~/.config/parser-2gis (для конфигурации)
        * ~/.local/share/parser-2gis (для данных)

    Args:
        is_config: Если True, возвращает путь к конфигурации, иначе к данным.

    Returns:
        Путь к пользовательской директории.

    """
    if is_config:
        path = os.getenv("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    else:
        path = os.getenv("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

    path = os.path.join(path, "parser-2gis")
    return pathlib.Path(path)


@lru_cache(maxsize=256)
def image_path(basename: str, ext: str | None = None) -> str:
    """Получает путь к изображению.

    Расширение игнорируется, если `ext` установлен в `None`.

    Кэширование:
        Использует lru_cache(maxsize=256) для кэширования путей к часто
        используемым изображениям, что снижает количество обращений к файловой системе.

    Args:
        basename: Базовое имя изображения.
        ext: Расширение изображения (опционально).

    Returns:
        Абсолютный путь к изображению.

    Raises:
        ValueError: Если basename содержит недопустимые символы или path traversal.
        FileNotFoundError: Если изображение не найдено.

    """
    # Проверка на пустое имя
    if not basename or basename.strip() == "":
        msg = "Имя файла не может быть пустым"
        raise ValueError(msg)

    # Проверка на запрещённые символы для предотвращения path traversal атак
    for forbidden in FORBIDDEN_PATH_CHARS:
        if forbidden in basename:
            msg = f"Недопустимое имя файла: {basename}"
            raise ValueError(msg)

    # Дополнительная проверка на специальные символы
    if any(c in basename for c in ["..", "/", "\\", "~", "$", "`", "|", ";", "&", ">", "<"]):
        msg = f"Недопустимое имя файла: {basename}"
        raise ValueError(msg)

    images_dir = data_path() / "images"

    # Проверка что images_dir существует
    if not images_dir.exists():
        msg = f"Директория изображений не найдена: {images_dir}"
        raise FileNotFoundError(msg)

    # Оптимизированный поиск: сразу формируем ожидаемое имя файла
    if ext is not None:
        img_name = f"{basename}.{ext}"
        img_path = images_dir / img_name

        # Используем resolve() для получения абсолютного канонического пути
        try:
            resolved_img_path = img_path.resolve(strict=False)
            resolved_images_dir = images_dir.resolve()

            # Проверяем что путь находится внутри директории изображений
            # ИСПРАВЛЕНИЕ: Используем универсальную функцию для совместимости с Python <3.9
            if not _is_relative_to(resolved_img_path, resolved_images_dir):
                msg = f"Path traversal detected: {basename}"
                raise ValueError(msg)
        except (OSError, ValueError) as e:
            msg = f"Недопустимый путь к изображению: {e}"
            raise ValueError(msg) from e

        if resolved_img_path.exists():
            return str(resolved_img_path)
        msg = f"Изображение {basename}.{ext} не найдено"
        raise FileNotFoundError(msg)

    # Если расширение не указано, ищем любой файл с таким basename
    for img_name in os.listdir(images_dir):
        img_basename, _ = os.path.splitext(img_name)
        if img_basename == basename:
            img_path = images_dir / img_name
            resolved_img_path = img_path.resolve()
            resolved_images_dir = images_dir.resolve()

            # Проверяем что путь находится внутри директории изображений
            # ИСПРАВЛЕНИЕ: Используем универсальную функцию для совместимости с Python <3.9
            if not _is_relative_to(resolved_img_path, resolved_images_dir):
                msg = f"Path traversal detected: {img_name}"
                raise ValueError(msg)

            return str(resolved_img_path)
    msg = f"Изображение {basename} не найдено"
    raise FileNotFoundError(msg)


@lru_cache
def image_data(basename: str, ext: str | None = None) -> bytes:
    """Получает данные изображения.

    Расширение игнорируется, если `ext` установлен в `None`.

    Args:
        basename: Базовое имя изображения.
        ext: Расширение изображения (опционально).

    Returns:
        Данные изображения в кодировке base64.

    Raises:
        FileNotFoundError: Если изображение не найдено.
        IOError: Если файл не может быть прочитан.

    """
    img_path = image_path(basename, ext)
    try:
        with open(img_path, "rb") as f_img:
            return base64.b64encode(f_img.read())
    except OSError:
        # Файл не может быть прочитан - ошибка логируется и пробрасывается дальше
        raise


@lru_cache
def cache_path() -> pathlib.Path:
    """Получает путь к директории кэша для Linux Ubuntu.

    Примечание:
        Расположение пути для Linux Ubuntu:
        * ~/.cache/parser-2gis (для кэша)

    Returns:
        Путь к директории кэша.

    """
    path = os.getenv("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    path = os.path.join(path, "parser-2gis")
    return pathlib.Path(path)
