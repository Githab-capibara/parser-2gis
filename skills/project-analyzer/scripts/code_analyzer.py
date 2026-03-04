#!/usr/bin/env python3
"""
Скрипт для статического анализа кода.

Использование:
    python code_analyzer.py <path> [options]

Анализирует код на:
- Логические ошибки
- Синтаксические ошибки
- Уязвимости безопасности
- Нарушения стиля
"""

import ast
import re
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class IssueSeverity(Enum):
    """Уровень серьёзности проблемы."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CodeIssue:
    """Проблема в коде."""
    file: str
    line: int
    column: int
    message: str
    severity: IssueSeverity
    issue_type: str


class CodeAnalyzer:
    """Анализатор кода для Python файлов."""
    
    def __init__(self):
        self.issues: List[CodeIssue] = []
        
        # Паттерны для поиска уязвимостей
        self.security_patterns = [
            (r'eval\s*\(', 'Использование eval() опасно'),
            (r'exec\s*\(', 'Использование exec() опасно'),
            (r'__import__\s*\(', 'Использование __import__() опасно'),
            (r'pickle\.loads?\s*\(', 'Использование pickle может быть опасно'),
            (r'yaml\.load\s*\([^)]*\)', 'Использование yaml.load() без Loader опасно'),
            (r'os\.system\s*\(', 'Использование os.system() может быть опасно'),
            (r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True', 
             'subprocess с shell=True может быть опасно'),
            (r'password\s*=\s*["\'][^"\']+["\']', 'Хардкод пароля'),
            (r'secret\s*=\s*["\'][^"\']+["\']', 'Хардкод секрета'),
            (r'token\s*=\s*["\'][^"\']+["\']', 'Хардкод токена'),
            (r'api_key\s*=\s*["\'][^"\']+["\']', 'Хардкод API ключа'),
        ]
        
        # Паттерны для поиска проблем стиля
        self.style_patterns = [
            (r'^#(?! )', 'Комментарий без пробела после #'),
            (r'\s+$', 'Лишние пробелы в конце строки'),
            (r'\t', 'Использование табов вместо пробелов'),
        ]
    
    def analyze_file(self, file_path: Path) -> List[CodeIssue]:
        """
        Анализировать файл.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Список найденных проблем
        """
        self.issues = []
        
        if not file_path.exists():
            return [CodeIssue(
                file=str(file_path),
                line=0,
                column=0,
                message="Файл не найден",
                severity=IssueSeverity.ERROR,
                issue_type="file_error"
            )]
        
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            return [CodeIssue(
                file=str(file_path),
                line=0,
                column=0,
                message=f"Ошибка чтения файла: {e}",
                severity=IssueSeverity.ERROR,
                issue_type="file_error"
            )]
        
        # Синтаксический анализ
        self._check_syntax(content, str(file_path))
        
        # Проверка безопасности
        self._check_security(content, str(file_path))
        
        # Проверка стиля
        self._check_style(content, str(file_path))
        
        # Логический анализ (для Python)
        if file_path.suffix == '.py':
            self._check_logic(content, str(file_path))
        
        return self.issues
    
    def _check_syntax(self, content: str, file_path: str):
        """Проверить синтаксис."""
        try:
            ast.parse(content)
        except SyntaxError as e:
            self.issues.append(CodeIssue(
                file=file_path,
                line=e.lineno or 0,
                column=e.offset or 0,
                message=f"Синтаксическая ошибка: {e.msg}",
                severity=IssueSeverity.ERROR,
                issue_type="syntax_error"
            ))
    
    def _check_security(self, content: str, file_path: str):
        """Проверить на уязвимости безопасности."""
        lines = content.split('\n')
        
        for pattern, message in self.security_patterns:
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    self.issues.append(CodeIssue(
                        file=file_path,
                        line=line_num,
                        column=0,
                        message=message,
                        severity=IssueSeverity.WARNING,
                        issue_type="security"
                    ))
    
    def _check_style(self, content: str, file_path: str):
        """Проверить стиль кода."""
        lines = content.split('\n')
        
        for pattern, message in self.style_patterns:
            for line_num, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    self.issues.append(CodeIssue(
                        file=file_path,
                        line=line_num,
                        column=0,
                        message=message,
                        severity=IssueSeverity.INFO,
                        issue_type="style"
                    ))
    
    def _check_logic(self, content: str, file_path: str):
        """
        Проверить логические ошибки.
        
        Анализирует AST для поиска потенциальных проблем.
        """
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return  # Синтаксические ошибки уже зафиксированы
        
        for node in ast.walk(tree):
            # Проверка на бесконечные циклы
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    # while True без break
                    has_break = any(
                        isinstance(n, ast.Break)
                        for n in ast.walk(node)
                    )
                    if not has_break:
                        self.issues.append(CodeIssue(
                            file=file_path,
                            line=node.lineno,
                            column=0,
                            message="Возможный бесконечный цикл while True без break",
                            severity=IssueSeverity.WARNING,
                            issue_type="logic"
                        ))
            
            # Проверка на пустые except
            if isinstance(node, ast.ExceptHandler):
                if not node.body:
                    self.issues.append(CodeIssue(
                        file=file_path,
                        line=node.lineno,
                        column=0,
                        message="Пустой обработчик исключений",
                        severity=IssueSeverity.ERROR,
                        issue_type="logic"
                    ))
                
                # Проверка на bare except
                if node.type is None:
                    self.issues.append(CodeIssue(
                        file=file_path,
                        line=node.lineno,
                        column=0,
                        message="Используйте конкретный тип исключения вместо bare except",
                        severity=IssueSeverity.WARNING,
                        issue_type="logic"
                    ))
            
            # Проверка на присваивание в условии
            if isinstance(node, ast.If):
                # Это упрощённая проверка, реальная требует более сложного анализа
                pass
    
    def report(self, format: str = 'text') -> str:
        """
        Сформировать отчёт.
        
        Args:
            format: Формат отчёта (text, json)
            
        Returns:
            Отчёт в виде строки
        """
        if format == 'json':
            import json
            return json.dumps([
                {
                    'file': issue.file,
                    'line': issue.line,
                    'column': issue.column,
                    'message': issue.message,
                    'severity': issue.severity.value,
                    'issue_type': issue.issue_type
                }
                for issue in self.issues
            ], indent=2, ensure_ascii=False)
        
        # Текстовый формат
        if not self.issues:
            return "Проблем не найдено ✓"
        
        lines = [f"Найдено проблем: {len(self.issues)}"]
        
        # Группировка по серьёзности
        by_severity = {}
        for issue in self.issues:
            if issue.severity not in by_severity:
                by_severity[issue.severity] = []
            by_severity[issue.severity].append(issue)
        
        for severity in [IssueSeverity.CRITICAL, IssueSeverity.ERROR, 
                        IssueSeverity.WARNING, IssueSeverity.INFO]:
            if severity in by_severity:
                for issue in by_severity[severity]:
                    icon = {'critical': '🔴', 'error': '❌', 
                           'warning': '⚠️', 'info': 'ℹ️'}[severity.value]
                    lines.append(
                        f"{icon} [{severity.value.upper()}] "
                        f"{issue.file}:{issue.line}:{issue.column} - {issue.message}"
                    )
        
        return '\n'.join(lines)


def analyze_directory(dir_path: Path, pattern: str = '*.py') -> Dict[str, List[CodeIssue]]:
    """
    Анализировать директорию.
    
    Args:
        dir_path: Путь к директории
        pattern: Глоб-паттерн для файлов
        
    Returns:
        Словарь {файл: проблемы}
    """
    analyzer = CodeAnalyzer()
    results = {}
    
    files = list(dir_path.rglob(pattern))
    
    for file_path in files:
        if '__pycache__' in str(file_path):
            continue
        
        issues = analyzer.analyze_file(file_path)
        if issues:
            results[str(file_path)] = issues
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Статический анализ кода'
    )
    parser.add_argument(
        'path',
        help='Путь к файлу или директории'
    )
    parser.add_argument(
        '--pattern',
        default='*.py',
        help='Глоб-паттерн для файлов (по умолчанию *.py)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['text', 'json'],
        default='text',
        help='Формат вывода'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Рекурсивный анализ директории'
    )
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"Ошибка: путь не найден: {path}", file=sys.stderr)
        sys.exit(1)
    
    analyzer = CodeAnalyzer()
    
    if path.is_file():
        issues = analyzer.analyze_file(path)
        print(analyzer.report(format=args.format))
    elif path.is_dir():
        if args.recursive:
            results = analyze_directory(path, args.pattern)
            if results:
                for file_path, issues in results.items():
                    print(f"\n{file_path}:")
                    analyzer.issues = issues
                    print(analyzer.report(format=args.format))
            else:
                print("Проблем не найдено ✓")
        else:
            # Только файлы в корневой директории
            for file_path in path.glob(args.pattern):
                if file_path.is_file():
                    issues = analyzer.analyze_file(file_path)
                    if issues:
                        print(f"\n{file_path}:")
                        analyzer.issues = issues
                        print(analyzer.report(format=args.format))
    else:
        print(f"Ошибка: неверный путь: {path}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
