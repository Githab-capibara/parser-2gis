#!/usr/bin/env python3

# Загружаем информацию о городах для следующих стран:
# ae, az, bh, by, cl, cy, cz, eg, it, kg, kw, kz, om, qa, ru, sa, uz

import json
import os
import sys

for _ in range(2):
    try:
        import parser_2gis.paths
        from parser_2gis.chrome import (ChromeOptions,
                                        ChromeRemote)
        break
    except ImportError:
        here = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.abspath(os.path.join(here, os.pardir))
        if parent_dir not in sys.path:
            sys.path.insert(1, parent_dir)

# Получаем доступные города с https://data.2gis.com и сохраняем в data/cities.json

_REGIONS_LIST_RESPONSE = r'https://catalog\.api\.2gis.[^/]+/.*/region/list'

# ПРИМЕЧАНИЕ:
# Также есть список городов в 'https://hermes.2gis.ru/api/data/availableParameters'
# В нём меньше записей, чем в '/region/list', но он более структурирован (дерево против плоского списка).
# Лучше использовать '/region/list' для целей парсинга.

chrome_options = ChromeOptions(headless=True)
with ChromeRemote(chrome_options, [_REGIONS_LIST_RESPONSE]) as chrome_remote:
    chrome_remote.navigate('https://data.2gis.com', timeout=300)
    response = chrome_remote.wait_response(_REGIONS_LIST_RESPONSE)
    data = chrome_remote.get_response_body(response)

    try:
        doc = json.loads(data)
    except json.JSONDecodeError:
        print('Возвращён некорректный JSON документ!', file=sys.stderr)
        exit(1)

    if not doc:
        print('Нет ответа, выходим!', file=sys.stderr)
        exit(1)

    cities = []
    for item in doc['result']['items']:
        cities.append({
            # "name" может содержать завершающий символ подчёркивания
            # по некоторым причинам, избавляемся от него.
            'name': item['name'].strip('_'),
            'code': item['code'],
            'domain': item['domain'],
            'country_code': item['country_code'],
        })

    cities = sorted(cities, key=lambda x: x['domain'])
    cities_path = parser_2gis.paths.data_path() / 'cities.json'
    with open(cities_path, 'w', encoding='utf-8') as f:
        json.dump(cities, f, ensure_ascii=False, indent=4)
