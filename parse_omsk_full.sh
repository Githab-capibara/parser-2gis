#!/bin/bash

# Строгий режим обработки ошибок
set -euo pipefail

# ╔══════════════════════════════════════════════════════════╗
# ║     Парсинг ВСЕГО Омска (93 категории, 10 браузеров)     ║
# ║            с автоматическим объединением в 1 CSV         ║
# ╚══════════════════════════════════════════════════════════╝

# =============================================================================
# КОНФИГУРАЦИЯ (все параметры вынесены в переменные)
# =============================================================================
CITY_CODE="${CITY_CODE:-omsk}"
CITY_NAME="${CITY_NAME:-Омск}"
PARALLEL_WORKERS="${PARALLEL_WORKERS:-10}"
CATEGORIES_MODE="${CATEGORIES_MODE:---categories-mode}"
CHROME_HEADLESS="${CHROME_HEADLESS:-yes}"
CHROME_DISABLE_IMAGES="${CHROME_DISABLE_IMAGES:-yes}"
OUTPUT_FORMAT="${OUTPUT_FORMAT:-csv}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output/omsk_all"
MERGED_FILE="$SCRIPT_DIR/output/omsk_ALL_merged.csv"
RUN_SCRIPT="$SCRIPT_DIR/run.sh"
ENTRY_SCRIPT="$SCRIPT_DIR/parser_2gis_entry.py"

# =============================================================================
# ФУНКЦИИ ОБРАБОТКИ ОШИБОК
# =============================================================================

# Функция очистки ресурсов при выходе
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}Ошибка: скрипт завершён с кодом $exit_code${NC}"
        echo -e "${RED}Проверьте логи в папке logs/ для получения подробностей${NC}"
    fi
    # Деактивируем виртуальное окружение если активно
    if command -v deactivate &>/dev/null; then
        deactivate 2>/dev/null || true
    fi
    exit $exit_code
}

# Функция обработки критических ошибок
handle_error() {
    local line_number=$1
    echo -e "${RED}КРИТИЧЕСКАЯ ОШИБКА в строке $line_number${NC}"
    echo -e "${RED}Выполняется аварийная остановка...${NC}"
    exit 1
}

# Устанавливаем ловушки для обработки ошибок
trap cleanup EXIT
trap 'handle_error $LINENO' ERR
trap 'echo -e "\n${RED}Прервано пользователем${NC}"; exit 130' INT
trap 'echo -e "\n${RED}Прервано по сигналу TERM${NC}"; exit 143' TERM

# =============================================================================
# ЦВЕТА (с проверкой поддержки ANSI)
# =============================================================================
if [ -t 1 ] && command -v tput &>/dev/null && [ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]; then
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    RED='\033[0;31m'
    NC='\033[0m'
else
    GREEN=''
    BLUE=''
    YELLOW=''
    CYAN=''
    RED=''
    NC=''
fi

# =============================================================================
# ПРОВЕРКА ЗАВИСИМОСТЕЙ
# =============================================================================

# Проверка наличия run.sh
if [ ! -f "$RUN_SCRIPT" ]; then
    echo -e "${RED}Ошибка: Скрипт run.sh не найден в $RUN_SCRIPT${NC}"
    exit 1
fi

# Проверка наличия Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Ошибка: Python3 не найден в PATH${NC}"
    exit 1
fi

# =============================================================================
# ОСНОВНОЙ СКРИПТ
# =============================================================================

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     Парсинг ВСЕГО Омска (93 категории, 10 браузеров)     ║"
echo "║            с автоматическим объединением в 1 CSV         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Создаём директорию
mkdir -p "$OUTPUT_DIR"

# ═══════════════════════════════════════════════════════════════
# ШАГ 1: Парсинг
# ═══════════════════════════════════════════════════════════════
echo -e "${GREEN}🚀 ШАГ 1: Запуск парсинга...${NC}"
echo -e "${BLUE}   📊 Город: $CITY_NAME${NC}"
echo -e "${BLUE}   📂 Категории: 93 (все доступные)${NC}"
echo -e "${BLUE}   🔧 Потоков: $PARALLEL_WORKERS (параллельных браузеров)${NC}"
echo -e "${BLUE}   📁 Вывод: $OUTPUT_DIR${NC}"
echo ""

cd "$SCRIPT_DIR"

# Запускаем парсинг через run.sh
set +e
"$RUN_SCRIPT" --cities "$CITY_CODE" "$CATEGORIES_MODE" \
    --parallel.max-workers "$PARALLEL_WORKERS" \
    -o "$OUTPUT_DIR" -f "$OUTPUT_FORMAT" \
    --chrome.headless "$CHROME_HEADLESS" \
    --chrome.disable-images "$CHROME_DISABLE_IMAGES"
PARSE_EXIT_CODE=$?
set -e

if [ $PARSE_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ Ошибка парсинга (код: $PARSE_EXIT_CODE)!${NC}"
    echo -e "${RED}Проверьте логи в папке logs/ для получения подробностей${NC}"
    exit $PARSE_EXIT_CODE
fi

# ═══════════════════════════════════════════════════════════════
# ШАГ 2: Объединение всех CSV в один файл
# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}📊 ШАГ 2: Объединение всех CSV в один файл...${NC}"

python3 << 'PYEOF'
import csv
import sys
from pathlib import Path

output_dir = Path("output/omsk_all")
merged_file = Path("output/omsk_ALL_merged.csv")

# Находим все CSV файлы
csv_files = sorted(output_dir.glob("*.csv"))

if not csv_files:
    print("❌ CSV файлы не найдены!", file=sys.stderr)
    sys.exit(1)

print(f"   📂 Найдено файлов: {len(csv_files)}")

# Читаем заголовки из первого файла
with open(csv_files[0], 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    headers = next(reader)

# Добавляем столбец "Категория"
headers.append("Категория")

# Открываем выходной файл
with open(merged_file, 'w', encoding='utf-8', newline='') as out_f:
    writer = csv.writer(out_f)
    writer.writerow(headers)

    total_rows = 0

    for csv_file in csv_files:
        # Имя категории = имя файла без расширения
        category_name = csv_file.stem

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # пропускаем заголовок

            for row in reader:
                row.append(category_name)
                writer.writerow(row)
                total_rows += 1

        print(f"   ✓ {csv_file.name}")

print()
print(f"✅ ГОТОВО!")
print(f"📊 Всего записей: {total_rows:,}")
print(f"📁 Файл: {merged_file}")
PYEOF

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                  ✅ ЗАВЕРШЕНО УСПЕШНО!                   ${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📁 Отдельные файлы:${NC} $OUTPUT_DIR"
echo -e "${BLUE}📁 Объединённый файл:${NC} $MERGED_FILE"
echo ""
