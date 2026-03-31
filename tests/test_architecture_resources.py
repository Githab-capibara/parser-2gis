"""
Тесты для новой структуры resources/.

Проверяет:
- Существование директории resources/
- Наличие cities.json и rubrics.json
- Наличие изображений в resources/images/
- Удаление старых data/ директорий
- Работу функции resources_path()
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# =============================================================================
# ТЕСТ 1: СУЩЕСТВОВАНИЕ ДИРЕКТОРИИ RESOURCES
# =============================================================================


class TestResourcesDirectory:
    """Тесты для директории resources/."""

    def test_resources_directory_exists(self) -> None:
        """Проверка существования директории resources/.

        Убеждаемся что новая структура ресурсов существует
        и доступна для использования.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        resources_dir = project_root / "resources"

        assert resources_dir.exists(), "Директория resources/ должна существовать"
        assert resources_dir.is_dir(), "resources/ должна быть директорией"

    def test_resources_has_cities_json(self) -> None:
        """Проверка наличия cities.json.

        Файл cities.json должен существовать в resources/
        и содержать валидный JSON со списком городов.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        cities_file = project_root / "resources" / "cities.json"

        assert cities_file.exists(), "cities.json должен существовать в resources/"

        # Проверяем что это валидный JSON
        with open(cities_file, "r", encoding="utf-8") as f:
            cities_data = json.load(f)

        assert isinstance(cities_data, list), "cities.json должен содержать список городов"
        assert len(cities_data) > 0, "cities.json не должен быть пустым"

        # Проверяем структуру первого города
        if cities_data:
            first_city = cities_data[0]
            assert "code" in first_city, "Город должен содержать поле 'code'"
            assert "domain" in first_city, "Город должен содержать поле 'domain'"

    def test_resources_has_rubrics_json(self) -> None:
        """Проверка наличия rubrics.json.

        Файл rubrics.json должен существовать в resources/
        и содержать валидный JSON.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        rubrics_file = project_root / "resources" / "rubrics.json"

        assert rubrics_file.exists(), "rubrics.json должен существовать в resources/"

        # Проверяем что это валидный JSON
        with open(rubrics_file, "r", encoding="utf-8") as f:
            rubrics_data = json.load(f)

        # rubrics.json может быть dict или list
        assert isinstance(rubrics_data, (dict, list)), "rubrics.json должен содержать dict или list"

    def test_resources_has_images(self) -> None:
        """Проверка наличия изображений.

        Директория resources/images/ должна существовать
        и содержать файлы изображений.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"
        images_dir = project_root / "resources" / "images"

        assert images_dir.exists(), "Директория resources/images/ должна существовать"
        assert images_dir.is_dir(), "resources/images/ должна быть директорией"

        # Проверяем что есть хотя бы одно изображение
        image_files = list(images_dir.glob("*"))
        assert len(image_files) > 0, "resources/images/ должна содержать хотя бы одно изображение"

    def test_old_data_directories_removed(self) -> None:
        """Проверка удаления старых data/ директорий.

        Старые директории data/ не должны существовать
        для предотвращения дублирования ресурсов.
        """
        project_root = Path(__file__).parent.parent / "parser_2gis"

        # Проверяем что старых data/ директорий нет
        old_data_dirs = [project_root / "data", project_root / "parser_2gis" / "data"]

        for data_dir in old_data_dirs:
            if data_dir.exists():
                # Если директория существует, проверяем что она не содержит
                # городов или рубрик (может быть другая data)
                cities_file = data_dir / "cities.json"
                rubrics_file = data_dir / "rubrics.json"

                assert not cities_file.exists(), (
                    f"Старый cities.json не должен существовать в {data_dir}"
                )
                assert not rubrics_file.exists(), (
                    f"Старый rubrics.json не должен существовать в {data_dir}"
                )

    def test_resources_path_function(self) -> None:
        """Проверка работы функции resources_path().

        Функция resources_path() должна возвращать корректный путь
        к директории ресурсов.
        """
        from parser_2gis.utils.paths import resources_path

        resources_dir = resources_path()

        # resources_path может возвращать путь внутри пакета
        # Проверяем что путь существует или может быть создан
        assert resources_dir is not None, "resources_path() должна возвращать путь"

        # Проверяем что функция возвращает Path
        assert isinstance(resources_dir, Path), "resources_path() должна возвращать Path"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
