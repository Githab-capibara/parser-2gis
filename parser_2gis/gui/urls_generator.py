from __future__ import annotations

import json

from ..common import GUI_ENABLED, running_linux
from ..paths import data_path
from .error_popup import gui_error_popup
from .rubric_selector import gui_rubric_selector
from .theme import (COLOR_ACCENT, COLOR_BACKGROUND, COLOR_BACKGROUND_SECONDARY,
                    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
                    COLOR_WHITE, FONT_SIZE_BASE, FONT_SIZE_LG, FONT_SIZE_MD,
                    FONT_SIZE_SM, FONT_SIZE_XL, SPACING_LG, SPACING_MD, SPACING_SM,
                    SPACING_XS, apply_theme, get_font)
from .utils import ensure_gui_enabled, setup_text_widget, url_query_encode

if GUI_ENABLED:
    import PySimpleGUI as sg


@ensure_gui_enabled
def gui_urls_generator() -> list[str]:
    """Запускает генератор URL.

    Запускает форму, которая может построить набор URL из запроса и указанных городов.

    Returns:
        Список сгенерированных URL.
    """
    # Применяем современную тему
    apply_theme('modern')

    # Находим и загружаем список городов
    cities_path = data_path() / 'cities.json'
    if not cities_path.is_file():
        raise FileNotFoundError(f'Файл {cities_path} не найден')

    try:
        with open(cities_path, 'r', encoding='utf-8') as f:
            cities = json.load(f)
    except json.JSONDecodeError as e:
        gui_error_popup(f'Файл {cities_path.name} повреждён:\n{e}')
        return []

    # Доступные страны с их кодами
    default_city_code = 'ru'
    country_code_to_name = dict(
        ae='Объединенные Арабские Эмираты', iq='Ирак',
        az='Азербайджан', bh='Бахрейн', by='Беларусь', cl='Чили', cy='Кипр', cz='Чехия',
        eg='Египет', it='Италия', kg='Киргизия', kw='Кувейт', kz='Казахстан', om='Оман',
        qa='Катар', ru='Россия', sa='Саудовская Аравия', uz='Узбекистан')

    country_name_to_code = {v: k for k, v in country_code_to_name.items()}

    # Стили для элементов
    checkbox_style = {'background_color': COLOR_BACKGROUND,
                      'text_color': COLOR_TEXT_PRIMARY,
                      'font': get_font(FONT_SIZE_BASE),
                      'checkbox_color': COLOR_ACCENT,
                      'pad': ((0, SPACING_SM), (SPACING_XS, SPACING_XS))}
    
    input_style = {'background_color': COLOR_WHITE,
                   'text_color': COLOR_TEXT_PRIMARY,
                   'font': get_font(FONT_SIZE_BASE)}
    
    frame_style = {'background_color': COLOR_BACKGROUND,
                   'title_color': COLOR_TEXT_PRIMARY,
                   'font': get_font(FONT_SIZE_MD, 'bold'),
                   'border_width': 1,
                   'pad': (SPACING_MD, SPACING_SM),
                   'relief': 'flat'}
    
    button_style = {'button_color': (COLOR_WHITE, COLOR_ACCENT),
                    'border_width': 0,
                    'font': get_font(FONT_SIZE_BASE),
                    'pad': (SPACING_SM, SPACING_XS)}
    
    button_secondary_style = {'button_color': (COLOR_TEXT_PRIMARY, COLOR_BACKGROUND_SECONDARY),
                              'border_width': 0,
                              'font': get_font(FONT_SIZE_BASE),
                              'pad': (SPACING_SM, SPACING_XS)}

    # Макеты с чекбоксами для выбора городов по странам
    checkbox_layouts = {}
    for country_code in country_code_to_name.keys():
        layout = []
        for city in cities:
            if city['country_code'] == country_code:
                layout.append([
                    sg.Checkbox(
                        city['name'], metadata=city,
                        **checkbox_style)
                ])
        checkbox_layouts[country_code] = sg.Column(
            layout, scrollable=True, vertical_scroll_only=True,
            expand_x=True, expand_y=True, visible=False,
            background_color=COLOR_BACKGROUND)

    # Получаем размеры экрана для оптимального расположения окна
    _, screen_height = sg.Window.get_screen_size()

    # Макет окна - современный дизайн
    layout = [
        # Заголовок
        [
            sg.Column([
                [
                    sg.Text('Генератор ссылок', font=get_font(FONT_SIZE_XL, 'bold'), 
                            text_color=COLOR_TEXT_PRIMARY, pad=(SPACING_LG, SPACING_MD)),
                ],
            ], background_color=COLOR_BACKGROUND, pad=0),
        ],
        
        # Поля ввода
        [
            sg.Frame('Параметры поиска', layout=[
                [
                    sg.Column([
                        [
                            sg.Text('Поисковый запрос', font=get_font(FONT_SIZE_MD), 
                                    text_color=COLOR_TEXT_PRIMARY, pad=(0, SPACING_XS)),
                            sg.Input(key='-IN_QUERY-', size=(40, 1), 
                                     font=get_font(FONT_SIZE_BASE), background_color=COLOR_WHITE),
                        ],
                    ], expand_x=True, pad=SPACING_MD),
                ],
                [
                    sg.Column([
                        [
                            sg.Text('Страна', font=get_font(FONT_SIZE_MD), 
                                    text_color=COLOR_TEXT_PRIMARY, pad=(0, SPACING_XS)),
                            sg.Combo(key='-COUNTRY-', 
                                     default_value=country_code_to_name[default_city_code],
                                     values=sorted(country_code_to_name.values()), 
                                     readonly=True, enable_events=True,
                                     font=get_font(FONT_SIZE_BASE), 
                                     background_color=COLOR_WHITE,
                                     size=(35, 1)),
                        ],
                    ], expand_x=True, pad=SPACING_MD),
                ],
                [
                    sg.Column([
                        [
                            sg.Text('Рубрика', font=get_font(FONT_SIZE_MD), 
                                    text_color=COLOR_TEXT_PRIMARY, pad=(0, SPACING_XS)),
                            sg.Column([
                                [
                                    sg.Input(key='-IN_RUBRIC-', disabled=True,
                                             size=(35, 1), expand_x=True,
                                             font=get_font(FONT_SIZE_BASE), 
                                             background_color=COLOR_BACKGROUND_SECONDARY),
                                ],
                            ], expand_x=True, pad=(SPACING_MD, 0)),
                            sg.Column([
                                [
                                    sg.Button('Выбрать', key='-BTN_RUBRIC-', 
                                              **button_style),
                                ],
                            ], element_justification='right', pad=(SPACING_SM, 0)),
                        ],
                    ], expand_x=True, pad=SPACING_MD),
                ],
            ], **frame_style, expand_x=True),
        ],
        
        # Города
        [
            sg.Frame('Города для парсинга', layout=[
                [
                    sg.Column(list(checkbox_layouts.values()), 
                              expand_x=True, expand_y=True, 
                              background_color=COLOR_BACKGROUND),
                ],
            ], **frame_style, size=(None, int(screen_height / 3)), 
               expand_x=True, expand_y=True),
        ],
        
        # Кнопки управления
        [
            sg.Column([
                [
                    sg.Button('✅ OK', size=(10, 1), key='-BTN_OK-', 
                              **button_style),
                    sg.Button('🗀 Выделить всё', size=(14, 1), key='-BTN_SELECT_ALL-', 
                              **button_secondary_style),
                    sg.Button('🗅 Снять выделение', size=(18, 1), key='-BTN_DESELECT_ALL-', 
                              **button_secondary_style),
                ],
            ], expand_x=True, element_justification='right', 
               background_color=COLOR_BACKGROUND, pad=SPACING_MD),
        ],
    ]

    window_title = 'Generate links' if running_linux() else 'Генератор ссылок'
    window = sg.Window(window_title, layout=layout, auto_size_text=True,
                       finalize=True, font=get_font(FONT_SIZE_BASE), 
                       modal=True, keep_on_top=True,
                       resizable=True, size=(700, 550), 
                       min_size=(600, 450))

    setup_text_widget(window['-IN_QUERY-'].widget, window.TKroot,
                      menu_clear=False, set_focus=True)

    setup_text_widget(window['-IN_RUBRIC-'].widget, window.TKroot,
                      menu_clear=False, menu_paste=False, menu_cut=False)

    def update_checkbox_layouts(country_name: str) -> None:
        """Делает видимым фрейм с чекбоксами, которые
        принадлежат `country_name`.

        Args:
            country_name: Название страны.
        """
        for country_code, column_element in checkbox_layouts.items():
            if country_code_to_name[country_code] == country_name:
                column_element.update(visible=True)
            else:
                column_element.update(visible=False)

        # Сброс рубрик
        rubric_input = window['-IN_RUBRIC-']  # noqa: F821
        rubric_input.metadata = None
        rubric_input.update(value='Без рубрики')

    def select_checkboxes(country_name: str, state: bool = True) -> None:
        """Выбирает все чекбоксы, которые принадлежат `country_name`.

        Args:
            country_name: Название страны.
            state: Желаемое состояние чекбоксов.
        """
        country_code = country_name_to_code[country_name]
        for element in sum(checkbox_layouts[country_code].Rows, []):
            element.update(state)

    def get_checkboxes(state: bool | None) -> list[sg.Checkbox]:
        """Возвращает все чекбоксы.

        Args:
            state: Требование к состоянию чекбокса.

        Returns:
            Чекбоксы с указанным `state`.
        """
        all_checkboxes: list[sg.Checkbox] = sum(sum([x.Rows for x in checkbox_layouts.values()], []), [])
        if isinstance(state, bool):
            all_checkboxes = [x for x in all_checkboxes if x.get() == state]

        return all_checkboxes

    def get_selected_urls(query: str) -> list[str]:
        """Получает все отмеченные чекбоксы среди всех фреймов и генерирует URL.

        Args:
            query: Запрос пользователя.

        Returns:
            Список URL.
        """
        urls = []
        rubric = window['-IN_RUBRIC-'].metadata  # noqa: F821
        for checkbox in get_checkboxes(state=True):
            metadata = checkbox.metadata
            base_url = f'https://2gis.{metadata["domain"]}/{metadata["code"]}'
            rest_url = f'/search/{url_query_encode(query)}'
            if rubric:
                rest_url += f'/rubricId/{rubric["code"]}'

            rest_url += '/filters/sort=name'

            url = base_url + rest_url
            urls.append(url)

        return urls

    # Устанавливаем макет по умолчанию
    update_checkbox_layouts(country_code_to_name[default_city_code])

    # Список результирующих URL
    ret_urls = []

    # Основной цикл обработки событий
    while True:
        event, values = window.read()

        if event in (None, ):
            break

        elif event == '-COUNTRY-':
            update_checkbox_layouts(values['-COUNTRY-'])

        elif event == '-BTN_SELECT_ALL-':
            select_checkboxes(values['-COUNTRY-'], True)

        elif event == '-BTN_DESELECT_ALL-':
            select_checkboxes(values['-COUNTRY-'], False)

        elif event == '-BTN_RUBRIC-':
            rubric_dict = gui_rubric_selector(is_russian=values['-COUNTRY-'] == 'Россия')
            if rubric_dict:
                rubric_input = window['-IN_RUBRIC-']
                rubric_label = rubric_dict['label']
                rubric_input.update(value=rubric_label)
                if rubric_label == 'Без рубрики':
                    rubric_input.metadata = None
                else:
                    rubric_input.metadata = rubric_dict
                    window['-IN_QUERY-'].update(value=rubric_label)

        elif event == '-BTN_OK-':
            if not values['-IN_QUERY-'].strip():
                gui_error_popup('Необходимо ввести запрос!\n\nВведите поисковый запрос для генерации ссылок.')
                continue

            if not get_checkboxes(state=True):
                gui_error_popup('Необходимо выбрать города!\n\nВыберите хотя бы один город для парсинга.')
                continue

            ret_urls = get_selected_urls(values['-IN_QUERY-'])
            break

    window.close()
    del window

    return ret_urls
