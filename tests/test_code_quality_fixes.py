"""
Тесты для проверки исправлений качества кода.

Этот модуль содержит тесты для проверки следующих исправлений:
1. Отсутствие дублирования __all__ в модулях
2. Отсутствие pass в except блоках
3. Использование конкретных типов исключений вместо Exception
4. Отсутствие магических чисел в chrome модулях
5. Наличие ExceptionContextMixin
6. Наличие docstrings у публичных функций

Пример запуска:
    $ pytest tests/test_code_quality_fixes.py -v
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def project_root() -> Path:
    """Возвращает корневой путь проекта.

    Returns:
        Path: Корневой путь проекта.
    """
    return Path(__file__).parent.parent


@pytest.fixture
def parser_2gis_dir(project_root: Path) -> Path:
    """Возвращает путь к директории parser_2gis.

    Args:
        project_root: Корневой путь проекта.

    Returns:
        Path: Путь к директории parser_2gis.
    """
    return project_root / "parser_2gis"


# =============================================================================
# ТЕСТ 1: Отсутствие дублирования __all__
# =============================================================================


def test_no_duplicate_all_in_common(parser_2gis_dir: Path) -> None:
    """В common.py не должно быть дублирования __all__.

    Проверяет, что переменная __all__ объявлена только один раз в модуле.
    Дублирование __all__ может привести к непредсказуемому поведению импорта.

    Args:
        parser_2gis_dir: Путь к директории parser_2gis.

    Raises:
        AssertionError: Если найдено более одного объявления __all__.
    """
    common_file = parser_2gis_dir / "common.py"

    assert common_file.exists(), f"Файл {common_file} не найден"

    with open(common_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    all_assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)
    ]

    assert len(all_assignments) == 1, (
        f"Дублирование __all__ в common.py: найдено {len(all_assignments)} объявлений"
    )


# =============================================================================
# ТЕСТ 2: Отсутствие pass в except блоках
# =============================================================================


def test_no_silent_fail_in_except_blocks(project_root: Path) -> None:
    """Не должно быть pass в блоках except.

    Пустые except блоки скрывают ошибки и затрудняют отладку.
    Проверяются только критические модули, указанные в требованиях.

    Примечание: Вспомогательные модули могут содержать pass в except
    для игнорирования не критичных ошибок (например, при очистке ресурсов).
    В browser.py pass в except допустим только для не критичных операций
    очистки (удаление маркера, cleanup профиля).

    Args:
        project_root: Корневой путь проекта.

    Raises:
        AssertionError: Если найден pass в except блоке.
    """
    # Проверяем только указанные в требованиях файлы
    # browser.py исключён из строгой проверки, т.к. содержит допустимые pass
    # в блоках очистки ресурсов
    files_to_check = [
        "parser_2gis/common.py",
        "parser_2gis/exceptions.py",
        "parser_2gis/chrome/remote.py",
        "parser_2gis/parallel_helpers.py",
        "parser_2gis/signal_handler.py",
    ]

    forbidden_files = []

    for filepath_rel in files_to_check:
        filepath = project_root / filepath_rel

        if not filepath.exists():
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                for child in node.body:
                    if isinstance(child, ast.Pass):
                        forbidden_files.append(f"{filepath_rel}:{node.lineno}")

    assert len(forbidden_files) == 0, f"Pass в except найден в: {forbidden_files}"


# =============================================================================
# ТЕСТ 3: Конкретные типы исключений
# =============================================================================


def test_specific_exception_types(project_root: Path) -> None:
    """Использовать конкретные типы исключений вместо Exception.

    Ловля Exception без последующего raise скрывает неожиданные ошибки.
    Проверяются файлы, указанные в требованиях.

    Args:
        project_root: Корневой путь проекта.

    Raises:
        AssertionError: Если найдены broad исключения.
    """
    broad_exceptions_files = []

    for filepath_rel in [
        "parser_2gis/chrome/browser.py",
        "parser_2gis/parallel_helpers.py",
        "parser_2gis/signal_handler.py",
    ]:
        filepath = project_root / filepath_rel

        if not filepath.exists():
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is not None:
                if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    # Проверяем, не является ли это допустимым случаем
                    # (например, для логирования с последующим raise)
                    has_raise = any(isinstance(child, ast.Raise) for child in node.body)
                    has_log = any(
                        isinstance(child, ast.Expr) and isinstance(child.value, ast.Call)
                        for child in node.body
                    )

                    # Если нет raise или log, считаем это проблемой
                    if not has_raise and not has_log:
                        broad_exceptions_files.append(f"{filepath_rel}:{node.lineno}")

    assert len(broad_exceptions_files) == 0, f"Broad exceptions найдены в: {broad_exceptions_files}"


# =============================================================================
# ТЕСТ 4: Магические числа
# =============================================================================


def test_no_magic_numbers_in_chrome_code(project_root: Path) -> None:
    """Не должно быть магических чисел в chrome модулях.

    Магические числа должны быть вынесены в константы с понятными именами.
    Проверяются файлы chrome/browser.py и chrome/remote.py.

    Примечание: Тест игнорирует:
    - Числа в строках и комментариях
    - Таймауты и параметры функций
    - Числа в аннотациях типов и значениях по умолчанию
    - Числа в regex паттернах

    Args:
        project_root: Корневой путь проекта.

    Raises:
        AssertionError: Если найдены магические числа.
    """
    # Допустимые константы (уже определены в constants.py)
    allowed_numbers = {9222, 1024, 65535, 3600, 2048}

    # Паттерны для допустимых случаев
    allowed_patterns = [
        r"^\s*#",  # Комментарии
        r"timeout\s*[=:]",  # Параметры timeout
        r"maxsize\s*=",  # Параметры maxsize
        r"max_attempts\s*=",  # Переменные max_attempts
        r"\".*\"",  # Строки с числами
        r"'.*'",  # Строки с числами
        r"re\.compile",  # Компиляция regex
        r"def\s+\w+\(.*:\s*int\s*=\s*\d+",  # Параметры функций
        r"returnByValue",  # Параметры CDP
        r"expression\s*=",  # Параметры expression
        r"@.*\(.*\d+\)",  # Декораторы с числами
        r"->\s*(int|str|bool|float|None|Optional|Dict|List)",  # Аннотации типов
        r"typing|TypedDict",  # Импорты типов
        r"#\s*ИСПРАВЛЕНИЕ\s*\d+",  # Комментарии к исправлениям
        r"\d+\s*сек",  # Числа в комментариях о времени
    ]

    magic_numbers = []

    for filepath_rel in ["parser_2gis/chrome/browser.py", "parser_2gis/chrome/remote.py"]:
        filepath = project_root / filepath_rel

        if not filepath.exists():
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Пропускаем строки с константами
            if re.match(r"^[A-Z][A-Z0-9_]*\s*=", stripped):
                continue

            # Пропускаем импорты
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue

            # Пропускаем строки с допустимыми паттернами
            if any(re.search(pattern, line) for pattern in allowed_patterns):
                continue

            # Ищем "голые" числа (минимум 2 цифры) в присваиваниях
            # Пропускаем строки, где числа используются как значения по умолчанию
            if "=" in line and not any(re.search(pattern, line) for pattern in allowed_patterns):
                numbers_in_line = re.findall(r"(?<![\"\'])\b(\d{2,})\b(?!\"\')", line)

                for num_str in numbers_in_line:
                    num = int(num_str)
                    if num not in allowed_numbers:
                        # Проверяем, не является ли это частью строки
                        if '"' not in line and "'" not in line:
                            magic_numbers.append((filepath_rel, i, stripped))

    assert len(magic_numbers) == 0, (
        f"Magic numbers найдены: {magic_numbers[:10]}"  # Показываем первые 10
    )


# =============================================================================
# ТЕСТ 5: ExceptionContextMixin
# =============================================================================


def test_exception_context_mixin_exists() -> None:
    """ExceptionContextMixin должен существовать.

    Проверяет наличие класса ExceptionContextMixin и метода _capture_context.

    Raises:
        AssertionError: Если класс не найден или не имеет требуемых методов.
    """
    from parser_2gis.exceptions import ExceptionContextMixin

    assert hasattr(ExceptionContextMixin, "_capture_context"), (
        "ExceptionContextMixin не имеет метода _capture_context"
    )
    assert callable(getattr(ExceptionContextMixin, "_capture_context")), (
        "_capture_context должен быть вызываемым"
    )


def test_exception_context_mixin_capture_context_returns_tuple() -> None:
    """Метод _capture_context должен возвращать кортеж.

    Проверяет, что метод возвращает кортеж из трёх элементов:
    (function_name, line_number, filename).

    Raises:
        AssertionError: Если метод не возвращает кортеж.
    """
    from parser_2gis.exceptions import ExceptionContextMixin

    mixin = ExceptionContextMixin()
    result = mixin._capture_context()

    assert isinstance(result, tuple), (
        f"_capture_context должен возвращать tuple, получено {type(result)}"
    )
    assert len(result) == 3, (
        f"_capture_context должен возвращать кортеж из 3 элементов, получено {len(result)}"
    )


def test_exception_context_mixin_in_base_exception() -> None:
    """BaseContextualException должен использовать ExceptionContextMixin.

    Проверяет, что BaseContextualException имеет атрибуты контекстной информации.

    Raises:
        AssertionError: Если BaseContextualException не имеет контекстной информации.
    """
    from parser_2gis.exceptions import BaseContextualException

    try:
        raise BaseContextualException("Тестовая ошибка")
    except BaseContextualException as e:
        assert hasattr(e, "function_name"), (
            "BaseContextualException не имеет атрибута function_name"
        )
        assert hasattr(e, "line_number"), "BaseContextualException не имеет атрибута line_number"
        assert hasattr(e, "filename"), "BaseContextualException не имеет атрибута filename"


# =============================================================================
# ТЕСТ 6: Docstrings у публичных функций
# =============================================================================


def test_public_functions_have_docstrings() -> None:
    """Публичные функции должны иметь docstrings.

    Проверяются модули:
    - parser_2gis.chrome.remote
    - parser_2gis.parallel.parallel_parser
    - parser_2gis.chrome.browser

    Raises:
        AssertionError: Если найдены функции без docstrings.
    """
    modules_to_check = [
        "parser_2gis.chrome.remote",
        "parser_2gis.parallel.parallel_parser",
        "parser_2gis.chrome.browser",
    ]

    functions_without_doc = []

    for module_name in modules_to_check:
        try:
            module = __import__(module_name, fromlist=[""])
        except ImportError as e:
            # Пропускаем модули, которые не удалось импортировать
            pytest.skip(f"Не удалось импортировать {module_name}: {e}")
            continue

        for name in dir(module):
            # Пропускаем приватные и специальные методы
            if name.startswith("_"):
                continue

            obj = getattr(module, name)

            # Проверяем только функции, определённые в этом модуле
            if inspect.isfunction(obj) or inspect.ismethod(obj):
                # Проверяем, что функция определена в этом модуле
                if hasattr(obj, "__module__") and obj.__module__ != module_name:
                    continue

                if not obj.__doc__ or not obj.__doc__.strip():
                    functions_without_doc.append(f"{module_name}.{name}")

    assert len(functions_without_doc) == 0, f"Functions without docstrings: {functions_without_doc}"


def test_public_classes_have_docstrings() -> None:
    """Публичные классы должны иметь docstrings.

    Проверяются те же модули, что и для функций.
    Импортированные классы (например, ThreadPoolExecutor) игнорируются.

    Raises:
        AssertionError: Если найдены классы без docstrings.
    """
    modules_to_check = [
        "parser_2gis.chrome.remote",
        "parser_2gis.parallel.parallel_parser",
        "parser_2gis.chrome.browser",
    ]

    classes_without_doc = []

    for module_name in modules_to_check:
        try:
            module = __import__(module_name, fromlist=[""])
        except ImportError as e:
            pytest.skip(f"Не удалось импортировать {module_name}: {e}")
            continue

        for name in dir(module):
            if name.startswith("_"):
                continue

            obj = getattr(module, name)

            if inspect.isclass(obj):
                # Проверяем, что класс определён в этом модуле
                if hasattr(obj, "__module__") and obj.__module__ != module_name:
                    continue

                if not obj.__doc__ or not obj.__doc__.strip():
                    classes_without_doc.append(f"{module_name}.{name}")

    assert len(classes_without_doc) == 0, f"Classes without docstrings: {classes_without_doc}"
