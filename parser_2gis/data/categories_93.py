"""
Список из 93 категорий для парсинга городов.

Каждая категория содержит:
- name: Название категории (как будет отображаться в CSV)
- query: Поисковый запрос для 2GIS
- rubric_code: Код рубрики (опционально, если есть точное совпадение)

Этот файл используется для автоматической генерации URL при парсинге городов.
"""

from typing import List, Optional, TypedDict


class CategoryDict(TypedDict):
    """Типизация словаря категории."""

    name: str
    query: str
    rubric_code: Optional[str]


# Полный список из 93 категорий
CATEGORIES_93: List[CategoryDict] = [
    # 1-15: Общественное питание
    {"name": "Кафе", "query": "Кафе", "rubric_code": "161"},
    {"name": "Рестораны", "query": "Рестораны", "rubric_code": "164"},
    {"name": "Бары", "query": "Бары", "rubric_code": "159"},
    {"name": "Столовые", "query": "Столовые", "rubric_code": "166"},
    {"name": "Кофейни", "query": "Кофейни", "rubric_code": "162"},
    {"name": "Пиццерии", "query": "Пиццерии", "rubric_code": "51459"},
    {"name": "Суши-бары", "query": "Суши-бары", "rubric_code": "15791"},
    {"name": "Фастфуд", "query": "Фастфуд", "rubric_code": "20223"},
    {"name": "Бургерные", "query": "Бургерные", "rubric_code": None},  # Используем поиск
    {"name": "Шаурмичные", "query": "Шаурма", "rubric_code": "20223"},
    {"name": "Кондитерские", "query": "Кондитерские", "rubric_code": "363"},
    {"name": "Пекарни", "query": "Пекарни", "rubric_code": "111594"},
    {"name": "Мороженое", "query": "Мороженое", "rubric_code": "469"},
    {"name": "Кальянные", "query": "Кальянные", "rubric_code": "69774"},
    {"name": "Пивные магазины", "query": "Пивные магазины", "rubric_code": None},
    # 16-20: Гостиницы
    {"name": "Гостиницы", "query": "Гостиницы", "rubric_code": "269"},
    {"name": "Хостелы", "query": "Хостелы", "rubric_code": "52681"},
    {"name": "Апартаменты", "query": "Апартаменты посуточно", "rubric_code": None},
    {"name": "Мотели", "query": "Мотели", "rubric_code": None},
    {"name": "Базы отдыха", "query": "Базы отдыха", "rubric_code": "547"},
    # 21-34: Досуг и развлечения
    {"name": "Театры", "query": "Театры", "rubric_code": "192"},
    {"name": "Музеи", "query": "Музеи", "rubric_code": "193"},
    {"name": "Кинотеатры", "query": "Кинотеатры", "rubric_code": "112637"},
    {"name": "Ночные клубы", "query": "Ночные клубы", "rubric_code": "173"},
    {"name": "Боулинг", "query": "Боулинг", "rubric_code": "170"},
    {"name": "Бильярдные", "query": "Бильярдные", "rubric_code": "169"},
    {"name": "Квест-комнаты", "query": "Квест-комнаты", "rubric_code": "110300"},
    {"name": "Парки развлечений", "query": "Парки развлечений", "rubric_code": None},
    {"name": "Аквапарки", "query": "Аквапарки", "rubric_code": "537"},
    {"name": "Зоопарки", "query": "Зоопарки", "rubric_code": None},
    {"name": "Планетарии", "query": "Планетарии", "rubric_code": None},
    {"name": "Галереи", "query": "Художественные галереи", "rubric_code": "190"},
    {"name": "Выставочные центры", "query": "Выставочные центры", "rubric_code": "190"},
    {"name": "Торговые центры", "query": "Торговые центры", "rubric_code": "611"},
    # 35-42: Магазины
    {"name": "Супермаркеты", "query": "Супермаркеты", "rubric_code": "350"},
    {"name": "Продуктовые магазины", "query": "Продуктовые магазины", "rubric_code": "14"},
    {"name": "Магазины одежды", "query": "Магазины одежды", "rubric_code": "69"},
    {"name": "Аптеки", "query": "Аптеки", "rubric_code": "204"},
    {"name": "Магазины электроники", "query": "Магазины электроники", "rubric_code": "85"},
    {"name": "Книжные магазины", "query": "Книжные магазины", "rubric_code": "347"},
    {"name": "Цветочные магазины", "query": "Цветочные магазины", "rubric_code": "389"},
    {"name": "Магазины подарков", "query": "Магазины подарков", "rubric_code": "510"},
    # 43-47: Красота и здоровье
    {"name": "Салоны красоты", "query": "Салоны красоты", "rubric_code": None},
    {"name": "Парикмахерские", "query": "Парикмахерские", "rubric_code": "305"},
    {"name": "Барбершопы", "query": "Барбершопы", "rubric_code": "110998"},
    {"name": "СПА-салоны", "query": "СПА-салоны", "rubric_code": "206"},
    {"name": "Массажные салоны", "query": "Массажные салоны", "rubric_code": "671"},
    # 48-50: Спорт и фитнес
    {"name": "Фитнес-клубы", "query": "Фитнес-клубы", "rubric_code": "268"},
    {"name": "Бассейны", "query": "Бассейны", "rubric_code": "261"},
    {"name": "Сауны", "query": "Сауны", "rubric_code": "946"},
    # 51-54: Медицина
    {"name": "Стоматологии", "query": "Стоматологии", "rubric_code": "222"},
    {"name": "Медицинские центры", "query": "Медицинские центры", "rubric_code": "4521"},
    {"name": "Поликлиники", "query": "Поликлиники", "rubric_code": "224"},
    {"name": "Ветеринарные клиники", "query": "Ветеринарные клиники", "rubric_code": "205"},
    # 55-61: Финансы и услуги
    {"name": "Банки", "query": "Банки", "rubric_code": "492"},
    {"name": "Банкоматы", "query": "Банкоматы", "rubric_code": "522"},
    {"name": "Почта", "query": "Почта", "rubric_code": "338"},
    {"name": "Нотариусы", "query": "Нотариусы", "rubric_code": "343"},
    {"name": "Юридические услуги", "query": "Юридические услуги", "rubric_code": "65"},
    {"name": "Турагентства", "query": "Турагентства", "rubric_code": "272"},
    {"name": "Страховые компании", "query": "Страховые компании", "rubric_code": "107"},
    # 62-65: Бытовые услуги
    {"name": "Фотосалоны", "query": "Фотосалоны", "rubric_code": None},
    {"name": "Химчистки", "query": "Химчистки", "rubric_code": "313"},
    {"name": "Прачечные", "query": "Прачечные", "rubric_code": "1013"},
    {"name": "Ремонт телефонов", "query": "Ремонт телефонов", "rubric_code": "667"},
    # 66-70: Авто
    {"name": "Автосервисы", "query": "Автосервисы", "rubric_code": None},
    {"name": "Автозапчасти", "query": "Автозапчасти", "rubric_code": "430"},
    {"name": "Автозаправки", "query": "Автозаправки", "rubric_code": "618"},
    {"name": "Автошколы", "query": "Автошколы", "rubric_code": "233"},
    {"name": "Такси", "query": "Такси", "rubric_code": "533"},
    # 71-77: Образование
    {"name": "Школы", "query": "Школы", "rubric_code": "243"},
    {"name": "Детские сады", "query": "Детские сады", "rubric_code": "237"},
    {"name": "Университеты", "query": "Университеты", "rubric_code": "232"},
    {"name": "Колледжи", "query": "Колледжи", "rubric_code": "246"},
    {"name": "Языковые школы", "query": "Языковые школы", "rubric_code": "675"},
    {"name": "Учебные центры", "query": "Учебные центры", "rubric_code": "39"},
    {"name": "Детские кружки и секции", "query": "Детские кружки и секции", "rubric_code": None},
    # 78-84: Госучреждения
    {"name": "МФЦ", "query": "МФЦ", "rubric_code": "53505"},
    {"name": "Налоговые инспекции", "query": "Налоговые инспекции", "rubric_code": "132"},
    {"name": "Паспортные столы", "query": "Паспортные столы", "rubric_code": "330"},
    {"name": "ЗАГСы", "query": "ЗАГСы", "rubric_code": "138"},
    {"name": "Суды", "query": "Суды", "rubric_code": "153"},
    {"name": "Полиция", "query": "Полиция", "rubric_code": "8463"},
    # 85-87: Религия
    {"name": "Церкви", "query": "Церкви", "rubric_code": "194"},
    {"name": "Мечети", "query": "Мечети", "rubric_code": "13374"},
    {"name": "Синагоги", "query": "Синагоги", "rubric_code": "1175"},
    # 88-93: Прочее
    {"name": "Парки", "query": "Парки", "rubric_code": "168"},
    {"name": "Скверы", "query": "Скверы", "rubric_code": "168"},
    {"name": "Стадионы", "query": "Стадионы", "rubric_code": "634"},
    {"name": "Спортивные площадки", "query": "Спортивные площадки", "rubric_code": None},
    {"name": "Кладбища", "query": "Кладбища", "rubric_code": "323"},
    {"name": "Отели для животных", "query": "Отели для животных", "rubric_code": "19661"},
    {"name": "Пункты выдачи заказов", "query": "Пункты выдачи заказов", "rubric_code": "112611"},
]


