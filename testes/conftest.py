"""
Общие фикстуры и конфигурация для тестов.

Этот файл содержит общие фикстуры, которые используются
в нескольких тестовых модулях.
"""

import pytest
import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope='session')
def test_data_dir():
    """Фикстура для директории с тестовыми данными.
    
    Returns:
        Путь к директории с тестовыми данными.
    """
    return os.path.join(os.path.dirname(__file__), 'data')


@pytest.fixture
def temp_file(tmp_path):
    """Фикстура для временного файла.
    
    Args:
        tmp_path: pytest tmp_path fixture.
    
    Returns:
        Путь к временному файлу.
    """
    file_path = tmp_path / 'test_file.txt'
    file_path.write_text('')
    return str(file_path)


@pytest.fixture
def sample_urls():
    """Фикстура для примеров URL.
    
    Returns:
        Список примеров URL.
    """
    return [
        'https://2gis.ru/moscow/search/Аптеки',
        'https://2gis.ru/spb/search/Рестораны',
        'https://2gis.ru/kazan/search/Магазины',
    ]


@pytest.fixture
def sample_config_dict():
    """Фикстура для примера конфигурации в виде словаря.
    
    Returns:
        Словарь с примером конфигурации.
    """
    return {
        'chrome': {
            'headless': True,
            'memory_limit': 512,
            'disable_images': True,
        },
        'parser': {
            'max_records': 10,
            'delay_between_clicks': 100,
            'skip_404_response': True,
        },
        'writer': {
            'encoding': 'utf-8-sig',
            'verbose': False,
            'csv': {
                'add_rubrics': True,
                'add_comments': False,
            }
        }
    }


@pytest.fixture
def sample_org_data():
    """Фикстура для примера данных организации.
    
    Returns:
        Словарь с примером данных организации.
    """
    return {
        'name': 'Тестовая организация',
        'address': 'г. Москва, ул. Тестовая, д. 1',
        'phones': ['+7 (495) 123-45-67'],
        'emails': ['test@example.com'],
        'website': 'https://example.com',
        'rubrics': ['Тестовая рубрика'],
    }


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Автоматическая фикстура для настройки тестового окружения.
    
    Выполняется перед каждым тестом.
    """
    # Настройка перед тестом
    os.environ['TESTING'] = 'True'
    
    yield
    
    # Очистка после теста
    if 'TESTING' in os.environ:
        del os.environ['TESTING']


@pytest.fixture
def mock_response():
    """Фикстура для мок-ответа.
    
    Returns:
        Словарь с примером ответа.
    """
    return {
        'status': 'success',
        'data': {
            'items': [],
            'total': 0
        }
    }


@pytest.fixture(params=['csv', 'json', 'xlsx'])
def output_format(request):
    """Фикстура для перебора форматов вывода.
    
    Returns:
        Формат вывода.
    """
    return request.param


@pytest.fixture(params=[True, False])
def headless_mode(request):
    """Фикстура для перебора режимов headless.
    
    Returns:
        Значение headless режима.
    """
    return request.param


@pytest.fixture(params=[1, 5, 10, 50, 100])
def num_records(request):
    """Фикстура для перебора количества записей.
    
    Returns:
        Количество записей.
    """
    return request.param
