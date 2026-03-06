"""
Главный модуль для запуска Parser2GIS через `python -m parser_2gis`.

Этот модуль позволяет запускать парсер как пакет из командной строки:
    python -m parser_2gis --help
    python -m parser_2gis --url https://2gis.ru/moscow/search/Аптеки -o output.csv -f csv
"""

from parser_2gis import main

if __name__ == '__main__':
    main()