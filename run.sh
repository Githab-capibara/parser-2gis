#!/bin/bash

# Скрипт запуска Parser2GIS
# Автоматически активирует виртуальное окружение и запускает приложение

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# Проверка наличия виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "Ошибка: Виртуальное окружение не найдено в $VENV_DIR"
    echo "Запустите установку зависимостей перед запуском приложения"
    exit 1
fi

# Активация виртуального окружения
source "$VENV_DIR/bin/activate"

# Запуск приложения (фильтрация предупреждений PySimpleGUI)
python "$SCRIPT_DIR/parser-2gis.py" "$@" 2>&1 | grep -v -E "(PySimpleGUI|pip uninstall|pip cache|pip install.*--extra-index-url|PySimpleGUI\.net|The version you just installed|Then install the latest|You can also force|Use python3 command|if you're running on the Mac)"
