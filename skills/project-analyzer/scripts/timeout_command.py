#!/usr/bin/env python3
"""
Скрипт для выполнения команд с таймаутом.

Использование:
    python timeout_command.py <command> [timeout_ms]

Аргументы:
    command - команда для выполнения
    timeout_ms - таймаут в миллисекундах (по умолчанию 300000 = 5 минут)
"""

import subprocess
import sys
import argparse


def execute_command(command: str, timeout_ms: int = 300000) -> tuple[int, str, str]:
    """
    Выполнить команду с указанным таймаутом.
    
    Args:
        command: Команда для выполнения
        timeout_ms: Таймаут в миллисекундах
        
    Returns:
        Кортеж (код возврата, stdout, stderr)
    """
    timeout_sec = timeout_ms / 1000.0
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return (
            -1,
            "",
            f"Ошибка: команда превысила таймаут {timeout_ms} мс ({timeout_sec} сек)"
        )
    except Exception as e:
        return -1, "", f"Ошибка выполнения: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description='Выполнение команд с таймаутом'
    )
    parser.add_argument(
        'command',
        help='Команда для выполнения'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300000,
        help='Таймаут в миллисекундах (по умолчанию 300000 = 5 минут)'
    )
    
    args = parser.parse_args()
    
    returncode, stdout, stderr = execute_command(args.command, args.timeout)
    
    if stdout:
        print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    
    sys.exit(returncode if returncode >= 0 else 1)


if __name__ == '__main__':
    main()
