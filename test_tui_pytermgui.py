#!/usr/bin/env python3
"""
Тестовый скрипт для проверки TUI Parser2GIS на pytermgui.
"""

import sys
import os

# Добавить проект в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parser_2gis.tui_pytermgui import Parser2GISTUI


def main():
    """Запустить TUI приложение."""
    print("Запуск Parser2GIS TUI на pytermgui...")
    print("Нажмите Ctrl+C для выхода")
    print()
    
    app = Parser2GISTUI()
    app.run()


if __name__ == "__main__":
    main()
