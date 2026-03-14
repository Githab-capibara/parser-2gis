"""
Модуль совместимости с Pydantic v1 и v2.

Предоставляет единый интерфейс для работы с разными версиями Pydantic.
"""

from __future__ import annotations

import pydantic

# Определяем мажорную версию Pydantic
PYDANTIC_V2 = pydantic.VERSION.startswith("2.")


def get_model_dump(model: pydantic.BaseModel, **kwargs) -> dict:
    """
    Сериализует модель Pydantic в словарь.
    
    Args:
        model: Модель Pydantic.
        **kwargs: Дополнительные аргументы для model_dump (Pydantic v2).
    
    Returns:
        Словарь с данными модели.
    """
    if PYDANTIC_V2:
        # Pydantic v2 использует model_dump()
        return model.model_dump(**kwargs)  # type: ignore[attr-defined]
    else:
        # Pydantic v1 использует dict()
        return model.dict(**kwargs)


def get_model_fields_set(model: pydantic.BaseModel) -> set[str]:
    """
    Получает набор установленных полей модели.
    
    Args:
        model: Модель Pydantic.
    
    Returns:
        Набор имён установленных полей.
    """
    if PYDANTIC_V2:
        # Pydantic v2 использует model_fields_set
        return model.model_fields_set  # type: ignore[attr-defined]
    else:
        # Pydantic v1 использует __fields_set__
        return model.__fields_set__


def model_validate_json(json_str: str) -> type[pydantic.BaseModel]:
    """
    Создаёт модель из JSON строки.
    
    Args:
        json_str: JSON строка.
    
    Returns:
        Модель Pydantic.
    """
    if PYDANTIC_V2:
        # Pydantic v2 использует model_validate_json
        return pydantic.BaseModel.model_validate_json(json_str)  # type: ignore[attr-defined]
    else:
        # Pydantic v1 использует parse_raw
        return pydantic.BaseModel.parse_raw(json_str)
