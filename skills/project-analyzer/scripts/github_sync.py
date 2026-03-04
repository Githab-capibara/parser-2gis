#!/usr/bin/env python3
"""
Скрипт для синхронизации изменений с GitHub.

Использование:
    python github_sync.py <action> [options]

Действия:
    status - проверить статус изменений
    add - добавить файлы
    commit - сделать коммит
    push - отправить изменения
    sync - полная синхронизация (add + commit + push)
"""

import subprocess
import sys
import argparse
from pathlib import Path


class GitHubSync:
    """Класс для синхронизации с GitHub."""
    
    def __init__(self, repo_path: str = None, timeout_ms: int = 300000):
        """
        Инициализировать синхронизатор.
        
        Args:
            repo_path: Путь к репозиторию (по умолчанию текущая директория)
            timeout_ms: Таймаут для команд в миллисекундах
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.timeout_sec = timeout_ms / 1000.0
    
    def run_command(self, command: str) -> tuple[bool, str, str]:
        """
        Выполнить git команду.
        
        Args:
            command: Команда для выполнения
            
        Returns:
            Кортеж (успех, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                encoding='utf-8',
                errors='replace'
            )
            return (
                result.returncode == 0,
                result.stdout,
                result.stderr
            )
        except subprocess.TimeoutExpired:
            return (
                False,
                "",
                f"Превышен таймаут {self.timeout_sec} сек"
            )
        except Exception as e:
            return False, "", str(e)
    
    def status(self) -> bool:
        """Проверить статус изменений."""
        print("Проверка статуса изменений...")
        success, stdout, stderr = self.run_command("git status")
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        return success
    
    def add(self, files: str = ".") -> bool:
        """
        Добавить файлы.
        
        Args:
            files: Файлы для добавления (по умолчанию все)
        """
        print(f"Добавление файлов: {files}")
        success, stdout, stderr = self.run_command(f"git add {files}")
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        return success
    
    def commit(self, message: str) -> bool:
        """
        Сделать коммит.
        
        Args:
            message: Сообщение коммита
        """
        print(f"Создание коммита: {message}")
        success, stdout, stderr = self.run_command(
            f'git commit -m "{message}"'
        )
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        return success
    
    def push(self, remote: str = "origin", branch: str = None) -> bool:
        """
        Отправить изменения.
        
        Args:
            remote: Удалённый репозиторий
            branch: Ветка (по умолчанию текущая)
        """
        branch_part = f"{remote} {branch}" if branch else remote
        print(f"Отправка изменений в {branch_part}...")
        success, stdout, stderr = self.run_command(
            f"git push {branch_part}"
        )
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        return success
    
    def diff(self) -> bool:
        """Показать изменения."""
        print("Изменения в рабочей директории:")
        success, stdout, stderr = self.run_command("git diff HEAD")
        if stdout:
            print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        return success
    
    def sync(self, message: str, files: str = ".") -> bool:
        """
        Полная синхронизация.
        
        Args:
            message: Сообщение коммита
            files: Файлы для добавления
        """
        print("Начало синхронизации...")
        
        if not self.add(files):
            print("Ошибка при добавлении файлов")
            return False
        
        if not self.commit(message):
            print("Ошибка при создании коммита")
            return False
        
        if not self.push():
            print("Ошибка при отправке изменений")
            return False
        
        print("Синхронизация завершена успешно")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Синхронизация изменений с GitHub'
    )
    parser.add_argument(
        'action',
        choices=['status', 'add', 'commit', 'push', 'sync', 'diff'],
        help='Действие для выполнения'
    )
    parser.add_argument(
        '--files',
        default='.',
        help='Файлы для добавления (по умолчанию все)'
    )
    parser.add_argument(
        '--message', '-m',
        help='Сообщение коммита'
    )
    parser.add_argument(
        '--branch', '-b',
        help='Ветка для пуша'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300000,
        help='Таймаут в миллисекундах (по умолчанию 300000 = 5 минут)'
    )
    parser.add_argument(
        '--repo',
        help='Путь к репозиторию'
    )
    
    args = parser.parse_args()
    
    sync = GitHubSync(repo_path=args.repo, timeout_ms=args.timeout)
    
    if args.action == 'status':
        success = sync.status()
    elif args.action == 'add':
        success = sync.add(args.files)
    elif args.action == 'commit':
        if not args.message:
            print("Ошибка: требуется сообщение коммита (-m)")
            sys.exit(1)
        success = sync.commit(args.message)
    elif args.action == 'push':
        success = sync.push(branch=args.branch)
    elif args.action == 'sync':
        if not args.message:
            print("Ошибка: требуется сообщение коммита (-m)")
            sys.exit(1)
        success = sync.sync(args.message, args.files)
    elif args.action == 'diff':
        success = sync.diff()
    else:
        print(f"Неизвестное действие: {args.action}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
