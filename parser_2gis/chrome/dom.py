from __future__ import annotations

from typing import Callable

from pydantic import BaseModel, Field

try:
    from pydantic import field_validator  # type: ignore[attr-defined]

    PYDANTIC_V2 = True
except ImportError:
    from pydantic import validator

    PYDANTIC_V2 = False


class DOMNode(BaseModel):
    """DOM узел.

    Атрибуты:
        id: Идентификатор узла.
        backend_id: BackendNodeId узла.
        type: Тип узла.
        name: Имя узла.
        local_name: Локальное имя узла.
        value: Значение узла.
        children: Дочерние узлы.
        attributes: Атрибуты узла.
    """

    id: int = Field(..., alias="nodeId")
    backend_id: int = Field(..., alias="backendNodeId")
    type: int = Field(..., alias="nodeType")
    name: str = Field(..., alias="nodeName")
    local_name: str = Field(..., alias="localName")
    value: str = Field(..., alias="nodeValue")
    children: list["DOMNode"] = []
    attributes: dict[str, str] = {}

    @staticmethod
    def _validate_attributes(attributes_list: list[str]) -> dict[str, str]:
        """Валидирует список атрибутов, преобразуя его в словарь.

        Args:
            attributes_list: Список атрибутов в формате [name1, value1, name2, value2, ...].

        Returns:
            Словарь атрибутов {name1: value1, name2: value2, ...}.

        Raises:
            ValueError: Если список содержит нечётное количество элементов.
        """
        attributes = {}
        attributes_list_count = len(attributes_list)
        if attributes_list_count % 2 != 0:
            raise ValueError(
                "Список атрибутов должен содержать чётное количество элементов"
            )
        for name_idx in range(0, attributes_list_count, 2):
            attributes[attributes_list[name_idx]] = attributes_list[name_idx + 1]
        return attributes

    if PYDANTIC_V2:

        @field_validator("attributes", mode="before")
        @classmethod
        def validate_attributes(cls, attributes_list: list[str]) -> dict[str, str]:
            return cls._validate_attributes(attributes_list)

    else:

        @validator("attributes", pre=True)
        def validate_attributes(cls, attributes_list: list[str]) -> dict[str, str]:
            return cls._validate_attributes(attributes_list)

    def search(self, predicate: Callable[[DOMNode], bool]) -> list[DOMNode]:
        """Ищет узлы в DOM дереве с помощью predicate."""

        def _search(node: DOMNode, found_nodes: list[DOMNode]) -> None:
            if predicate(node):
                found_nodes.append(node)
            for child in node.children:
                _search(child, found_nodes)

        found_nodes: list[DOMNode] = []
        _search(self, found_nodes)
        return found_nodes

    @property
    def text(self) -> str:
        """Возвращает текстовое содержимое узла и всех его потомков.

        Returns:
            Текстовое содержимое узла.
        """
        text_parts: list[str] = []

        # Добавляем значение текущего узла если это текстовый узел
        if self.value:
            text_parts.append(self.value)

        # Рекурсивно собираем текст из дочерних узлов
        for child in self.children:
            text_parts.append(child.text)

        return "".join(text_parts)
