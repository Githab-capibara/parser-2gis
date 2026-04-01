"""Форматировщик справки для аргументов командной строки.

Модуль предоставляет класс ArgumentHelpFormatter для форматирования
справки argparse с добавлением значений по умолчанию.
"""

from __future__ import annotations

import argparse
from typing import Any

from parser_2gis.config import Configuration
from parser_2gis.pydantic_compat import get_model_dump


class ArgumentHelpFormatter(argparse.HelpFormatter):
    """Форматировщик справки, добавляющий значения по умолчанию к описанию аргументов.

    Этот класс расширяет стандартный HelpFormatter для автоматического
    добавления значений по умолчанию из Configuration к каждому аргументу.

    Example:
        >>> parser = argparse.ArgumentParser(formatter_class=ArgumentHelpFormatter)
        >>> parser.print_help()

    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Инициализирует форматировщик с конфигурацией по умолчанию.

        Args:
            *args: Позиционные аргументы для HelpFormatter.
            **kwargs: Именованные аргументы для HelpFormatter.

        """
        super().__init__(*args, **kwargs)
        self._default_config = get_model_dump(Configuration())

    def _get_default_value(self, dest: str) -> Any:
        """Получает значение по умолчанию для аргумента.

        Args:
            dest: Имя атрибута (например, "chrome.headless").

        Returns:
            Значение по умолчанию или argparse.SUPPRESS если не найдено.

        """
        if dest == "version":
            return argparse.SUPPRESS

        fields = dest.split(".")
        value: Any = self._default_config
        try:
            for field in fields:
                value = value[field]
            return value
        except KeyError:
            return argparse.SUPPRESS

    def _get_help_string(self, action: argparse.Action) -> str | None:
        """Получает строку справки с добавлением значения по умолчанию.

        Args:
            action: Действие argparse.

        Returns:
            Строка справки с значением по умолчанию или None.

        """
        help_string = action.help
        if help_string:
            default_value = self._get_default_value(action.dest)
            if default_value != argparse.SUPPRESS:
                if isinstance(default_value, bool):
                    default_value = "yes" if default_value else "no"
                help_string += f" (по умолчанию: {default_value})"
        return help_string


def patch_argparse_translations() -> None:
    """Патчит gettext в argparse для перевода строк на русский язык.

    Заменяет стандартные сообщения argparse на русские аналоги.
    """
    custom_translations = {
        "usage: ": "Использование: ",
        "one of the arguments %s is required": "один из аргументов %s обязателен",
        "unrecognized arguments: %s": "нераспознанные аргументы: %s",
        "the following arguments are required: %s": "следующие аргументы обязательны: %s",
        "%(prog)s: error: %(message)s\n": "%(prog)s: ошибка: %(message)s\n",
        "invalid choice: %(value)r (choose from %(choices)s)": (
            "неверная опция: %(value)r (выберите одну из %(choices)s)"
        ),
    }

    orig_gettext = argparse._  # type: ignore[attr-defined]

    def gettext(message: str) -> str:
        if message in custom_translations:
            return custom_translations[message]
        return orig_gettext(message)

    argparse._ = gettext  # type: ignore[attr-defined]

    # Заменяем хардкодную строку `argument` в классе ArgumentError
    # Этот баг был исправлен только 6 мая 2022 https://github.com/python/cpython/pull/17169
    def argument_error__str__(self: argparse.ArgumentError) -> str:
        if self.argument_name is None:
            format_str = "%(message)s"
        else:
            format_str = "аргумент %(argument_name)s: %(message)s"
        return format_str % dict(message=self.message, argument_name=self.argument_name)

    argparse.ArgumentError.__str__ = argument_error__str__  # type: ignore


__all__ = ["ArgumentHelpFormatter", "format_config_summary", "patch_argparse_translations"]


def format_config_summary(
    config: Configuration, args: argparse.Namespace | None = None
) -> dict[str, Any]:
    """Форматирует конфигурацию для логирования.

    Args:
        config: Конфигурация приложения.
        args: Аргументы командной строки (для получения формата).

    Returns:
        Словарь с отформатированной конфигурацией.

    """
    # Получаем формат из args, т.к. в config.writer нет атрибута format
    format_value: str = getattr(args, "format", "csv") if args else "csv"

    return {
        "chrome": {
            "Headless": "Да" if config.chrome.headless else "Нет",
            "Без изображений": "Да" if config.chrome.disable_images else "Нет",
            "Максимизирован": "Да" if config.chrome.start_maximized else "Нет",
        },
        "parser": {
            "Макс. записей": str(config.parser.max_records),
            "Задержка (мс)": str(config.parser.delay_between_clicks),
            "GC включен": "Да" if config.parser.use_gc else "Нет",
        },
        "writer": {
            "Формат": format_value.upper() if format_value else "CSV",
            "Кодировка": config.writer.encoding,
            "Удалить дубликаты": "Да" if config.writer.csv.remove_duplicates else "Нет",
        },
    }
