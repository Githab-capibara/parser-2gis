"""
Модуль путей к ресурсам парсера.

Предоставляет функции для получения путей к данным, изображениям
и пользовательским директориям.
"""

from __future__ import annotations

import base64
import functools
import os
import pathlib

from .constants import FORBIDDEN_PATH_CHARS


def _is_relative_to(path: pathlib.Path, other: pathlib.Path) -> bool:
    """Проверяет, является ли путь относительным к другому пути.

    Универсальная реализация для совместимости с Python <3.9 и >=3.9.
    В Python 3.9+ используется встроенный метод is_relative_to().
    В Python <3.9 используется os.path.realpath() + проверка префикса.

    Args:
        path: Путь для проверки.
        other: Базовый путь.

    Returns:
        True если path находится внутри other, False иначе.
    """
    try:
        # Python 3.9+ - используем встроенный метод
        return path.is_relative_to(other)  # type: ignore[attr-defined]
    except AttributeError:
        # Python <3.9 - используем os.path.realpath + проверка префикса
        abs_path = os.path.realpath(str(path))
        abs_other = os.path.realpath(str(other))
        # Добавляем os.sep для предотвращения ложных совпадений
        # Например: /foo/bar и /foobar
        return abs_path == abs_other or abs_path.startswith(abs_other + os.sep)


def data_path() -> pathlib.Path:
    """Получает путь к данным пакета."""
    if "_MEIPASS2" in os.environ:
        here = os.environ["_MEIPASS2"]
    else:
        here = os.path.dirname(os.path.abspath(__file__))

    path = os.path.join(here, "data")
    return pathlib.Path(path)


def user_path(is_config: bool = True) -> pathlib.Path:
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


@functools.lru_cache()
def image_path(basename: str, ext: str | None = None) -> str:
    """Получает путь к изображению `basename`.`ext`.
    Расширение игнорируется, если `ext` установлен в `None`.

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
        raise ValueError("Имя файла не может быть пустым")

    # Проверка на запрещённые символы для предотвращения path traversal атак
    for forbidden in FORBIDDEN_PATH_CHARS:
        if forbidden in basename:
            raise ValueError(f"Недопустимое имя файла: {basename}")

    # Дополнительная проверка на специальные символы
    if any(c in basename for c in ["..", "/", "\\", "~", "$", "`", "|", ";", "&", ">", "<"]):
        raise ValueError(f"Недопустимое имя файла: {basename}")

    images_dir = data_path() / "images"

    # Проверка что images_dir существует
    if not images_dir.exists():
        raise FileNotFoundError(f"Директория изображений не найдена: {images_dir}")

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
                raise ValueError(f"Path traversal detected: {basename}")
        except (OSError, ValueError) as e:
            raise ValueError(f"Недопустимый путь к изображению: {e}") from e

        if resolved_img_path.exists():
            return str(resolved_img_path)
        raise FileNotFoundError(f"Изображение {basename}.{ext} не найдено")

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
                raise ValueError(f"Path traversal detected: {img_name}")

            return str(resolved_img_path)
    raise FileNotFoundError(f"Изображение {basename} не найдено")


@functools.lru_cache()
def image_data(basename: str, ext: str | None = None) -> bytes:
    """Получает данные изображения `basename`.`ext`.
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
    except (IOError, OSError):
        # Файл не может быть прочитан - ошибка логируется и пробрасывается дальше
        raise


@functools.lru_cache()
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
