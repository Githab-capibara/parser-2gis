#!/usr/bin/env bash
# Pyright: быстрая проверка типов с кратким выводом
set -euo pipefail

pyright parser_2gis --outputjson 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    diags = data.get('generalDiagnostics', [])
    summary = data.get('summary', {})
    if not diags:
        print('Pyright: ошибок не найдено ✓')
    else:
        for d in diags[:50]:
            print(f\"{d['file']}:{d.get('range',{}).get('start',{}).get('line','?')}: [{d['severity']}] {d['message'][:150]}\")
        print(f\"\nИтого: {summary.get('errorCount', 0)} ошибок, {summary.get('warningCount', 0)} предупреждений\")
except Exception as e:
    print(f'Pyright анализ завершён: {e}')
" || true
