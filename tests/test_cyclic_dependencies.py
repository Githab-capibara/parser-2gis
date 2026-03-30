"""
Тесты на отсутствие циклических зависимостей.

Использует AST анализ для проверки графа зависимостей между модулями.
Примечание: тест с pydeps удалён так как требует установки дополнительной зависимости.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


class TestCyclicDependencies:
    """Тесты на отсутствие циклических зависимостей."""

    def test_no_direct_circular_imports(self) -> None:
        """Проверяет отсутствие прямых циклических импортов через AST анализ."""
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Словарь зависимостей: модуль -> множество импортируемых модулей
        dependencies: dict[str, set[str]] = {}

        # Сканируем основные модули
        core_modules = [
            "cache.py",
            "common.py",
            "config.py",
            "validation.py",
            "parallel_parser.py",
            "constants.py",
            "main.py",
        ]

        for module_name in core_modules:
            module_path = project_root / module_name
            if not module_path.exists():
                continue

            content = module_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            imported_modules: set[str] = set()

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("."):
                        # Относительный импорт
                        imported = node.module.lstrip(".")
                        if imported:
                            imported_modules.add(imported.split(".")[0] + ".py")
                    elif node.module:
                        # Абсолютный импорт
                        if node.module.startswith("parser_2gis"):
                            imported = node.module.replace("parser_2gis.", "")
                            imported_modules.add(imported.split(".")[0] + ".py")

            dependencies[module_name] = imported_modules

        # Проверяем циклы
        cycles: list[str] = []
        checked_pairs: set[str] = set()

        for module_a, deps_a in dependencies.items():
            for module_b in deps_a:
                if module_b in dependencies:
                    deps_b = dependencies[module_b]
                    if module_a in deps_b:
                        # Сортируем чтобы избежать дубликатов A<->B и B<->A
                        pair = tuple(sorted([module_a, module_b]))
                        if pair not in checked_pairs:
                            cycles.append(f"{module_a} <-> {module_b}")
                            checked_pairs.add(pair)

        assert not cycles, "Обнаружены циклические зависимости между модулями:\n" + "\n".join(
            f"  {c}" for c in cycles
        )


if __name__ == "__main__":
    import ast

    pytest.main([__file__, "-v"])
