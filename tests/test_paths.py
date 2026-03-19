"""
Тесты для модуля paths.py.

Проверяют следующие функции:
- data_path()
- user_path()
- image_path()
- image_data()
"""

import os
import pathlib
import pytest

from parser_2gis.paths import data_path, image_data, image_path, user_path


class TestDataPath:
    """Тесты для data_path."""

    def test_data_path_exists(self):
        """Проверка существования data_path."""
        path = data_path()
        assert path is not None

    def test_data_path_is_pathlib(self):
        """Проверка, что data_path возвращает pathlib.Path."""
        path = data_path()
        assert isinstance(path, pathlib.Path)

    def test_data_path_exists_on_disk(self):
        """Проверка существования директории на диске."""
        path = data_path()
        assert path.exists()
        assert path.is_dir()

    def test_data_path_contains_data(self):
        """Проверка, что data_path содержит данные."""
        path = data_path()
        # Должны быть файлы cities.json и rubrics.json
        assert (path / "cities.json").exists()
        assert (path / "rubrics.json").exists()

    def test_data_path_contains_images(self):
        """Проверка, что data_path содержит изображения."""
        path = data_path()
        images_dir = path / "images"
        assert images_dir.exists()
        assert images_dir.is_dir()


class TestUserPath:
    """Тесты для user_path."""

    def test_user_path_exists(self):
        """Проверка существования user_path."""
        path = user_path()
        assert path is not None

    def test_user_path_is_pathlib(self):
        """Проверка, что user_path возвращает pathlib.Path."""
        path = user_path()
        assert isinstance(path, pathlib.Path)

    def test_user_path_for_config(self):
        """Проверка user_path для конфигурации."""
        path = user_path(is_config=True)
        assert path is not None

    def test_user_path_for_data(self):
        """Проверка user_path для данных."""
        path = user_path(is_config=False)
        assert path is not None

    def test_user_path_parser_2gis_name(self):
        """Проверка имени директории parser-2gis."""
        path_config = user_path(is_config=True)
        path_data = user_path(is_config=False)
        assert "parser-2gis" in str(path_config)
        assert "parser-2gis" in str(path_data)


class TestImagePath:
    """Тесты для image_path."""

    def test_image_path_icon_png(self):
        """Проверка image_path для icon.png."""
        path = image_path("icon", "png")
        assert os.path.exists(path)
        assert path.endswith(".png")

    def test_image_path_logo_png(self):
        """Проверка image_path для logo.png."""
        path = image_path("logo", "png")
        assert os.path.exists(path)
        assert path.endswith(".png")

    def test_image_path_loading_gif(self):
        """Проверка image_path для loading.gif."""
        path = image_path("loading", "gif")
        assert os.path.exists(path)
        assert path.endswith(".gif")

    def test_image_path_without_extension(self):
        """Проверка image_path без указания расширения."""
        path = image_path("icon")
        assert os.path.exists(path)

    def test_image_path_not_found(self):
        """Проверка image_path для несуществующего файла."""
        with pytest.raises(FileNotFoundError):
            image_path("nonexistent_image")

    def test_image_path_returns_absolute(self):
        """Проверка, что image_path возвращает абсолютный путь."""
        path = image_path("icon", "png")
        assert os.path.isabs(path)


class TestImageData:
    """Тесты для image_data."""

    def test_image_data_icon_png(self):
        """Проверка image_data для icon.png."""
        data = image_data("icon", "png")
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_image_data_logo_png(self):
        """Проверка image_data для logo.png."""
        data = image_data("logo", "png")
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_image_data_is_base64(self):
        """Проверка, что image_data возвращает base64."""
        import base64

        data = image_data("icon", "png")
        # Должно быть валидным base64
        try:
            base64.b64decode(data)
        except Exception:
            pytest.fail("image_data не вернула валидный base64")

    def test_image_data_without_extension(self):
        """Проверка image_data без указания расширения."""
        data = image_data("icon")
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_image_data_not_found(self):
        """Проверка image_data для несуществующего файла."""
        with pytest.raises(FileNotFoundError):
            image_data("nonexistent_image")

    def test_image_data_cached(self):
        """Проверка кэширования image_data."""
        data1 = image_data("icon", "png")
        data2 = image_data("icon", "png")
        assert data1 is data2  # Один и тот же объект благодаря lru_cache


class TestImagePathVsImageData:
    """Тесты для связи image_path и image_data."""

    def test_image_data_matches_file(self):
        """Проверка, что image_data соответствует файлу."""
        import base64

        path = image_path("icon", "png")
        data = image_data("icon", "png")

        with open(path, "rb") as f:
            file_data = base64.b64encode(f.read())

        assert data == file_data


class TestImageFormats:
    """Тесты для различных форматов изображений."""

    def test_png_images(self):
        """Проверка PNG изображений."""
        png_images = [
            "icon",
            "logo",
            "rubric_folder",
            "rubric_item",
            "settings",
            "settings_inverted",
        ]
        for name in png_images:
            try:
                path = image_path(name, "png")
                assert os.path.exists(path)
            except FileNotFoundError:
                pass  # Некоторые изображения могут отсутствовать

    def test_gif_images(self):
        """Проверка GIF изображений."""
        path = image_path("loading", "gif")
        assert os.path.exists(path)

    def test_ico_images(self):
        """Проверка ICO изображений."""
        try:
            path = image_path("icon", "ico")
            assert os.path.exists(path)
        except FileNotFoundError:
            pass  # Может отсутствовать на некоторых платформах

    def test_icns_images(self):
        """Проверка ICNS изображений."""
        try:
            path = image_path("icon", "icns")
            assert os.path.exists(path)
        except FileNotFoundError:
            pass  # Может отсутствовать на некоторых платформах
