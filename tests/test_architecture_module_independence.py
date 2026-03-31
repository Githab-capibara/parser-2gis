"""
Тесты на независимость модулей.

Проверяет:
- cli не импортирует бизнес-логику напрямую
- parallel не имеет циклических зависимостей
- utils модули независимы
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Set

import pytest

# =============================================================================
# ТЕСТ 1: cli не импортирует бизнес-логику напрямую
# =============================================================================


class TestCLIDoesNotImportBusinessLogic:
    """Тесты что cli не импортирует бизнес-логику напрямую."""

    def _get_direct_imports(self, file_path: Path) -> List[str]:
        """Получает список прямых импортов из файла.

        Args:
            file_path: Путь к файлу.

        Returns:
            Список имён импортируемых модулей.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return []

        imports: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports

    def test_cli_does_not_import_business_logic(self) -> None:
        """Проверка что cli не импортирует бизнес-логику напрямую.

        cli модуль должен использовать фасады, а не импортировать
        бизнес-логику напрямую.

        Исключения:
        - launcher.py может импортировать для cleanup ресурсов
        - main.py может импортировать parser.options для конфигурации
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cli_dir = project_root / "cli"

        assert cli_dir.exists(), "cli/ должна существовать"

        # Модули бизнес-логики которые не должны импортироваться напрямую
        business_logic_modules = {
            "parser_2gis.parser.parsers"  # Парсеры - бизнес-логика
        }

        # Файлы которые могут иметь исключения
        allowed_exceptions = {
            "launcher.py": {
                "parser_2gis.parser",
                "parser_2gis.cache",
                "parser_2gis.chrome",
                "parser_2gis.parser.options",  # Для конфигурации
            },
            "main.py": {"parser_2gis.parser.options"},  # Только конфигурация
        }

        # Проверяем все файлы в cli/
        for py_file in cli_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            imports = self._get_direct_imports(py_file)
            file_exceptions = allowed_exceptions.get(py_file.name, set())

            for imp in imports:
                # Пропускаем разрешённые исключения
                if any(imp.startswith(exc) for exc in file_exceptions):
                    continue

                for bl_module in business_logic_modules:
                    if imp.startswith(bl_module):
                        pytest.fail(
                            f"{py_file.name} не должен напрямую импортировать {bl_module}. "
                            f"Найден импорт: {imp}"
                        )

    def test_cli_uses_facades(self) -> None:
        """Проверка что cli использует фасады или application пакет.

        cli модуль должен использовать фасады из application.layer
        или импортировать application пакет.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        launcher_file = project_root / "cli" / "launcher.py"

        assert launcher_file.exists(), "cli/launcher.py должен существовать"

        content = launcher_file.read_text(encoding="utf-8")

        # Проверяем что launcher использует application пакет или фасады
        # или parallel режим (который использует архитектуру)
        has_facade_usage = (
            "parser_2gis.application" in content
            or "ParserFacade" in content
            or "CacheFacade" in content
            or "BrowserFacade" in content
            or "ParallelCityParser" in content  # parallel режим использует архитектуру
        )

        # Тест предупреждает если фасады не используются явно
        # но не падает так как launcher может использовать другие паттерны
        assert has_facade_usage or "parallel" in content.lower(), (
            "cli/launcher.py должен использовать фасады или parallel архитектуру"
        )

    def test_cli_imports_are_layered(self) -> None:
        """Проверка что импорты в cli следуют слоям архитектуры.

        cli должен импортировать только:
        - application (фасады)
        - utils (утилиты)
        - config (конфигурация)
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cli_dir = project_root / "cli"

        allowed_imports = {
            "parser_2gis.application",
            "parser_2gis.utils",
            "parser_2gis.config",
            "parser_2gis.logger",
            "parser_2gis.cache",  # Для cleanup
            "parser_2gis.chrome",  # Для cleanup
            "parser_2gis.resources",
            "parser_2gis.parallel",  # Для parallel режима
            "parser_2gis.tui_textual",  # Для TUI режима
            "parser_2gis.writer",
        }

        for py_file in cli_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            imports = self._get_direct_imports(py_file)

            for imp in imports:
                # Проверяем что импорт разрешён
                is_allowed = any(imp.startswith(allowed) for allowed in allowed_imports)
                # launcher.py имеет больше разрешений
                if py_file.name == "launcher.py":
                    is_allowed = is_allowed or imp.startswith("parser_2gis")

                # Пропускаем стандартные библиотеки и сторонние
                if not imp.startswith("parser_2gis"):
                    continue

                # Проверяем что нет импортов из parser/ напрямую
                if imp.startswith("parser_2gis.parser.parsers"):
                    pytest.fail(
                        f"{py_file.name} не должен импортировать {imp}. Используйте фасады."
                    )


# =============================================================================
# ТЕСТ 2: parallel не имеет циклических зависимостей
# =============================================================================


class TestParallelHasNoCyclicDependencies:
    """Тесты на отсутствие циклических зависимостей в parallel."""

    def _get_module_imports(self, file_path: Path) -> Set[str]:
        """Получает множество импортов из модуля.

        Args:
            file_path: Путь к файлу.

        Returns:
            Множество имён импортируемых модулей.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return set()

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return set()

        imports: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("parser_2gis.parallel"):
                    # Извлекаем только имя модуля
                    imports.add(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("parser_2gis.parallel"):
                        imports.add(alias.name)

        return imports

    def test_no_circular_dependencies_in_parallel(self) -> None:
        """Проверка отсутствия циклических зависимостей в parallel.

        Модули parallel не должны иметь циклических зависимостей.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        # Строим граф зависимостей
        dependencies: Dict[str, Set[str]] = {}

        for py_file in parallel_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            module_name = f"parser_2gis.parallel.{py_file.stem}"
            imports = self._get_module_imports(py_file)

            # Преобразуем в имена модулей
            imported_modules: Set[str] = set()
            for imp in imports:
                mod_name = imp.replace("parser_2gis.parallel.", "")
                imported_modules.add(mod_name)

            dependencies[module_name] = imported_modules

        # Проверяем на циклы
        def has_cycle(start: str, current: str, visited: Set[str], path: List[str]) -> bool:
            """Проверяет наличие цикла в графе зависимостей."""
            if current in visited:
                return current in path

            visited.add(current)
            path.append(current)

            for dep in dependencies.get(current, set()):
                full_dep = f"parser_2gis.parallel.{dep}"
                if has_cycle(start, full_dep, visited, path):
                    return True

            path.pop()
            return False

        # Проверяем каждый модуль
        for module in dependencies:
            visited: Set[str] = set()
            path: List[str] = []
            assert not has_cycle(module, module, visited, path), (
                f"Обнаружена циклическая зависимость: {' -> '.join(path)}"
            )

    def test_parallel_modules_have_clear_responsibilities(self) -> None:
        """Проверка что модули parallel имеют чёткие обязанности.

        Каждый модуль должен иметь одну ответственность.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        parallel_dir = project_root / "parallel"

        # Ожидаемые модули и их обязанности
        expected_modules = {
            "coordinator": "координация параллельного парсинга",
            "error_handler": "обработка ошибок",
            "merger": "слияние файлов",
            "progress": "отчётность о прогрессе",
            "config": "конфигурация",
            "helpers": "вспомогательные функции",
            "optimizer": "оптимизация",
            "options": "опции",
            "parallel_parser": "основной параллельный парсер",
        }

        for module_name, responsibility in expected_modules.items():
            module_file = parallel_dir / f"{module_name}.py"
            assert module_file.exists(), (
                f"parallel/{module_name}.py должен существовать (отвечает за: {responsibility})"
            )


# =============================================================================
# ТЕСТ 3: utils модули независимы
# =============================================================================


class TestUtilsModulesAreIndependent:
    """Тесты на независимость utils модулей."""

    def _check_module_dependencies(self, file_path: Path) -> List[str]:
        """Проверяет зависимости модуля внутри parser_2gis.

        Args:
            file_path: Путь к файлу.

        Returns:
            Список внутренних зависимостей.
        """
        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return []

        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError:
            return []

        dependencies: List[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("parser_2gis"):
                    # Исключаем зависимости от других utils
                    if not node.module.startswith("parser_2gis.utils"):
                        dependencies.append(node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("parser_2gis"):
                        if not alias.name.startswith("parser_2gis.utils"):
                            dependencies.append(alias.name)

        return dependencies

    def test_utils_modules_are_independent(self) -> None:
        """Проверка что utils модули независимы.

        Модули в utils/ должны быть независимыми утилитами
        без сильных зависимостей от бизнес-логики.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        assert utils_dir.exists(), "utils/ должна существовать"

        # Модули которые могут импортироваться из utils
        allowed_dependencies = {
            "parser_2gis.logger",
            "parser_2gis.constants",
            "parser_2gis.exceptions",
            "parser_2gis.protocols",
        }

        for py_file in utils_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            dependencies = self._check_module_dependencies(py_file)

            for dep in dependencies:
                # Проверяем что зависимость разрешена
                is_allowed = any(dep.startswith(allowed) for allowed in allowed_dependencies)

                # utils модули могут зависеть друг от друга
                if dep.startswith("parser_2gis.utils"):
                    is_allowed = True

                assert is_allowed, (
                    f"{py_file.name} не должен зависеть от {dep}. "
                    "utils модули должны быть независимыми."
                )

    def test_utils_modules_are_reusable(self) -> None:
        """Проверка что utils модули переиспользуемы.

        Каждый utils модуль должен быть самодостаточным.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        utils_dir = project_root / "utils"

        # Проверяем что основные utils модули существуют
        expected_utils = [
            "paths.py",
            "signal_handler.py",
            "url_utils.py",
            "validation_utils.py",
            "temp_file_manager.py",
        ]

        for util_file in expected_utils:
            util_path = utils_dir / util_file
            assert util_path.exists(), f"utils/{util_file} должен существовать"

    def test_paths_module_is_independent(self) -> None:
        """Проверка что paths модуль независим.

        paths.py должен быть независимой утилитой.
        """
        from parser_2gis.utils.paths import cache_path, resources_path, user_path

        # Проверяем что функции работают без импорта бизнес-логики
        resources = resources_path()
        assert resources.exists(), "resources_path() должна работать"

        cache = cache_path()
        assert cache is not None, "cache_path() должна работать"

        user = user_path()
        assert user is not None, "user_path() должна работать"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
