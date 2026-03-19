#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт обновления списка рубрик.

Загружает рубрики с API 2GIS и сохраняет в parser_2gis/data/rubrics.json
"""

import json
import os
import sys

for _ in range(2):
    try:
        import parser_2gis.paths
        from parser_2gis.chrome import ChromeOptions, ChromeRemote

        break
    except ImportError:
        here = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.abspath(os.path.join(here, os.pardir))
        if parent_dir not in sys.path:
            sys.path.insert(1, parent_dir)

# URL API для получения списка рубрик
_REGIONS_LIST_RESPONSE = r"https://hermes.2gis.ru/api/data/availableParameters"

chrome_options = ChromeOptions(headless=True)
with ChromeRemote(chrome_options, [_REGIONS_LIST_RESPONSE]) as chrome_remote:
    chrome_remote.navigate("https://data.2gis.com", timeout=300)
    response = chrome_remote.wait_response(_REGIONS_LIST_RESPONSE)
    data = chrome_remote.get_response_body(response)

    try:
        doc = json.loads(data)
    except json.JSONDecodeError:
        print("Возвращён некорректный JSON документ!", file=sys.stderr)
        sys.exit(1)

    if not doc:
        print("Нет ответа, выходим!", file=sys.stderr)
        sys.exit(1)

    # Отбираем нужные данные
    rubrics = doc["rubrics"]
    for v in rubrics.values():
        del v["totalCount"]
        del v["groupId"]

    # Проверка специальной None рубрики
    assert any(x["label"] == "Без рубрики" for x in rubrics.values())

    # Сохраняем список рубрик
    rubrics_path = parser_2gis.paths.data_path() / "rubrics.json"
    with open(rubrics_path, "w", encoding="utf-8") as f:
        json.dump(rubrics, f, ensure_ascii=False, indent=4)
        print(f"Сохранено {len(rubrics)} рубрик в {rubrics_path}")
