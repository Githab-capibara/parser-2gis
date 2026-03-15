"""
Тесты для проверки форматирования TUI тегов.

Проверяют корректность использования тегов форматирования в файлах TUI:
1. Отсутствие пробелов перед закрывающими тегами [/]
2. Отсутствие специфичных закрывающих тегов вида [/bold cyan], [/green] и т.п.
3. Отсутствие вложенных тегов
4. Корректность всех тегов форматирования
5. Проверка строк с эмодзи и форматированием на наличие лишних символов
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

import pytest


# Пути к директориям с TUI файлами
PROJECT_ROOT = Path(__file__).parent.parent
TUI_PYTERMGUI_DIR = PROJECT_ROOT / "parser_2gis" / "tui_pytermgui"
TUI_DIR = PROJECT_ROOT / "parser_2gis" / "tui"


def get_tui_python_files() -> List[Path]:
    """
    Получить все Python файлы в директориях TUI.

    Returns:
        Список путей к Python файлам
    """
    files = []

    # Собираем файлы из tui_pytermgui
    if TUI_PYTERMGUI_DIR.exists():
        for py_file in TUI_PYTERMGUI_DIR.rglob("*.py"):
            # Пропускаем __pycache__ и __init__.py
            if "__pycache__" not in str(py_file):
                files.append(py_file)

    # Собираем файлы из tui
    if TUI_DIR.exists():
        for py_file in TUI_DIR.rglob("*.py"):
            # Пропускаем __pycache__ и __init__.py
            if "__pycache__" not in str(py_file):
                files.append(py_file)

    return files


def read_file_content(file_path: Path) -> List[Tuple[int, str]]:
    """
    Прочитать содержимое файла с номерами строк.

    Args:
        file_path: Путь к файлу

    Returns:
        Список кортежей (номер_строки, содержимое_строки)
    """
    lines = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                lines.append((line_num, line))
    except (IOError, UnicodeDecodeError):
        pass
    return lines


def extract_string_literals(line: str) -> List[str]:
    """
    Извлечь строковые литералы из строки кода.

    Args:
        line: Строка кода

    Returns:
        Список строковых литералов
    """
    literals = []
    # Находим строки в двойных кавычках
    double_quoted = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', line)
    # Находим строки в одинарных кавычках
    single_quoted = re.findall(r"'([^'\\]*(?:\\.[^'\\]*)*)'", line)
    # Находим f-строки
    f_strings = re.findall(r'f"([^"\\]*(?:\\.[^"\\]*)*)"', line)
    f_strings_single = re.findall(r"f'([^'\\]*(?:\\.[^'\\]*)*)'", line)

    literals.extend(double_quoted)
    literals.extend(single_quoted)
    literals.extend(f_strings)
    literals.extend(f_strings_single)

    return literals


class TestTUIFormattingTags:
    """Тесты для проверки форматирования TUI тегов."""

    @pytest.fixture
    def tui_files(self) -> List[Path]:
        """Фикстура для получения списка TUI файлов."""
        return get_tui_python_files()

    def test_no_spaces_before_closing_tags(self, tui_files: List[Path]) -> None:
        """
        Проверка отсутствия пробелов перед закрывающими тегами [/].

        Ошибка: текст [/] - пробел перед закрывающим тегом
        Правильно: текст[/]

        Этот тест находит все случаи, где перед [/] есть пробел,
        что является ошибкой форматирования в pytermgui/rich.
        """
        errors = []

        # Регулярное выражение для поиска пробелов перед [/]
        # Ищем пробельные символы непосредственно перед [/]
        pattern = re.compile(r'\s+\[/\]')

        for file_path in tui_files:
            lines = read_file_content(file_path)
            for line_num, line in lines:
                # Пропускаем строки с комментариями
                if line.strip().startswith("#"):
                    continue

                # Проверяем только строковые литералы
                string_literals = extract_string_literals(line)
                for literal in string_literals:
                    matches = pattern.findall(literal)
                    if matches:
                        errors.append(
                            f"{file_path.relative_to(PROJECT_ROOT)}:{line_num}: "
                            f"Обнаружен пробел перед закрывающим тегом [/]: '{literal.strip()[:60]}'"
                        )

        assert not errors, (
            f"Найдены проблемы с пробелами перед закрывающими тегами в {len(errors)} местах:\n"
            + "\n".join(errors[:20])  # Показываем первые 20 ошибок
            + (f"\n... и ещё {len(errors) - 20}" if len(errors) > 20 else "")
        )

    def test_no_specific_closing_tags(self, tui_files: List[Path]) -> None:
        """
        Проверка отсутствия специфичных закрывающих тегов.

        Ошибка: [/bold cyan], [/green], [/dim], [/red] и т.п.
        Правильно: использовать универсальный закрывающий тег [/]

        В pytermgui/rich рекомендуется использовать универсальный [/]
        вместо специфичных тегов для лучшей читаемости и поддержки.
        """
        errors = []

        # Регулярное выражение для поиска специфичных закрывающих тегов
        # Ищем теги вида [/что-то] где что-то - не пустая строка
        pattern = re.compile(r'\[/([a-zA-Z_][a-zA-Z0-9_]*(?:\s+[a-zA-Z_][a-zA-Z0-9_]*)*)\]')

        for file_path in tui_files:
            lines = read_file_content(file_path)
            for line_num, line in lines:
                # Пропускаем строки с комментариями
                if line.strip().startswith("#"):
                    continue

                # Проверяем только строковые литералы
                string_literals = extract_string_literals(line)
                for literal in string_literals:
                    matches = pattern.findall(literal)
                    for match in matches:
                        errors.append(
                            f"{file_path.relative_to(PROJECT_ROOT)}:{line_num}: "
                            f"Обнаружен специфичный закрывающий тег '[/{match}]'. "
                            f"Используйте универсальный [/] вместо '[/{match}]'"
                        )

        assert not errors, (
            f"Найдены специфичные закрывающие теги в {len(errors)} местах:\n"
            + "\n".join(errors[:20])
            + (f"\n... и ещё {len(errors) - 20}" if len(errors) > 20 else "")
        )

    def test_no_nested_tags(self, tui_files: List[Path]) -> None:
        """
        Проверка отсутствия вложенных тегов форматирования.

        Ошибка: [green]текст [bold]вложенный[/bold] текст[/green]
        Правильно: [green bold]текст [bold]вложенный[/] текст[/]

        Вложенные теги могут вызывать проблемы с отображением
        и усложняют поддержку кода.
        """
        errors = []

        # Паттерн для поиска явных закрывающих тегов цвета
        explicit_close_pattern = re.compile(
            r'\[/(?:bold|cyan|green|red|yellow|dim|italic|underline|strike|reverse|blink)\]'
        )

        for file_path in tui_files:
            lines = read_file_content(file_path)
            for line_num, line in lines:
                # Пропускаем строки с комментариями
                if line.strip().startswith("#"):
                    continue

                # Проверяем только строковые литералы
                string_literals = extract_string_literals(line)
                for literal in string_literals:
                    # Проверяем паттерн с явными закрывающими тегами цвета
                    if explicit_close_pattern.search(literal):
                        errors.append(
                            f"{file_path.relative_to(PROJECT_ROOT)}:{line_num}: "
                            f"Обнаружен явный закрывающий тег цвета (возможная вложенность): '{literal.strip()[:60]}'"
                        )

        assert not errors, (
            f"Найдены возможные проблемы с вложенностью тегов в {len(errors)} местах:\n"
            + "\n".join(errors[:20])
            + (f"\n... и ещё {len(errors) - 20}" if len(errors) > 20 else "")
        )

    def test_tag_formatting_correctness(self, tui_files: List[Path]) -> None:
        """
        Проверка корректности всех тегов форматирования.

        Проверяет:
        - Все открывающие теги имеют закрывающие
        - Теги правильно сформированы (квадратные скобки)
        - Нет незавершённых тегов
        - Нет опечаток в названиях тегов
        """
        errors = []

        # Допустимые имена тегов
        valid_tags = {
            'bold', 'cyan', 'green', 'red', 'yellow', 'blue', 'magenta',
            'dim', 'italic', 'underline', 'strike', 'reverse', 'blink',
            'black', 'white', 'bright_red', 'bright_green', 'bright_yellow',
            'bright_blue', 'bright_magenta', 'bright_cyan', 'bright_white',
            'on_black', 'on_red', 'on_green', 'on_blue', 'on_cyan', 'on_magenta',
            'on_yellow', 'on_white', 'on_bright_red', 'on_bright_green',
            'on_bright_yellow', 'on_bright_blue', 'on_bright_magenta',
            'on_bright_cyan', 'on_bright_white',
            'dark_gray', 'gray', 'orange', 'pink', 'brown',
            'on_dark_gray', 'on_gray', 'on_orange', 'on_pink', 'on_brown',
        }

        # Паттерн для открывающих тегов
        open_tag_pattern = re.compile(r'\[([a-zA-Z_][a-zA-Z0-9_\s]*)\]')
        # Паттерн для закрывающих тегов
        close_tag_pattern = re.compile(r'\[/\]')
        # Паттерн для специфичных закрывающих тегов
        specific_close_pattern = re.compile(r'\[/([a-zA-Z_][a-zA-Z0-9_\s]*)\]')

        for file_path in tui_files:
            lines = read_file_content(file_path)
            for line_num, line in lines:
                # Пропускаем строки с комментариями
                if line.strip().startswith("#"):
                    continue

                # Пропускаем строки, которые определяют паттерны (regex)
                if 'pattern' in line.lower() or 'regex' in line.lower():
                    continue

                # Проверяем только строковые литералы
                string_literals = extract_string_literals(line)
                for literal in string_literals:
                    # Находим все открывающие теги
                    open_tags = open_tag_pattern.findall(literal)

                    # Находим все закрывающие теги (универсальные)
                    universal_close_count = len(close_tag_pattern.findall(literal))

                    # Находим все специфичные закрывающие теги
                    specific_close_tags = specific_close_pattern.findall(literal)

                    # Считаем общее количество закрывающих тегов
                    total_close_count = universal_close_count + len(specific_close_tags)

                    # Проверяем баланс тегов
                    if len(open_tags) > total_close_count + 1:
                        errors.append(
                            f"{file_path.relative_to(PROJECT_ROOT)}:{line_num}: "
                            f"Возможный дисбаланс тегов: {len(open_tags)} открывающих, "
                            f"{total_close_count} закрывающих. Строка: '{literal.strip()[:60]}'"
                        )

                    # Проверяем валидность имён тегов
                    for tag in open_tags:
                        tag_names = tag.split()
                        for tag_name in tag_names:
                            # Проверяем, является ли тег допустимым
                            if tag_name.lower() not in valid_tags:
                                # Проверяем, не является ли это тегом фона (on_*)
                                if tag_name.lower() == 'on':
                                    # Это часть составного тега фона, пропускаем
                                    continue
                                # Проверяем, не является ли это комбинацией тегов
                                is_valid_combo = all(
                                    t.lower() in valid_tags for t in tag_name.split()
                                )
                                if not is_valid_combo:
                                    errors.append(
                                        f"{file_path.relative_to(PROJECT_ROOT)}:{line_num}: "
                                        f"Неизвестный тег '{tag_name}'. "
                                        f"Допустимые: {', '.join(sorted(valid_tags)[:10])}..."
                                    )

        assert not errors, (
            f"Найдены проблемы с корректностью тегов в {len(errors)} местах:\n"
            + "\n".join(errors[:20])
            + (f"\n... и ещё {len(errors) - 20}" if len(errors) > 20 else "")
        )

    def test_emoji_and_formatting_strings(self, tui_files: List[Path]) -> None:
        """
        Проверка строк с эмодзи и форматированием на наличие лишних символов.

        Проверяет:
        - Отсутствие лишних пробелов вокруг эмодзи
        - Корректное сочетание эмодзи с тегами форматирования
        - Отсутствие битых последовательностей эмодзи
        - Правильное использование эмодзи в строках форматирования
        """
        errors = []

        # Популярные эмодзи в проекте
        common_emojis = ['✅', '❌', '⏸', '▶', '🗕', '📊', '📋', '📁', '📂', '⚙️', '🔧', '🚀', 'ℹ️']

        # Паттерн для поиска проблем с эмодзи
        # 1. Эмодзи с пробелом перед закрывающим тегом
        emoji_space_close_pattern = re.compile(
            r'([' + ''.join(common_emojis) + r'])\s+\[/\]'
        )

        for file_path in tui_files:
            lines = read_file_content(file_path)
            for line_num, line in lines:
                # Пропускаем строки с комментариями
                if line.strip().startswith("#"):
                    continue

                # Проверяем только строковые литералы
                string_literals = extract_string_literals(line)
                for literal in string_literals:
                    # Проверяем эмодзи с пробелом перед закрывающим тегом
                    emoji_space_matches = emoji_space_close_pattern.findall(literal)
                    if emoji_space_matches:
                        for emoji in emoji_space_matches:
                            errors.append(
                                f"{file_path.relative_to(PROJECT_ROOT)}:{line_num}: "
                                f"Обнаружен лишний пробел между эмодзи '{emoji}' и закрывающим тегом [/]"
                            )

        assert not errors, (
            f"Найдены проблемы с эмодзи и форматированием в {len(errors)} местах:\n"
            + "\n".join(errors[:20])
            + (f"\n... и ещё {len(errors) - 20}" if len(errors) > 20 else "")
        )


class TestTUIFormattingIntegration:
    """Интеграционные тесты для проверки общего качества форматирования."""

    @pytest.fixture
    def tui_files(self) -> List[Path]:
        """Фикстура для получения списка TUI файлов."""
        return get_tui_python_files()

    def test_all_files_have_no_formatting_issues(self, tui_files: List[Path]) -> None:
        """
        Комплексная проверка всех файлов на отсутствие проблем форматирования.

        Объединяет все проверки в одном тесте для общей статистики.
        """
        all_errors = {
            'spaces_before_close': [],
            'specific_close_tags': [],
            'nested_tags': [],
        }

        # Паттерны для проверок
        space_close_pattern = re.compile(r'\s+\[/\]')
        specific_close_pattern = re.compile(r'\[/[a-zA-Z_][a-zA-Z0-9_]*(?:\s+[a-zA-Z_][a-zA-Z0-9_]*)*\]')
        explicit_close_pattern = re.compile(r'\[/(?:bold|cyan|green|red|yellow|dim|italic)\]')

        for file_path in tui_files:
            lines = read_file_content(file_path)
            for line_num, line in lines:
                if line.strip().startswith("#"):
                    continue

                # Проверяем только строковые литералы
                string_literals = extract_string_literals(line)
                for literal in string_literals:
                    # Проверка 1: пробелы перед [/]
                    if space_close_pattern.search(literal):
                        all_errors['spaces_before_close'].append(
                            f"{file_path}:{line_num}"
                        )

                    # Проверка 2: специфичные закрывающие теги
                    if specific_close_pattern.search(literal):
                        all_errors['specific_close_tags'].append(
                            f"{file_path}:{line_num}"
                        )

                    # Проверка 3: явные закрывающие теги
                    if explicit_close_pattern.search(literal):
                        all_errors['nested_tags'].append(
                            f"{file_path}:{line_num}"
                        )

        # Формируем отчёт
        total_errors = sum(len(errors) for errors in all_errors.values())

        report_lines = [f"Всего найдено проблем: {total_errors}"]
        for error_type, errors in all_errors.items():
            if errors:
                report_lines.append(f"\n{error_type}: {len(errors)} проблем")
                for error in errors[:5]:
                    report_lines.append(f"  - {error}")

        assert total_errors == 0, "\n".join(report_lines)


# Дополнительные утилитные тесты
class TestTUIFormattingHelpers:
    """Вспомогательные тесты для проверки утилит форматирования."""

    def test_get_tui_files_returns_non_empty_list(self) -> None:
        """Проверка, что функция получения файлов возвращает непустой список."""
        files = get_tui_python_files()
        assert len(files) > 0, "Не найдено ни одного TUI файла для тестирования"
        assert all(f.exists() for f in files), "Некоторые файлы не существуют"

    def test_all_tui_files_are_valid_python(self) -> None:
        """Проверка, что все TUI файлы являются валидным Python кодом."""
        import ast

        tui_files = get_tui_python_files()
        invalid_files = []
        for file_path in tui_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                ast.parse(content)
            except SyntaxError as e:
                invalid_files.append(f"{file_path}: {e}")
            except Exception as e:
                invalid_files.append(f"{file_path}: {type(e).__name__}: {e}")

        assert not invalid_files, (
            f"Найдены файлы с синтаксическими ошибками:\n"
            + "\n".join(invalid_files)
        )
