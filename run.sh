#!/bin/bash

# Скрипт запуска Parser2GIS с новым TUI интерфейсом на pytermgui
# Автоматически активирует виртуальное окружение и запускает приложение с TUI
# Запускает парсинг Омска в 10 параллельных браузеров по всем 93 категориям

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # Без цвета

# Функция вывода заголовка
print_header() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║     Parser2GIS v2.1 - Современный парсер данных 2GIS     ║"
    echo "║              с новым TUI интерфейсом                     ║"
    echo "╚══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# Функция вывода справки
print_help() {
    print_header
    echo -e "${GREEN}Использование:${NC}"
    echo "  ./run.sh [опции]"
    echo ""
    echo -e "${GREEN}Режимы работы:${NC}"
    echo "  Без аргументов    - Запуск TUI с парсингом Омска (10 браузеров, 93 категории)"
    echo "  --tui             - Запуск TUI без автоматического парсинга"
    echo "  С аргументами     - Запуск CLI с указанными параметрами"
    echo ""
    echo -e "${GREEN}Примеры:${NC}"
    echo "  ./run.sh                                          # Омск, 93 категории, 10 потоков, TUI"
    echo "  ./run.sh --tui                                    # Запуск TUI вручную"
    echo "  ./run.sh --cities omsk spb --categories-mode      # Омск + СПб, категории (CLI)"
    echo "  ./run.sh -i URL1 URL2 -o result.csv -f csv        # Парсинг по URL (CLI)"
    echo ""
    echo -e "${GREEN}Основные опции:${NC}"
    echo "  --tui                     - Запустить TUI интерфейс"
    echo "  --cities CITY1 CITY2      - Коды городов для парсинга"
    echo "  --categories-mode         - Режим парсинга по 93 категориям"
    echo "  --parallel-workers N      - Количество потоков (по умолчанию: 10)"
    echo "  -i URL                    - URL для парсинга"
    echo "  -o PATH                   - Путь к выходному файлу"
    echo "  -f FORMAT                 - Формат: csv, xlsx, json"
    echo "  -h, --help                - Показать эту справку"
    echo ""
    echo -e "${YELLOW}🎨 TUI интерфейс (pytermgui) отображает:${NC}"
    echo "  ✓ Главное меню с навигацией"
    echo "  ✓ Выбор городов с поиском (204 города)"
    echo "  ✓ Выбор категорий с поиском (93 категории)"
    echo "  ✓ Настройки браузера, парсера, вывода"
    echo "  ✓ Прогресс-бары (URL, страницы, записи)"
    echo "  ✓ Статистику в реальном времени"
    echo "  ✓ Логи с цветовой индикацией"
    echo "  ✓ Просмотр кэша"
    echo ""
}

# Проверка наличия виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Ошибка: Виртуальное окружение не найдено в $VENV_DIR${NC}"
    echo ""
    echo -e "${YELLOW}Создаю виртуальное окружение и устанавливаю зависимости...${NC}"
    echo ""

    # Создаём виртуальное окружение
    python3 -m venv "$VENV_DIR"

    # Активируем
    source "$VENV_DIR/bin/activate"

    # Обновляем pip
    echo -e "${CYAN}Обновление pip...${NC}"
    pip install --upgrade pip

    # Устанавливаем зависимости
    echo -e "${CYAN}Установка зависимостей...${NC}"
    pip install -e "$SCRIPT_DIR"

    echo ""
    echo -e "${GREEN}✓ Виртуальное окружение создано и настроено${NC}"
    echo ""
else
    # Активация виртуального окружения
    source "$VENV_DIR/bin/activate"
fi

# Обработка аргументов
if [ $# -eq 0 ]; then
    # Без аргументов - запускаем НОВЫЙ TUI с парсингом Омска в 10 потоков
    print_header
    echo -e "${GREEN}🚀 Запуск NEW TUI (pytermgui) с парсингом Омска${NC}"
    echo -e "${BLUE}📊 Город: Омск${NC}"
    echo -e "${BLUE}📂 Категории: 93 (все доступные)${NC}"
    echo -e "${BLUE}🔧 Потоков: 10 (одновременных браузеров)${NC}"
    echo -e "${YELLOW}🎨 Интерфейс: современный TUI на pytermgui${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Запускаем НОВЫЙ TUI с автоматическим парсингом Омска
    python "$SCRIPT_DIR/parser-2gis.py" --tui-new-omsk

    EXIT_CODE=$?

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ Парсинг завершён успешно!${NC}"
        echo -e "${BLUE}📁 Результаты в папке: ${YELLOW}output/${NC}"
        echo -e "${BLUE}📄 Логи в папке: ${YELLOW}logs/${NC}"
    else
        echo -e "${RED}❌ Парсинг завершён с ошибками${NC}"
    fi

    exit $EXIT_CODE

elif [ "$1" = "--tui" ]; then
    # Запуск TUI без автоматического парсинга
    print_header
    echo -e "${GREEN}🚀 Запуск NEW TUI (pytermgui)${NC}"
    echo -e "${YELLOW}🎨 Интерфейс: современный TUI на pytermgui${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Запускаем TUI вручную
    python "$SCRIPT_DIR/parser-2gis.py" --tui

    exit $?

elif [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ "$1" = "help" ]; then
    print_help
    exit 0

else
    # Запуск с переданными аргументами (CLI режим)
    print_header
    echo -e "${GREEN}🚀 Запуск Parser2GIS (CLI режим) с аргументами:${NC}"
    echo -e "${CYAN}   $@${NC}"
    echo ""
    echo -e "${YELLOW}🎨 TUI интерфейс (старый, на rich) активирован${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Запуск с переданными аргументами
    python "$SCRIPT_DIR/parser-2gis.py" "$@" \
        2>&1 | grep -v -E "(PySimpleGUI|pip uninstall|pip cache|pip install.*--extra-index-url|PySimpleGUI\.net|The version you just installed|Then install the latest|You can also force|Use python3 command|if you're running on the Mac)"

    EXIT_CODE=$?

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✅ Выполнено успешно!${NC}"
        echo -e "${BLUE}📄 Логи в папке: ${YELLOW}logs/${NC}"
    else
        echo -e "${RED}❌ Ошибка выполнения${NC}"
    fi

    exit $EXIT_CODE
fi
