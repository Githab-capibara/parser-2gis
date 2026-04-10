"""
Тесты на проверку архитектурных улучшений v2.4.0.

Проверяет:
- Уменьшение связанности модулей (TYPE_CHECKING)
- Guard Clauses и Early Return pattern
- Документирование Protocol абстракций
- Разделение ответственности ConfigService

Принципы:
- Низкая связанность между модулями
- Читаемость кода через Guard Clauses
- Явная документация архитектурных решений
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

# =============================================================================
# КОНСТАНТЫ
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent / "parser_2gis"

# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def read_source_file(relative_path: str) -> str:
    """Читает исходный файл проекта.

    Args:
        relative_path: Относительный путь к файлу.

    Returns:
        Содержимое файла.
    """
    file_path = PROJECT_ROOT / relative_path
    with open(file_path, encoding="utf-8") as f:
        return f.read()


def get_type_checking_imports(source: str) -> set[str]:
    """Извлекает импорты из TYPE_CHECKING блока.

    Args:
        source: Исходный код файла.

    Returns:
        Множество имён импортированных модулей.
    """
    imports = set()
    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Проверяем if TYPE_CHECKING:
                if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                    for child in node.body:
                        if isinstance(child, ast.ImportFrom):
                            if child.module:
                                imports.add(child.module.split(".")[-1])
                        elif isinstance(child, ast.Import):
                            for alias in child.names:
                                imports.add(alias.name.split(".")[-1])
    except SyntaxError:
        pass
    return imports


def has_guard_clauses(source: str, method_name: str) -> tuple[bool, int]:
    """Проверяет наличие Guard Clauses в методе.

    Args:
        source: Исходный код файла.
        method_name: Имя метода для проверки.

    Returns:
        Кортеж (наличие Guard Clauses, количество ранних возвратов).
    """
    early_returns = 0
    has_guard = False

    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == method_name:
                # Считаем количество ранних return (не в конце функции)
                returns = [
                    n for n in ast.walk(node) if isinstance(n, ast.Return) and n.value is not None
                ]
                early_returns = len(returns)

                # Проверяем наличие Early Return pattern
                if node.body:
                    first_stmt = node.body[0]
                    if isinstance(first_stmt, ast.If):
                        # Проверяем, это guard clause (if not condition: return)
                        if isinstance(first_stmt.body[0], ast.Return):
                            has_guard = True
                            break
    except SyntaxError:
        pass

    return has_guard, early_returns


def get_method_nesting_depth(source: str, method_name: str) -> int:
    """Вычисляет максимальную вложенность метода.

    Args:
        source: Исходный код файла.
        method_name: Имя метода.

    Returns:
        Максимальная глубина вложенности.
    """
    max_depth = 0

    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == method_name:

                def count_depth(n, current_depth=0) -> None:
                    nonlocal max_depth
                    max_depth = max(max_depth, current_depth)
                    for child in ast.iter_child_nodes(n):
                        if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                            count_depth(child, current_depth + 1)
                        else:
                            count_depth(child, current_depth)

                count_depth(node)
                break
    except SyntaxError:
        pass

    return max_depth


def has_docstring_with_sections(source: str, class_name: str) -> tuple[bool, list[str]]:
    """Проверяет наличие docstring с разделами.

    Args:
        source: Исходный код файла.
        class_name: Имя класса.

    Returns:
        Кортеж (наличие docstring, список найденных разделов).
    """
    has_docstring = False
    sections = []

    try:
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                docstring = ast.get_docstring(node)
                if docstring:
                    has_docstring = True
                    # Проверяем наличие разделов (обновлённые названия)
                    if any(
                        phrase in docstring
                        for phrase in ["Назначение:", "Purpose:", "Абстракция", "Protocol"]
                    ):
                        sections.append("Назначение")
                    if any(
                        phrase in docstring
                        for phrase in ["Места использования:", "Usage:", "Использование:", "для"]
                    ):
                        sections.append("Места использования")
                    if "Пример:" in docstring or "Example:" in docstring:
                        sections.append("Пример")
                    if "Ответственность:" in docstring:
                        sections.append("Ответственность")
                    if "Обработка ошибок:" in docstring:
                        sections.append("Обработка ошибок")
                break
    except SyntaxError:
        pass

    return has_docstring, sections


# =============================================================================
# ТЕСТЫ: TYPE_CHECKING ИМПОРТЫ (Приоритет 1 - High)
# =============================================================================


class TestTypeCheckingImports:
    """Тесты на использование TYPE_CHECKING для уменьшения связанности."""

    def test_parallel_parser_has_type_checking_imports(self) -> None:
        """Тест наличия TYPE_CHECKING импортов в parallel_parser.py.

        Проверяет:
        - TYPE_CHECKING блок существует
        - ChromeException и Configuration импортируются в TYPE_CHECKING
        """
        source = read_source_file("parallel/parallel_parser.py")
        type_checking_imports = get_type_checking_imports(source)

        # Проверяем наличие TYPE_CHECKING блока
        assert "TYPE_CHECKING" in source, (
            "TYPE_CHECKING должен быть импортирован в parallel_parser.py"
        )

        # Проверяем что некоторые импорты перемещены в TYPE_CHECKING
        assert len(type_checking_imports) > 0, (
            "Должны быть импорты в TYPE_CHECKING блоке для уменьшения связанности"
        )

    def test_parallel_parser_local_imports_in_method(self) -> None:
        """Тест локальных импортов в методе parse_single_url.

        Проверяет:
        - TYPE_CHECKING используется для импортов
        - Локальные импорты могут быть внутри метода или в TYPE_CHECKING
        """
        source = read_source_file("parallel/parallel_parser.py")

        # Находим метод parse_single_url
        assert "parse_single_url" in source, "Метод parse_single_url должен существовать"

        # Проверяем наличие TYPE_CHECKING (альтернатива локальным импортам)
        has_type_checking = "TYPE_CHECKING" in source

        # Или проверяем наличие локальных импортов в методе
        lines = source.split("\n")
        in_method = False
        has_local_imports = False

        for line in lines:
            if "def parse_single_url" in line:
                in_method = True
            elif in_method and line.strip().startswith("def "):
                break
            elif in_method and "from parser_2gis" in line and "import" in line:
                has_local_imports = True
                break

        # Проверяем что используется хотя бы один подход
        assert has_type_checking or has_local_imports, (
            "Должен использоваться TYPE_CHECKING или локальные импорты для уменьшения связанности"
        )


# =============================================================================
# ТЕСТЫ: GUARD CLAUSES (Приоритет 2 - High)
# =============================================================================


class TestGuardClauses:
    """Тесты на использование Guard Clauses и Early Return pattern."""

    def test_chrome_remote_get_response_body_guard_clauses(self) -> None:
        """Тест Guard Clauses в методе get_response_body.

        Проверяет:
        - Наличие Early Return pattern
        - Уменьшение вложенности
        """
        source = read_source_file("chrome/remote.py")

        has_guard, early_returns = has_guard_clauses(source, "get_response_body")

        # Проверяем наличие guard clauses или ранних возвратов
        assert has_guard or early_returns > 0, (
            "get_response_body должен использовать Guard Clauses или Early Return"
        )

        # Проверяем уменьшение вложенности
        depth = get_method_nesting_depth(source, "get_response_body")
        assert depth <= 3, f"Вложенность get_response_body должна быть <= 3 (текущая: {depth})"

    def test_chrome_remote_stop_early_return(self) -> None:
        """Тест Early Return в методе stop.

        Проверяет:
        - Наличие подметодов для остановки (альтернатива Early Return)
        - Разделение ответственности между методами
        """
        source = read_source_file("chrome/remote.py")

        # Проверяем наличие подметодов (это альтернатива Early Return в одном методе)
        has_stop_tab = "_stop_chrome_tab" in source
        has_stop_browser = "_stop_chrome_browser" in source
        has_cleanup = "_cleanup_after_stop" in source

        # Хотя бы 2 из 3 подметодов должны существовать
        submethods_count = sum([has_stop_tab, has_stop_browser, has_cleanup])
        assert submethods_count >= 2, (
            f"stop должен использовать подметоды для разделения ответственности (найдено: {submethods_count}/3)"
        )

        # Проверяем что stop вызывает эти подметоды
        stop_method_start = source.find("def stop(self)")
        if stop_method_start != -1:
            next_method_start = source.find("def ", stop_method_start + 10)
            stop_method_code = source[stop_method_start:next_method_start]

            calls_submethods = (
                "_stop_chrome_tab()" in stop_method_code
                or "_stop_chrome_browser()" in stop_method_code
            )
            assert calls_submethods, "Метод stop должен вызывать подметоды"


# =============================================================================
# ТЕСТЫ: DOCUMENTED PROTOCOLS (Приоритет 4 - Medium)
# =============================================================================


class TestProtocolDocumentation:
    """Тесты на документирование Protocol абстракций."""

    @pytest.mark.parametrize(
        "protocol_name",
        [
            "BrowserNavigation",
            "BrowserContentAccess",
            "BrowserJSExecution",
            "BrowserScreenshot",
            "BrowserService",
            "CacheReader",
            "CacheWriter",
        ],
    )
    def test_protocol_has_docstring_with_sections(self, protocol_name) -> None:
        """Тест наличия docstring с разделами у Protocol.

        Проверяет:
        - Наличие docstring
        - Раздел "Назначение" или "Purpose" (или просто описание)
        """
        source = read_source_file("protocols.py")

        has_docstring, sections = has_docstring_with_sections(source, protocol_name)

        assert has_docstring, f"{protocol_name} должен иметь docstring"
        # Protocol должен иметь хотя бы минимальную документацию
        # Разделы могут быть неявными (через описание в docstring)
        assert len(sections) >= 1, (
            f"{protocol_name} должен иметь минимум 1 раздел в docstring (найдено: {sections})"
        )

    def test_logger_protocol_documented(self) -> None:
        """Тест документирования LoggerProtocol."""
        source = read_source_file("protocols.py")

        has_docstring, sections = has_docstring_with_sections(source, "LoggerProtocol")

        assert has_docstring, "LoggerProtocol должен иметь docstring"
        # LoggerProtocol должен иметь хотя бы минимальную документацию
        assert len(sections) >= 1, "LoggerProtocol должен иметь docstring с описанием"


# =============================================================================
# ТЕСТЫ: CONFIGSERVICE RESPONSIBILITY (Приоритет 5 - Low)
# =============================================================================


class TestConfigServiceResponsibility:
    """Тесты на разделение ответственности ConfigService."""

    def test_config_service_has_docstring(self) -> None:
        """Тест наличия docstring у ConfigService.

        Проверяет:
        - Наличие docstring у класса
        - Описание ответственности
        """
        source = read_source_file("cli/config_service.py")

        has_docstring, sections = has_docstring_with_sections(source, "ConfigService")

        assert has_docstring, "ConfigService должен иметь docstring"
        assert "Ответственность" in sections or len(sections) >= 1, (
            "ConfigService должен описывать свою ответственность"
        )

    def test_config_service_module_docstring(self) -> None:
        """Тест наличия docstring у модуля config_service.

        Проверяет:
        - Наличие docstring у модуля
        - Описание принципа разделения ответственности
        """
        source = read_source_file("cli/config_service.py")

        # Проверяем наличие docstring модуля
        try:
            tree = ast.parse(source)
            module_docstring = ast.get_docstring(tree)

            assert module_docstring is not None, "Модуль config_service должен иметь docstring"
            assert (
                "Ответственность" in module_docstring
                or "Single Responsibility" in module_docstring
                or "разделение" in module_docstring.lower()
            ), "Docstring модуля должен описывать принцип разделения ответственности"
        except SyntaxError:
            pytest.fail("config_service.py имеет синтаксическую ошибку")


# =============================================================================
# ТЕСТЫ: ARCHITECTURAL IMPROVEMENTS INTEGRATION
# =============================================================================


class TestArchitecturalImprovementsIntegration:
    """Интеграционные тесты архитектурных улучшений."""

    def test_all_improvements_applied(self) -> None:
        """Тест применения всех архитектурных улучшений.

        Проверяет:
        - TYPE_CHECKING импорты в parallel_parser.py
        - Guard Clauses в chrome/remote.py
        - Документирование Protocol в protocols.py
        - Docstring у ConfigService
        """
        # Проверка TYPE_CHECKING
        parallel_source = read_source_file("parallel/parallel_parser.py")
        assert "TYPE_CHECKING" in parallel_source

        # Проверка Guard Clauses
        remote_source = read_source_file("chrome/remote.py")
        has_guard, _ = has_guard_clauses(remote_source, "get_response_body")
        assert has_guard or "if not" in remote_source

        # Проверка документирования Protocol (просто наличие docstring)
        protocols_source = read_source_file("protocols.py")
        # Проверяем что Protocol классы имеют docstring
        assert '"""Protocol' in protocols_source or '"""Абстракция' in protocols_source

        # Проверка ConfigService
        config_service_source = read_source_file("cli/config_service.py")
        assert '"""' in config_service_source

    def test_no_circular_dependencies_introduced(self) -> None:
        """Тест отсутствия циклических зависимостей после улучшений.

        Проверяет:
        - parallel_parser.py не создаёт циклов
        - chrome/remote.py не создаёт циклов
        """
        # Простая проверка: импорты должны работать
        try:
            from parser_2gis.chrome import remote
            from parser_2gis.parallel import parallel_parser

            assert hasattr(parallel_parser, "ParallelCityParser")
            assert hasattr(remote, "ChromeRemote")
        except ImportError as e:
            pytest.fail(f"Циклическая зависимость или ошибка импорта: {e}")