def get_categories_list() -> List[CategoryDict]:
    """Возвращает список категорий для парсинга."""
    return CATEGORIES_93


def get_category_by_name(name: str) -> Optional[CategoryDict]:
    """Возвращает категорию по названию."""
    for cat in CATEGORIES_93:
        if cat["name"].lower() == name.lower():
            return cat
    return None


def generate_urls_for_city(
    city: dict, categories: Optional[List[CategoryDict]] = None
) -> List[str]:
    """
    Генерирует URL для парсинга всех категорий для одного города.

    Args:
        city: Словарь города с полями code, domain.
        categories: Список категорий (по умолчанию все 93).

    Returns:
        Список URL для парсинга.
    """
    from parser_2gis.common import url_query_encode

    if categories is None:
        categories = CATEGORIES_93

    urls = []
    for cat in categories:
        base_url = f"https://2gis.{city['domain']}/{city['code']}"
        query_value = cat["query"]
        # Гарантируем что query_value это str
        if query_value is None:
            query_value = ""
        rest_url = f"/search/{url_query_encode(query_value)}"

        rubric_code = cat.get("rubric_code")
        if rubric_code:
            rest_url += f"/rubricId/{rubric_code}"

        rest_url += "/filters/sort=name"
        url = base_url + rest_url
        urls.append(url)

    return urls


if __name__ == "__main__":
    # Тестовый запуск
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Всего категорий: %d", len(CATEGORIES_93))
    logger.info("Список категорий:")
    for i, cat in enumerate(CATEGORIES_93, 1):
        rubric = cat.get("rubric_code", "Нет")
        logger.info("%2d. %s: %s (rubric: %s)", i, cat["name"], cat["query"], rubric)
