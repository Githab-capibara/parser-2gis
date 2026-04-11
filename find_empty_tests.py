#!/usr/bin/env python3
"""Скрипт для поиска пустых тестов (без ассертов)."""

import ast
import os
import sys
from pathlib import Path


class TestFunctionVisitor(ast.NodeVisitor):
    """Посетитель AST для анализа тестовых функций."""

    def __init__(self, source_lines):
        self.source_lines = source_lines
        self.empty_tests = []
        self.all_tests = []

    def visit_FunctionDef(self, node) -> None:
        if node.name.startswith("test_"):
            self.all_tests.append(node.name)
            self._check_test_function(node)
        self.generic_visit(node)

    def _check_test_function(self, node) -> None:
        """Проверяет, содержит ли тест ассерты или другие проверки."""
        has_assert = self._has_assertions(node)
        has_mock_assert = self._has_mock_assertions(node)
        has_print = self._has_print(node)
        has_only_pass = self._has_only_pass_or_ellipsis(node)
        has_only_creation = self._has_only_object_creation(node)

        if not has_assert and not has_mock_assert:
            self.empty_tests.append({
                "name": node.name,
                "lineno": node.lineno,
                "end_lineno": node.end_lineno,
                "has_print": has_print,
                "has_only_pass": has_only_pass,
                "has_only_creation": has_only_creation,
                "source": self._get_source(node),
            })

    def _get_source(self, node):
        """Получает исходный код функции."""
        start = node.lineno - 1
        end = node.end_lineno
        return "\n".join(self.source_lines[start:end])

    def _has_assertions(self, node) -> bool:
        """Проверяет наличие assert, pytest.raises, pytest.warns и т.д."""
        for child in ast.walk(node):
            # Проверка assert statement
            if isinstance(child, ast.Assert):
                return True
            # Проверка вызовов pytest.raises, pytest.warns
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute):
                    # pytest.raises, pytest.warns, mock.assert_called
                    if func.attr in ("raises", "warns", "deprecated_call",
                                     "pytest_raises", "assert_called",
                                     "assert_called_once", "assert_called_with",
                                     "assert_called_once_with", "assert_has_calls",
                                     "assert_not_called"):
                        return True
                    # Проверка цепочек вроде pytest.raises
                    if isinstance(func.value, ast.Attribute) and func.value.attr == "raises":
                        return True
                elif isinstance(func, ast.Name):
                    if func.id in ("pytest_raises", "raises"):
                        return True
        return False

    def _has_mock_assertions(self, node) -> bool:
        """Проверяет наличие mock.assert_called и подобных."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Attribute):
                    if func.attr.startswith("assert_"):
                        return True
                    # Проверка вызовых методов mock
                    if isinstance(func.value, ast.Name) and func.value.id == "mock":
                        return True
                    if isinstance(func.value, ast.Attribute) and func.value.attr in (
                        "mock",
                        "return_value",
                    ):
                        return True
        return False

    def _has_print(self, node) -> bool:
        """Проверяет наличие print() в тесте."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == "print":
                return True
        return False

    def _has_only_pass_or_ellipsis(self, node) -> bool:
        """Проверяет, содержит ли функция только pass или ..."""
        if len(node.body) == 1:
            stmt = node.body[0]
            if isinstance(stmt, ast.Pass):
                return True
            if (
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and (stmt.value.value is ... or stmt.value.value is None)
            ):
                return True
        return False

    def _has_only_object_creation(self, node):
        """Проверяет, содержит ли функция только создание объектов без проверок."""
        has_creation = False
        has_nothing_else = True

        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                has_creation = True
            if isinstance(child, (ast.Assert,)):
                has_nothing_else = False
                break

        return has_creation and has_nothing_else


def analyze_test_file(filepath):
    """Анализирует один тестовый файл на наличие пустых тестов."""
    try:
        with open(filepath, encoding="utf-8") as f:
            source = f.read()

        source_lines = source.split("\n")
        tree = ast.parse(source)

        visitor = TestFunctionVisitor(source_lines)
        visitor.visit(tree)

        return visitor.empty_tests
    except Exception as e:
        print(f"Ошибка при анализе {filepath}: {e}", file=sys.stderr)
        return []


def main() -> None:
    test_dir = Path("/home/d/parser-2gis/tests")

    all_empty_tests = []
    files_analyzed = 0

    for root, _dirs, files in os.walk(test_dir):
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                filepath = os.path.join(root, file)
                empty_tests = analyze_test_file(filepath)

                if empty_tests:
                    all_empty_tests.append({
                        "file": filepath,
                        "tests": empty_tests,
                    })
                files_analyzed += 1

    print(f"Проанализировано файлов: {files_analyzed}")
    print(f"Файлов с пустыми тестами: {len(all_empty_tests)}")
    print("=" * 80)

    for item in all_empty_tests:
        print(f"\n📁 Файл: {item['file']}")
        print(f"   Количество пустых тестов: {len(item['tests'])}")
        print("-" * 60)

        for test in item["tests"]:
            print(f"\n   ❌ Тест: {test['name']}")
            print(f"      Строки: {test['lineno']}-{test['end_lineno']}")

            if test["has_only_pass"]:
                print("      Тип: Только pass или ...")
            elif test["has_print"]:
                print("      Тип: Содержит print(), но нет ассертов")
            elif test["has_only_creation"]:
                print("      Тип: Только создание объектов, без проверок")
            else:
                print("      Тип: Нет ассертов или проверок")

            # Показать первые 3 строки кода для понимания что делает тест
            lines = test["source"].split("\n")
            print("      Код:")
            for _i, line in enumerate(lines[:5]):
                print(f"        {line}")
            if len(lines) > 5:
                print(f"        ... (ещё {len(lines) - 5} строк)")
        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
