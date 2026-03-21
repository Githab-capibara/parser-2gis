"""
Тест для проверки соответствия полей в TUI и моделях конфигурации.

Этот тест предотвращает ошибки, когда TUI обращается к полям,
которые не существуют в соответствующих Pydantic моделях.

Пример предотвращаемой ошибки:
    TUI пытается установить config.parser.timeout, но этого поля нет в ParserOptions.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import ast
import pytest

# Пути к файлам проекта
PROJECT_ROOT = Path(__file__).parent.parent
TUI_SETTINGS_FILE = PROJECT_ROOT / "parser_2gis" / "tui_textual" / "screens" / "settings.py"
CONFIG_FILE = PROJECT_ROOT / "parser_2gis" / "config.py"


class ConfigFieldExtractor:
    """Извлекает обращения к полям конфигурации из TUI кода."""

    # Паттерн для поиска обращений вида config.<section>.<field>
    CONFIG_ACCESS_PATTERN = re.compile(
        r"config\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)"
    )

    def __init__(self, settings_file: Path):
        self.settings_file = settings_file
        self.settings_content = ""
        self.config_accesses: List[Tuple[str, str, int]] = []  # (section, field, line_number)

    def load_settings(self) -> None:
        """Загружает содержимое файла настроек."""
        if not self.settings_file.exists():
            raise FileNotFoundError(f"Файл настроек не найден: {self.settings_file}")

        self.settings_content = self.settings_file.read_text(encoding="utf-8")

    def extract_config_accesses(self) -> List[Tuple[str, str, int]]:
        """
        Извлекает все обращения к config.<section>.<field> из кода.

        Returns:
            Список кортежей (section, field, line_number).
        """
        if not self.settings_content:
            self.load_settings()

        lines = self.settings_content.splitlines()

        for line_num, line in enumerate(lines, start=1):
            # Пропускаем комментарии
            code_line = line.split("#")[0]

            # Ищем все совпадения паттерна
            for match in self.CONFIG_ACCESS_PATTERN.finditer(code_line):
                section = match.group(1)
                field = match.group(2)
                self.config_accesses.append((section, field, line_num))

        return self.config_accesses

    def get_unique_accesses(self) -> Set[Tuple[str, str]]:
        """Возвращает уникальные обращения к полям конфигурации."""
        if not self.config_accesses:
            self.extract_config_accesses()

        return {(section, field) for section, field, _ in self.config_accesses}


class ConfigModelInspector:
    """Инспектирует Pydantic модели конфигурации для проверки наличия полей."""

    # Маппинг секций конфигурации на классы моделей
    SECTION_TO_MODEL = {
        "parser": "ParserOptions",
        "parallel": "ParallelOptions",
        "chrome": "ChromeOptions",
        "writer": "WriterOptions",
        "log": "LogOptions",
    }

    def __init__(self, config_file: Path, project_root: Optional[Path] = None):
        self.config_file = config_file
        self.project_root = project_root or config_file.parent.parent
        self.config_content = ""
        self.model_fields: Dict[str, Set[str]] = {}

    def load_config(self) -> None:
        """Загружает содержимое файла конфигурации."""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Файл конфигурации не найден: {self.config_file}")

        self.config_content = self.config_file.read_text(encoding="utf-8")

    def extract_model_fields(self) -> Dict[str, Set[str]]:
        """
        Извлекает поля из Pydantic моделей с помощью AST парсинга.
        Сканирует все Python файлы в проекте для поиска моделей.

        Returns:
            Словарь {model_name: set of field names}.
        """
        # Сканируем все Python файлы в проекте
        for py_file in self.project_root.rglob("*.py"):
            # Пропускаем тесты, виртуальное окружение, кэш
            if any(
                part.startswith(".") or part in ("venv", "__pycache__", "tests", "htmlcov")
                for part in py_file.parts
            ):
                continue

            try:
                self._extract_from_file(py_file)
            except (SyntaxError, UnicodeDecodeError):
                # Пропускаем файлы с ошибками синтаксиса или кодировки
                continue

        return self.model_fields

    def _extract_from_file(self, file_path: Path) -> None:
        """Извлекает Pydantic модели из одного файла."""
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Проверяем, является ли класс Pydantic моделью
                    if self._is_pydantic_model(node):
                        model_name = node.name
                        fields = self._extract_fields_from_class(node)
                        self.model_fields[model_name] = fields
        except (SyntaxError, UnicodeDecodeError):
            pass

    def _is_pydantic_model(self, class_node: ast.ClassDef) -> bool:
        """Проверяет, наследуется ли класс от BaseModel."""
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
            # Проверяем импортированные имена (например, pydantic.BaseModel)
            if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                return True
        return False

    def _extract_fields_from_class(self, class_node: ast.ClassDef) -> Set[str]:
        """Извлекает имена полей из тела класса."""
        fields = set()

        for item in class_node.body:
            # Аннотированные присваивания (field: Type = default)
            if isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    fields.add(item.target.id)
            # Обычные присваивания (field = value)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        fields.add(target.id)

        return fields

    def get_fields_for_section(self, section: str) -> Set[str]:
        """
        Возвращает набор полей для указанной секции конфигурации.

        Args:
            section: Название секции (parser, parallel, chrome, writer, log).

        Returns:
            Набор имён полей.

        Raises:
            ValueError: Если секция не найдена в маппинге.
        """
        if section not in self.SECTION_TO_MODEL:
            raise ValueError(f"Неизвестная секция конфигурации: {section}")

        model_name = self.SECTION_TO_MODEL[section]

        if not self.model_fields:
            self.extract_model_fields()

        if model_name not in self.model_fields:
            raise ValueError(f"Модель {model_name} не найдена в конфигурации")

        return self.model_fields[model_name]


class TUIConfigFieldValidator:
    """Валидирует соответствие полей TUI моделям конфигурации."""

    def __init__(self, settings_file: Path, config_file: Path, project_root: Optional[Path] = None):
        self.extractor = ConfigFieldExtractor(settings_file)
        self.inspector = ConfigModelInspector(
            config_file, project_root=project_root or settings_file.parent.parent.parent
        )
        self.errors: List[Dict] = []

    def validate(self) -> List[Dict]:
        """
        Выполняет валидацию всех обращений к конфигурации в TUI.

        Returns:
            Список ошибок валидации.
        """
        self.errors = []

        # Извлекаем обращения к конфигурации
        self.extractor.extract_config_accesses()

        # Извлекаем поля из моделей
        self.inspector.extract_model_fields()

        # Проверяем каждое обращение
        for section, field, line_num in self.extractor.config_accesses:
            try:
                valid_fields = self.inspector.get_fields_for_section(section)

                if field not in valid_fields:
                    self.errors.append(
                        {
                            "section": section,
                            "field": field,
                            "line": line_num,
                            "error": f"Поле '{field}' не существует в модели {section}",
                            "available_fields": sorted(valid_fields),
                        }
                    )
            except ValueError as e:
                self.errors.append(
                    {
                        "section": section,
                        "field": field,
                        "line": line_num,
                        "error": str(e),
                        "available_fields": [],
                    }
                )

        return self.errors

    def get_error_report(self) -> str:
        """Генерирует отчёт об ошибках валидации."""
        if not self.errors:
            return "Ошибок не найдено. Все поля TUI соответствуют моделям конфигурации."

        report_lines = [
            "=" * 70,
            "ОТЧЁТ О НЕСООТВЕТСТВИИ ПОЛЕЙ TUI И МОДЕЛЕЙ КОНФИГУРАЦИИ",
            "=" * 70,
            "",
        ]

        for error in self.errors:
            report_lines.append(
                f"❌ Строка {error['line']}: config.{error['section']}.{error['field']}"
            )
            report_lines.append(f"   Ошибка: {error['error']}")

            if error["available_fields"]:
                report_lines.append(f"   Доступные поля: {', '.join(error['available_fields'])}")

            report_lines.append("")

        report_lines.append("=" * 70)
        report_lines.append(f"Всего ошибок: {len(self.errors)}")
        report_lines.append("=" * 70)

        return "\n".join(report_lines)


@pytest.fixture
def settings_file() -> Path:
    """Возвращает путь к файлу настроек TUI."""
    return TUI_SETTINGS_FILE


@pytest.fixture
def config_file() -> Path:
    """Возвращает путь к файлу конфигурации."""
    return CONFIG_FILE


@pytest.fixture
def extractor(settings_file: Path) -> ConfigFieldExtractor:
    """Создаёт экстрактор полей конфигурации."""
    ext = ConfigFieldExtractor(settings_file)
    ext.load_settings()
    return ext


@pytest.fixture
def inspector(config_file: Path, settings_file: Path) -> ConfigModelInspector:
    """Создаёт инспектор моделей конфигурации."""
    insp = ConfigModelInspector(config_file, project_root=settings_file.parent.parent.parent)
    # Не загружаем config, так как теперь сканируем весь проект
    return insp


@pytest.fixture
def validator(settings_file: Path, config_file: Path) -> TUIConfigFieldValidator:
    """Создаёт валидатор полей TUI."""
    return TUIConfigFieldValidator(settings_file, config_file)


class TestConfigFieldExtractor:
    """Тесты для экстрактора полей конфигурации."""

    def test_load_settings_file_not_found(self, tmp_path: Path) -> None:
        """Проверяет обработку несуществующего файла."""
        non_existent = tmp_path / "non_existent.py"
        extractor = ConfigFieldExtractor(non_existent)

        with pytest.raises(FileNotFoundError):
            extractor.load_settings()

    def test_extract_simple_access(self, tmp_path: Path) -> None:
        """Проверяет извлечение простого обращения к конфигурации."""
        test_file = tmp_path / "test_settings.py"
        test_file.write_text("config.parser.timeout = 300\nconfig.parallel.max_workers = 10\n")

        extractor = ConfigFieldExtractor(test_file)
        accesses = extractor.extract_config_accesses()

        assert len(accesses) == 2
        assert ("parser", "timeout", 1) in accesses
        assert ("parallel", "max_workers", 2) in accesses

    def test_extract_multiple_accesses_same_line(self, tmp_path: Path) -> None:
        """Проверяет извлечение нескольких обращений в одной строке."""
        test_file = tmp_path / "test_settings.py"
        test_file.write_text("config.parser.timeout = 300; config.parallel.max_workers = 10\n")

        extractor = ConfigFieldExtractor(test_file)
        accesses = extractor.extract_config_accesses()

        assert len(accesses) == 2

    def test_skip_comments(self, tmp_path: Path) -> None:
        """Проверяет, что комментарии игнорируются."""
        test_file = tmp_path / "test_settings.py"
        test_file.write_text(
            "# config.parser.nonexistent = 100\n"
            "config.parser.timeout = 300  # config.parallel.fake\n"
        )

        extractor = ConfigFieldExtractor(test_file)
        accesses = extractor.extract_config_accesses()

        assert len(accesses) == 1
        assert accesses[0] == ("parser", "timeout", 2)

    def test_get_unique_accesses(self, tmp_path: Path) -> None:
        """Проверяет получение уникальных обращений."""
        test_file = tmp_path / "test_settings.py"
        test_file.write_text(
            "config.parser.timeout = 300\n"
            "config.parser.timeout = 400\n"
            "config.parallel.max_workers = 10\n"
        )

        extractor = ConfigFieldExtractor(test_file)
        unique = extractor.get_unique_accesses()

        assert len(unique) == 2
        assert ("parser", "timeout") in unique
        assert ("parallel", "max_workers") in unique


class TestConfigModelInspector:
    """Тесты для инспектора моделей конфигурации."""

    def test_load_config_file_not_found(self, tmp_path: Path) -> None:
        """Проверяет обработку несуществующего файла конфигурации."""
        non_existent = tmp_path / "non_existent.py"
        inspector = ConfigModelInspector(non_existent, project_root=tmp_path)

        with pytest.raises(FileNotFoundError):
            inspector.load_config()

    def test_extract_pydantic_model_fields(self, tmp_path: Path) -> None:
        """Проверяет извлечение полей из Pydantic модели."""
        test_config = tmp_path / "test_config.py"
        test_config.write_text(
            "from pydantic import BaseModel\n"
            "\n"
            "class TestOptions(BaseModel):\n"
            "    field1: int = 10\n"
            "    field2: str = 'default'\n"
            "    field3: bool = True\n"
        )

        inspector = ConfigModelInspector(test_config, project_root=tmp_path)
        # Временно добавляем маппинг для теста
        inspector.SECTION_TO_MODEL["test"] = "TestOptions"

        fields = inspector.extract_model_fields()

        assert "TestOptions" in fields
        assert fields["TestOptions"] == {"field1", "field2", "field3"}

    def test_get_fields_for_section_unknown(self, tmp_path: Path) -> None:
        """Проверяет обработку неизвестной секции."""
        test_config = tmp_path / "test_config.py"
        test_config.write_text("pass\n")

        inspector = ConfigModelInspector(test_config, project_root=tmp_path)

        with pytest.raises(ValueError, match="Неизвестная секция"):
            inspector.get_fields_for_section("unknown_section")


class TestTUIConfigFieldValidator:
    """Тесты для валидатора полей TUI."""

    def test_validator_no_errors(self, tmp_path: Path) -> None:
        """Проверяет валидацию без ошибок."""
        test_settings = tmp_path / "test_settings.py"
        test_settings.write_text("config.parser.timeout = 300\nconfig.parallel.max_workers = 10\n")

        test_config = tmp_path / "test_config.py"
        test_config.write_text(
            "from pydantic import BaseModel\n"
            "\n"
            "class ParserOptions(BaseModel):\n"
            "    timeout: int = 300\n"
            "\n"
            "class ParallelOptions(BaseModel):\n"
            "    max_workers: int = 10\n"
        )

        validator = TUIConfigFieldValidator(test_settings, test_config, project_root=tmp_path)
        errors = validator.validate()

        assert len(errors) == 0

    def test_validator_with_errors(self, tmp_path: Path) -> None:
        """Проверяет валидацию с ошибками."""
        test_settings = tmp_path / "test_settings.py"
        test_settings.write_text(
            "config.parser.nonexistent_field = 100\nconfig.parser.timeout = 300\n"
        )

        test_config = tmp_path / "test_config.py"
        test_config.write_text(
            "from pydantic import BaseModel\n"
            "\n"
            "class ParserOptions(BaseModel):\n"
            "    timeout: int = 300\n"
            "    existing_field: str = 'test'\n"
        )

        validator = TUIConfigFieldValidator(test_settings, test_config, project_root=tmp_path)
        errors = validator.validate()

        assert len(errors) == 1
        assert errors[0]["field"] == "nonexistent_field"
        assert "timeout" in errors[0]["available_fields"]

    def test_validator_error_report(self, tmp_path: Path) -> None:
        """Проверяет генерацию отчёта об ошибках."""
        test_settings = tmp_path / "test_settings.py"
        test_settings.write_text("config.parser.fake_field = 100\n")

        test_config = tmp_path / "test_config.py"
        test_config.write_text(
            "from pydantic import BaseModel\n"
            "\n"
            "class ParserOptions(BaseModel):\n"
            "    timeout: int = 300\n"
        )

        validator = TUIConfigFieldValidator(test_settings, test_config, project_root=tmp_path)
        validator.validate()
        report = validator.get_error_report()

        assert "fake_field" in report
        assert "timeout" in report
        assert "Всего ошибок: 1" in report


class TestRealTUIConfigFields:
    """
    Интеграционные тесты для проверки реальных полей TUI.

    Эти тесты запускаются только если файлы существуют.
    """

    @pytest.fixture(autouse=True)
    def skip_if_files_missing(self, settings_file: Path, config_file: Path) -> None:
        """Пропускает тесты, если файлы не найдены."""
        if not settings_file.exists():
            pytest.skip(f"Файл настроек не найден: {settings_file}")
        if not config_file.exists():
            pytest.skip(f"Файл конфигурации не найден: {config_file}")

    def test_all_tui_fields_exist_in_models(self, validator: TUIConfigFieldValidator) -> None:
        """
        Главный тест: проверяет, что все поля, к которым обращается TUI,
        существуют в соответствующих Pydantic моделях.

        Raises:
            AssertionError: Если найдены несоответствия полей.
        """
        errors = validator.validate()

        if errors:
            error_report = validator.get_error_report()
            raise AssertionError(
                f"Обнаружены несоответствия полей TUI и моделей конфигурации:\n\n{error_report}"
            )

    def test_extractor_finds_all_config_accesses(self, extractor: ConfigFieldExtractor) -> None:
        """Проверяет, что экстрактор находит все обращения к конфигурации."""
        accesses = extractor.get_unique_accesses()

        # Должны быть найдены обращения к различным секциям
        sections_found = {section for section, _ in accesses}

        # Проверяем, что найдены хотя бы некоторые секции
        assert len(accesses) > 0, "Не найдено ни одного обращения к конфигурации"
        assert (
            "parser" in sections_found or "chrome" in sections_found or "writer" in sections_found
        ), "Не найдены обращения к основным секциям конфигурации"

    def test_inspector_extracts_model_fields(self, inspector: ConfigModelInspector) -> None:
        """Проверяет, что инспектор извлекает поля из моделей."""
        fields = inspector.extract_model_fields()

        found_models = set(fields.keys())

        # Хотя бы некоторые модели должны быть найдены
        assert len(found_models) > 0, "Не найдено ни одной Pydantic модели"

        # Проверяем, что у моделей есть поля
        for model_name, model_fields in fields.items():
            assert len(model_fields) > 0, f"Модель {model_name} не имеет полей"

    def test_specific_parser_fields_exist(self, inspector: ConfigModelInspector) -> None:
        """
        Проверяет наличие конкретных полей в ParserOptions.

        Этот тест предотвращает регрессию полей, которые используются в TUI.
        """
        parser_fields = inspector.get_fields_for_section("parser")

        # Поля, которые используются в TUI settings.py
        required_fields = {"max_records", "delay_between_clicks", "max_retries", "timeout"}

        missing = required_fields - parser_fields

        assert not missing, (
            f"В ParserOptions отсутствуют поля, используемые в TUI: {missing}. "
            f"Доступные поля: {sorted(parser_fields)}"
        )

    def test_specific_parallel_fields_exist(self, inspector: ConfigModelInspector) -> None:
        """
        Проверяет наличие конкретных полей в ParallelOptions.

        Этот тест предотвращает регрессию полей, которые используются в TUI.
        """
        parallel_fields = inspector.get_fields_for_section("parallel")

        # Поля, которые используются в TUI settings.py
        required_fields = {"max_workers"}

        missing = required_fields - parallel_fields

        assert not missing, (
            f"В ParallelOptions отсутствуют поля, используемые в TUI: {missing}. "
            f"Доступные поля: {sorted(parallel_fields)}"
        )

    def test_specific_chrome_fields_exist(self, inspector: ConfigModelInspector) -> None:
        """
        Проверяет наличие конкретных полей в ChromeOptions.

        Этот тест предотвращает регрессию полей, которые используются в TUI.
        """
        chrome_fields = inspector.get_fields_for_section("chrome")

        # Поля, которые используются в TUI settings.py
        required_fields = {
            "headless",
            "disable_images",
            "silent_browser",
            "memory_limit",
            "startup_delay",
        }

        missing = required_fields - chrome_fields

        assert not missing, (
            f"В ChromeOptions отсутствуют поля, используемые в TUI: {missing}. "
            f"Доступные поля: {sorted(chrome_fields)}"
        )

    def test_specific_writer_fields_exist(self, inspector: ConfigModelInspector) -> None:
        """
        Проверяет наличие конкретных полей в WriterOptions.

        Этот тест предотвращает регрессию полей, которые используются в TUI.
        """
        writer_fields = inspector.get_fields_for_section("writer")

        # Поля, которые используются в TUI settings.py
        required_fields = {"encoding"}

        missing = required_fields - writer_fields

        assert not missing, (
            f"В WriterOptions отсутствуют поля, используемые в TUI: {missing}. "
            f"Доступные поля: {sorted(writer_fields)}"
        )


if __name__ == "__main__":
    # Запуск тестов через pytest
    pytest.main([__file__, "-v"])
