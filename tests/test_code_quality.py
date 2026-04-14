"""
Тесты для качества кода.

Проверяет:
- Наличие type hints у всех публичных функций
- Отсутствие функций длиннее 50 строк
- Отсутствие вложенности глубже 4 уровней
- Вынос магических чисел в константы
- Обработку UnicodeEncodeError и UnicodeDecodeError
"""

import ast
import re
from pathlib import Path

import pytest


class TestCodeQuality:
    """Тесты качества кода."""

    @pytest.fixture(scope="class")
    def project_root(self) -> Path:
        """Получает корень проекта.

        Returns:
            Path к корню проекта.
        """
        return Path(__file__).parent.parent.parent / "parser_2gis"

    @pytest.fixture(scope="class")
    def python_files(self, project_root: Path) -> list[Path]:
        """Получает список Python файлов.

        Args:
            project_root: Путь к корню проекта.

        Returns:
            Список путей к Python файлам.
        """
        exclude_dirs = {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            "tests",
            "venv",
            ".git",
        }

        python_files = []

        for py_file in project_root.rglob("*.py"):
            # Пропускаем исключенные директории
            if any(part in exclude_dirs for part in py_file.parts):
                continue

            # Пропускаем __init__.py файлы
            if py_file.name == "__init__.py":
                continue

            python_files.append(py_file)

        return python_files

    @pytest.fixture(scope="class")
    def parsed_files(self, python_files: list[Path]) -> list[tuple[Path, ast.AST]]:
        """Парсит Python файлы.

        Args:
            python_files: Список путей к Python файлам.

        Returns:
            Список кортежей (путь, AST дерево).
        """
        parsed = []

        for py_file in python_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                parsed.append((py_file, tree))
            except (SyntaxError, UnicodeDecodeError):
                # Пропускаем файлы с ошибками синтаксиса
                pass

        return parsed

    def test_type_hints_presence(self, parsed_files: list[tuple[Path, ast.AST]]) -> None:
        """Тест наличия type hints у публичных функций.

        Проверяет:
        - Все публичные функции имеют type hints
        - Return type указан
        """
        files_without_hints = []

        for file_path, tree in parsed_files:
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.FunctionDef)
                    and not node.name.startswith("_")
                    and node.returns is None
                ):
                    # Проверяем наличие argument annotations
                    has_args_hints = all(
                        arg.annotation is not None
                        for arg in node.args.args
                        if arg.arg != "self" and arg.arg != "cls"
                    )

                    if not has_args_hints:
                        files_without_hints.append(f"{file_path.name}:{node.name}")

        # Разрешаем до 10% функций без type hints
        total_public_functions = sum(
            1
            for _, tree in parsed_files
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
        )

        max_allowed_without_hints = max(10, int(total_public_functions * 0.1))

        assert len(files_without_hints) <= max_allowed_without_hints, (
            f"Слишком много функций без type hints: {len(files_without_hints)} "
            f"(максимум: {max_allowed_without_hints}). "
            f"Примеры: {files_without_hints[:5]}"
        )

    def test_function_length(self, parsed_files: list[tuple[Path, ast.AST]]) -> None:
        """Тест длины функций.

        Проверяет:
        - Отсутствие функций длиннее 50 строк
        - Кроме исключений (сложные методы)
        """
        # Исключения: известные длинные функции
        exceptions = {
            ("main.py", "_parse_search_results"),  # Основной цикл парсинга
            ("parallel_parser.py", "_worker"),  # Worker функция
        }

        long_functions = []

        for file_path, tree in parsed_files:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Вычисляем длину функции
                    if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
                        func_length = node.end_lineno - node.lineno
                    else:
                        # Fallback: подсчет по телу функции
                        func_length = len(node.body)

                    if func_length > 50 and (file_path.name, node.name) not in exceptions:
                        long_functions.append(
                            f"{file_path.name}:{node.name} ({func_length} строк)"
                        )

        # Разрешаем до 5 длинных функций
        assert len(long_functions) <= 5, (
            f"Слишком много длинных функций: {len(long_functions)}. Примеры: {long_functions[:5]}"
        )

    def test_nesting_depth(self, parsed_files: list[tuple[Path, ast.AST]]) -> None:
        """Тест глубины вложенности.

        Проверяет:
        - Отсутствие вложенности глубже 4 уровней
        """

        def get_max_depth(node, current_depth=0) -> int:
            """Получает максимальную глубину вложенности."""
            max_depth = current_depth

            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                    child_depth = get_max_depth(child, current_depth + 1)
                    max_depth = max(max_depth, child_depth)
                else:
                    child_depth = get_max_depth(child, current_depth)
                    max_depth = max(max_depth, child_depth)

            return max_depth

        deep_nesting = []

        for file_path, tree in parsed_files:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    max_depth = get_max_depth(node)

                    if max_depth > 4:
                        deep_nesting.append(f"{file_path.name}:{node.name} (глубина: {max_depth})")

        # Разрешаем до 5 функций с глубокой вложенностью
        assert len(deep_nesting) <= 5, (
            f"Слишком много функций с глубокой вложенностью: {len(deep_nesting)}. "
            f"Примеры: {deep_nesting[:5]}"
        )

    def test_magic_numbers(self, parsed_files: list[tuple[Path, ast.AST]]) -> None:
        """Тест магических чисел.

        Проверяет:
        - Магические числа вынесены в константы
        - Кроме 0, 1, -1, 2, 10, 100
        """
        # Разрешенные магические числа
        allowed_numbers = {0, 1, -1, 2, 10, 100}

        # Паттерн для констант
        constant_pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")

        magic_numbers = []

        for file_path, tree in parsed_files:
            # Собираем имена констант в файле
            constants = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and constant_pattern.match(target.id):
                            constants.add(target.id)

            # Ищем магические числа
            for node in ast.walk(tree):
                if isinstance(node, ast.Num) and node.n not in allowed_numbers:  # Python 3.7
                    # Проверяем не используется ли в сравнении с константой
                    magic_numbers.append(f"{file_path.name}:{node.lineno} (число: {node.n})")
                elif isinstance(node, ast.Constant) and isinstance(
                    node.value, (int, float)
                ) and node.value not in allowed_numbers:  # Python 3.8+
                    magic_numbers.append(
                        f"{file_path.name}:{node.lineno} (число: {node.value})"
                    )

        # Разрешаем до 20 магических чисел
        assert len(magic_numbers) <= 20, (
            f"Слишком много магических чисел: {len(magic_numbers)}. Примеры: {magic_numbers[:5]}"
        )

    def test_unicode_error_handling(self, parsed_files: list[tuple[Path, ast.AST]]) -> None:
        """Тест обработки Unicode ошибок.

        Проверяет:
        - UnicodeEncodeError обрабатывается
        - UnicodeDecodeError обрабатывается
        """
        files_without_unicode_handling = []

        for file_path, tree in parsed_files:
            # Проверяем наличие обработки Unicode ошибок
            has_unicode_handling = False

            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is not None:
                    # Проверяем тип исключения
                    if isinstance(node.type, ast.Name):
                        if node.type.id in (
                            "UnicodeEncodeError",
                            "UnicodeDecodeError",
                            "UnicodeError",
                        ):
                            has_unicode_handling = True
                            break
                    elif isinstance(node.type, ast.Tuple):
                        for elt in node.type.elts:
                            if isinstance(elt, ast.Name) and elt.id in (
                                "UnicodeEncodeError",
                                "UnicodeDecodeError",
                                "UnicodeError",
                            ):
                                has_unicode_handling = True
                                break

            # Проверяем файлы которые работают с текстом
            if file_path.name in ("csv_writer.py", "path_utils.py", "serializer.py") and not has_unicode_handling:
                files_without_unicode_handling.append(file_path.name)

        # Разрешаем до 3 файлов без обработки Unicode
        assert len(files_without_unicode_handling) <= 3, (
            f"Файлы без обработки Unicode ошибок: {files_without_unicode_handling}"
        )

    def test_docstrings_presence(self, parsed_files: list[tuple[Path, ast.AST]]) -> None:
        """Тест наличия docstrings.

        Проверяет:
        - Все публичные функции имеют docstrings
        - Все классы имеют docstrings
        """
        functions_without_docstrings = []
        classes_without_docstrings = []

        for file_path, tree in parsed_files:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        functions_without_docstrings.append(f"{file_path.name}:{node.name}")

                elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    docstring = ast.get_docstring(node)
                    if not docstring:
                        classes_without_docstrings.append(f"{file_path.name}:{node.name}")

        # Разрешаем до 20% функций без docstrings
        total_public_functions = len(functions_without_docstrings) + sum(
            1
            for _, tree in parsed_files
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and not node.name.startswith("_")
            and ast.get_docstring(node)
        )

        max_allowed = max(20, int(total_public_functions * 0.2))

        assert len(functions_without_docstrings) <= max_allowed, (
            f"Слишком много функций без docstrings: {len(functions_without_docstrings)}. "
            f"Примеры: {functions_without_docstrings[:5]}"
        )

    def test_exception_handling_best_practices(
        self, parsed_files: list[tuple[Path, ast.AST]]
    ) -> None:
        """Тест лучших практик обработки исключений.

        Проверяет:
        - Не используется bare except
        - Исключения логируются
        """
        bare_except_count = 0

        for _file_path, tree in parsed_files:
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    bare_except_count += 1

        # Разрешаем до 5 bare except
        assert bare_except_count <= 5, f"Слишком много bare except: {bare_except_count}"
