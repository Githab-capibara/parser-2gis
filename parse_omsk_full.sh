#!/bin/bash

# ╔══════════════════════════════════════════════════════════╗
# ║     Парсинг ВСЕГО Омска (93 категории, 10 браузеров)     ║
# ║            с автоматическим объединением в 1 CSV         ║
# ╚══════════════════════════════════════════════════════════╝

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output/omsk_all"
MERGED_FILE="$SCRIPT_DIR/output/omsk_ALL_merged.csv"

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

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
echo -e "${BLUE}   📊 Город: Омск${NC}"
echo -e "${BLUE}   📂 Категории: 93 (все доступные)${NC}"
echo -e "${BLUE}   🔧 Потоков: 10 (параллельных браузеров)${NC}"
echo -e "${BLUE}   📁 Вывод: $OUTPUT_DIR${NC}"
echo ""

cd "$SCRIPT_DIR"
./run.sh --cities omsk --categories-mode --parallel.max-workers 10 -o "$OUTPUT_DIR" -f csv --chrome.headless yes --chrome.disable-images yes

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Ошибка парсинга!${NC}"
    exit 1
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
