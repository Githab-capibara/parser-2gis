"""Модуль совместимости с Pydantic v2.

Предоставляет упрощённый интерфейс для работы с Pydantic v2.
Поддержка Pydantic v1 удалена.

Пример использования:
    >>> from pydantic import BaseModel
    >>> from parser_2gis.pydantic_compat import get_model_dump, get_model_fields_set
    >>> class MyModel(BaseModel):
    ...     name: str
    >>> model = MyModel(name="test")
    >>> dump = get_model_dump(model)
    >>> print(dump)
    {'name': 'test'}
"""

from __future__ import annotations

from typing import Any

import pydantic
from typing import TypeAlias

# TypeAlias для сложных типов
PydanticModel: TypeAlias = pydantic.BaseModel
PydanticModelDict: TypeAlias = dict[str, Any]


def get_model_dump(model: pydantic.BaseModel, **kwargs: Any) -> PydanticModelDict:
    """Сериализует модель Pydantic в словарь.

    Использует метод model_dump() из Pydantic v2.

    Args:
        model: Модель Pydantic для сериализации.
        **kwargs: Дополнительные аргументы для model_dump().

    Returns:
        Словарь с данными модели.

    Example:
        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     name: str
        ...     age: int
        >>> user = User(name="Alice", age=30)
        >>> get_model_dump(user)
        {'name': 'Alice', 'age': 30}

    """
    return model.model_dump(**kwargs)  # type: ignore[attr-defined]


def get_model_fields_set(model: pydantic.BaseModel) -> set[str]:
    """Получает набор установленных полей модели.

    Использует атрибут model_fields_set из Pydantic v2.

    Args:
        model: Модель Pydantic.

    Returns:
        Набор имён установленных полей.

    Example:
        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     name: str
        ...     age: int
        >>> user = User(name="Alice", age=30)
        >>> get_model_fields_set(user)
        {'name', 'age'}

    """
    return model.model_fields_set  # type: ignore[attr-defined]


def model_validate_json(json_str: str) -> pydantic.BaseModel:
    """Создаёт модель из JSON строки.

    Использует метод model_validate_json() из Pydantic v2.

    Args:
        json_str: JSON строка для парсинга.

    Returns:
        Модель Pydantic.

    Example:
        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     name: str
        ...     age: int
        >>> model_validate_json('{"name": "Alice", "age": 30}')
        User(name='Alice', age=30)

    """
    return pydantic.BaseModel.model_validate_json(json_str)  # type: ignore[attr-defined]


def model_validate_json_class(cls: type[pydantic.BaseModel], json_str: str) -> pydantic.BaseModel:
    """Создаёт модель из JSON строки для указанного класса.

    Использует метод model_validate_json() из Pydantic v2.

    Args:
        cls: Класс модели Pydantic.
        json_str: JSON строка для парсинга.

    Returns:
        Экземпляр модели Pydantic.

    Example:
        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     name: str
        ...     age: int
        >>> model_validate_json_class(User, '{"name": "Alice", "age": 30}')
        User(name='Alice', age=30)

    """
    return cls.model_validate_json(json_str)  # type: ignore[attr-defined]
