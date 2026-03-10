#!/usr/bin/env python3
"""
Тесты для проверки валидации аргументов --categories-mode в main.py.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Добавляем путь к пакету
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser_2gis.main import parse_arguments


class TestCategoriesModeValidation:
    """Тесты валидации аргументов для --categories-mode."""

    def test_categories_mode_requires_cities(self):
        """--categories-mode без --cities должен вызывать ошибку."""
        with patch('sys.argv', ['parser-2gis', '--categories-mode', '-o', 'output.csv', '-f', 'csv']):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 2  # Код ошибки argparse

    def test_categories_mode_with_cities_valid(self):
        """--categories-mode с --cities должен проходить валидацию."""
        # Мокаем cities.json в реальном data_path
        from parser_2gis.paths import data_path
        real_data_path = data_path()
        cities_file = real_data_path / 'cities.json'
        backup_file = real_data_path / 'cities.json.backup'
        
        # Создаём резервную копию если файл существует
        if cities_file.exists():
            import shutil
            shutil.copy2(cities_file, backup_file)
        
        # Создаём фиктивный cities.json
        cities_file.write_text('[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]')

        try:
            with patch('sys.argv', ['parser-2gis', '--cities', 'omsk', '--categories-mode', '-o', 'output/', '-f', 'csv']):
                args, config = parse_arguments()

            assert args.cities == ['omsk']
            assert args.categories_mode is True
        finally:
            # Восстанавливаем оригинальный файл
            if backup_file.exists():
                import shutil
                shutil.copy2(backup_file, cities_file)
                backup_file.unlink()

    def test_url_not_required_when_cities_specified(self):
        """-i/--url не обязателен, когда указан --cities."""
        from parser_2gis.paths import data_path
        real_data_path = data_path()
        cities_file = real_data_path / 'cities.json'
        backup_file = real_data_path / 'cities.json.backup'
        
        if cities_file.exists():
            import shutil
            shutil.copy2(cities_file, backup_file)
        
        cities_file.write_text('[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]')

        try:
            with patch('sys.argv', ['parser-2gis', '--cities', 'omsk', '-o', 'output.csv', '-f', 'csv']):
                args, config = parse_arguments()

            assert args.cities == ['omsk']
            assert args.url is None
        finally:
            if backup_file.exists():
                import shutil
                shutil.copy2(backup_file, cities_file)
                backup_file.unlink()

    def test_requires_url_or_cities(self):
        """Требуется хотя бы один источник URL: -i или --cities."""
        with patch('sys.argv', ['parser-2gis', '-o', 'output.csv', '-f', 'csv']):
            with pytest.raises(SystemExit) as exc_info:
                parse_arguments()
            assert exc_info.value.code == 2

    def test_both_url_and_cities_valid(self):
        """Можно указать и -i и --cities одновременно."""
        from parser_2gis.paths import data_path
        real_data_path = data_path()
        cities_file = real_data_path / 'cities.json'
        backup_file = real_data_path / 'cities.json.backup'
        
        if cities_file.exists():
            import shutil
            shutil.copy2(cities_file, backup_file)
        
        cities_file.write_text('[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]')

        try:
            with patch('sys.argv', ['parser-2gis', '-i', 'https://2gis.ru/moscow/search/Аптеки', '--cities', 'omsk', '-o', 'output.csv', '-f', 'csv']):
                args, config = parse_arguments()

            assert args.url is not None
            assert args.cities == ['omsk']
        finally:
            if backup_file.exists():
                import shutil
                shutil.copy2(backup_file, cities_file)
                backup_file.unlink()


class TestParallelWorkersValidation:
    """Тесты валидации --parallel-workers."""

    def test_parallel_workers_default(self):
        """Проверка значения по умолчанию."""
        from parser_2gis.paths import data_path
        real_data_path = data_path()
        cities_file = real_data_path / 'cities.json'
        backup_file = real_data_path / 'cities.json.backup'
        
        if cities_file.exists():
            import shutil
            shutil.copy2(cities_file, backup_file)
        
        cities_file.write_text('[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]')

        try:
            with patch('sys.argv', ['parser-2gis', '--cities', 'omsk', '--categories-mode', '-o', 'output/', '-f', 'csv']):
                args, config = parse_arguments()

            assert args.parallel_workers == 3  # По умолчанию
        finally:
            if backup_file.exists():
                import shutil
                shutil.copy2(backup_file, cities_file)
                backup_file.unlink()

    def test_parallel_workers_custom(self):
        """Проверка пользовательского значения."""
        from parser_2gis.paths import data_path
        real_data_path = data_path()
        cities_file = real_data_path / 'cities.json'
        backup_file = real_data_path / 'cities.json.backup'
        
        if cities_file.exists():
            import shutil
            shutil.copy2(cities_file, backup_file)
        
        cities_file.write_text('[{"code": "omsk", "domain": "ru", "name": "Омск", "country_code": "ru"}]')

        try:
            with patch('sys.argv', ['parser-2gis', '--cities', 'omsk', '--categories-mode', '--parallel-workers', '5', '-o', 'output/', '-f', 'csv']):
                args, config = parse_arguments()

            assert args.parallel_workers == 5
        finally:
            if backup_file.exists():
                import shutil
                shutil.copy2(backup_file, cities_file)
                backup_file.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
