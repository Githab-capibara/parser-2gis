"""Информация о версии пакета parser-2gis.

Содержит константы с версией пакета и версией конфигурации.
Используется для отображения версии в CLI и логировании.

Пример использования:
    >>> from parser_2gis.version import VERSION, CONFIG_VERSION
    >>> print(f"Версия парсера: {VERSION}")
    Версия парсера: 2.1.12
    >>> print(f"Версия конфигурации: {CONFIG_VERSION}")
    Версия конфигурации: 0.1
"""

from typing import Literal, overload

VERSION: str = "2.1.12"
CONFIG_VERSION: str = "0.1"

__all__ = ["CONFIG_VERSION", "VERSION"]


@overload
def __getattr__(name: Literal["version"]) -> str: ...
@overload
def __getattr__(name: Literal["config_version"]) -> str: ...


def __getattr__(name: str) -> str:
    """Ленивые алиасы для обратной совместимости.

    Args:
        name: Имя атрибута.

    Returns:
        Значение алиаса.

    Raises:
        AttributeError: Если атрибут не найден.

    """
    if name == "version":
        return VERSION
    if name == "config_version":
        return CONFIG_VERSION
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
