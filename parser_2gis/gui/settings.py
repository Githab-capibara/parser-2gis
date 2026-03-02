from __future__ import annotations

import pydantic

from ..common import (GUI_ENABLED, report_from_validation_error,
                      running_linux, unwrap_dot_dict)
from ..config import Configuration
from ..logger import logger
from .error_popup import gui_error_popup
from .theme import (COLOR_ACCENT, COLOR_BACKGROUND, COLOR_BACKGROUND_SECONDARY,
                    COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
                    COLOR_WHITE, FONT_SIZE_BASE, FONT_SIZE_MD, FONT_SIZE_SM,
                    FONT_SIZE_XL, RADIUS_MD, SPACING_LG, SPACING_MD, SPACING_SM,
                    SPACING_XS, apply_theme, get_font)
from .utils import ensure_gui_enabled

if GUI_ENABLED:
    import PySimpleGUI as sg


@ensure_gui_enabled
def gui_settings(config: Configuration) -> None:
    """Запускает настройки.

    Args:
        config: Конфигурация для изменения.
    """
    # Применяем современную тему
    apply_theme('modern')

    # Стили для элементов
    checkbox_style = {'background_color': COLOR_BACKGROUND,
                      'text_color': COLOR_TEXT_PRIMARY,
                      'font': get_font(FONT_SIZE_BASE),
                      'checkbox_color': COLOR_ACCENT,
                      'pad': ((0, SPACING_MD), (SPACING_SM, SPACING_SM))}
    
    frame_style = {'background_color': COLOR_BACKGROUND,
                   'title_color': COLOR_TEXT_PRIMARY,
                   'font': get_font(FONT_SIZE_MD, 'bold'),
                   'border_width': 1,
                   'border_color': COLOR_BORDER,
                   'pad': (SPACING_MD, SPACING_SM),
                   'element_padding': (SPACING_MD, SPACING_SM),
                   'relief': 'flat'}
    
    spin_style = {'background_color': COLOR_WHITE,
                  'text_color': COLOR_TEXT_PRIMARY,
                  'font': get_font(FONT_SIZE_BASE),
                  'size': (6, 1)}
    
    label_style = {'background_color': COLOR_BACKGROUND,
                   'text_color': COLOR_TEXT_SECONDARY,
                   'font': get_font(FONT_SIZE_SM)}

    # Макет окна - современный дизайн с вкладками настроек
    layout = [
        # Заголовок окна настроек
        [
            sg.Column([
                [
                    sg.Text('Настройки', font=get_font(FONT_SIZE_XL, 'bold'), 
                            text_color=COLOR_TEXT_PRIMARY, pad=(SPACING_LG, SPACING_MD)),
                ],
            ], background_color=COLOR_BACKGROUND, pad=0),
        ],
        
        # Вкладки настроек
        [
            sg.TabGroup([
                [
                    sg.Tab('🌐 Браузер', [
                        [
                            sg.Frame('Основные настройки', layout=[
                                [
                                    sg.Checkbox('Отключить изображения', key='-CHROME.DISABLE_IMAGES-',
                                                tooltip='Отключить изображения для увеличения скорости работы',
                                                default=config.chrome.disable_images,
                                                **checkbox_style),
                                ],
                                [
                                    sg.Checkbox('Запускать развёрнутым', key='-CHROME.START_MAXIMIZED-',
                                                tooltip='Запускать браузер развёрнутым во весь экран',
                                                default=config.chrome.start_maximized,
                                                **checkbox_style),
                                ],
                                [
                                    sg.Checkbox('Скрытый режим (headless)', key='-CHROME.HEADLESS-',
                                                tooltip='Запускать браузер в скрытом виде (без графического интерфейса)',
                                                default=config.chrome.headless,
                                                **checkbox_style),
                                ],
                            ], **frame_style, expand_x=True),
                        ],
                        [
                            sg.Frame('Производительность', layout=[
                                [
                                    sg.Column([
                                        [
                                            sg.Column([
                                                [
                                                    sg.Text('Лимит RAM (МБ)', font=get_font(FONT_SIZE_BASE),
                                                            text_color=COLOR_TEXT_PRIMARY),
                                                    sg.Text('Ограничение памяти браузера', 
                                                            font=get_font(FONT_SIZE_SM),
                                                            text_color=COLOR_TEXT_SECONDARY),
                                                ],
                                            ], expand_x=True, pad=0),
                                            sg.Column([
                                                [
                                                    sg.Spin([x for x in range(1, 100)], 
                                                            size=(8, 1), key='-CHROME.MEMORY_LIMIT-',
                                                            initial_value=config.chrome.memory_limit,
                                                            tooltip='Лимит оперативной памяти браузера (мегабайт)',
                                                            **spin_style),
                                                ],
                                            ], element_justification='right', pad=0),
                                        ],
                                    ], expand_x=True, pad=SPACING_MD),
                                ],
                            ], **frame_style, expand_x=True),
                        ],
                    ], font=get_font(FONT_SIZE_BASE), title_color=COLOR_TEXT_PRIMARY,
                    background_color=COLOR_BACKGROUND, selected_title_color=COLOR_ACCENT,
                    selected_background_color=COLOR_BACKGROUND_SECONDARY),
                    
                    sg.Tab('⚙️ Парсер', [
                        [
                            sg.Frame('Отображение', layout=[
                                [
                                    sg.Checkbox('Показывать города в логе', key='-WRITER.VERBOSE-',
                                                tooltip='Показывать названия обрабатываемых городов в логе',
                                                default=config.writer.verbose,
                                                **checkbox_style),
                                ],
                            ], **frame_style, expand_x=True),
                        ],
                        [
                            sg.Frame('Поведение', layout=[
                                [
                                    sg.Checkbox('Пропускать пустые результаты', key='-PARSER.SKIP_404_RESPONSE-',
                                                tooltip='Пропускать ссылки, вернувшие сообщение "Точных совпадений нет / Не найдено"',
                                                default=config.parser.skip_404_response,
                                                **checkbox_style),
                                ],
                            ], **frame_style, expand_x=True),
                        ],
                        [
                            sg.Frame('Тайминги и лимиты', layout=[
                                [
                                    sg.Column([
                                        [
                                            sg.Column([
                                                [
                                                    sg.Text('Задержка кликов (мс)', font=get_font(FONT_SIZE_BASE),
                                                            text_color=COLOR_TEXT_PRIMARY),
                                                    sg.Text('Пауза между кликами по записям', 
                                                            font=get_font(FONT_SIZE_SM),
                                                            text_color=COLOR_TEXT_SECONDARY),
                                                ],
                                            ], expand_x=True, pad=0),
                                            sg.Column([
                                                [
                                                    sg.Spin([x for x in range(1, 100000)], 
                                                            size=(8, 1), key='-PARSER.DELAY_BETWEEN_CLICKS-',
                                                            initial_value=config.parser.delay_between_clicks,
                                                            tooltip='Задержка между кликами (миллисекунд)',
                                                            **spin_style),
                                                ],
                                            ], element_justification='right', pad=0),
                                        ],
                                    ], expand_x=True, pad=SPACING_MD),
                                ],
                                [
                                    sg.Column([
                                        [
                                            sg.Column([
                                                [
                                                    sg.Text('Лимит записей с URL', font=get_font(FONT_SIZE_BASE),
                                                            text_color=COLOR_TEXT_PRIMARY),
                                                    sg.Text('Максимум записей с одного URL', 
                                                            font=get_font(FONT_SIZE_SM),
                                                            text_color=COLOR_TEXT_SECONDARY),
                                                ],
                                            ], expand_x=True, pad=0),
                                            sg.Column([
                                                [
                                                    sg.Spin([x for x in range(1, 100000)], 
                                                            size=(8, 1), key='-PARSER.MAX_RECORDS-',
                                                            initial_value=config.parser.max_records,
                                                            tooltip='Максимальное количество записей с одного URL',
                                                            **spin_style),
                                                ],
                                            ], element_justification='right', pad=0),
                                        ],
                                    ], expand_x=True, pad=SPACING_MD),
                                ],
                            ], **frame_style, expand_x=True),
                        ],
                    ], font=get_font(FONT_SIZE_BASE), title_color=COLOR_TEXT_PRIMARY,
                    background_color=COLOR_BACKGROUND, selected_title_color=COLOR_ACCENT,
                    selected_background_color=COLOR_BACKGROUND_SECONDARY),
                    
                    sg.Tab('📊 CSV/XLSX', [
                        [
                            sg.Frame('Структура данных', layout=[
                                [
                                    sg.Checkbox('Добавить колонку "Рубрики"', key='-WRITER.CSV.ADD_RUBRICS-',
                                                tooltip='Добавить колонку с рубриками организаций',
                                                default=config.writer.csv.add_rubrics,
                                                **checkbox_style),
                                ],
                                [
                                    sg.Checkbox('Удалить пустые колонки', key='-WRITER.CSV.REMOVE_EMPTY_COLUMNS-',
                                                tooltip='Удалить пустые колонки после завершения парсинга',
                                                default=config.writer.csv.remove_empty_columns,
                                                **checkbox_style),
                                ],
                                [
                                    sg.Checkbox('Удалить дубликаты', key='-WRITER.CSV.REMOVE_DUPLICATES-',
                                                tooltip='Удалить повторяющиеся записи после завершения парсинга',
                                                default=config.writer.csv.remove_duplicates,
                                                **checkbox_style),
                                ],
                            ], **frame_style, expand_x=True),
                        ],
                        [
                            sg.Frame('Дополнительно', layout=[
                                [
                                    sg.Checkbox('Добавлять комментарии к ячейкам', key='-WRITER.CSV.ADD_COMMENTS-',
                                                tooltip='Добавлять комментарии к ячейкам Телефон, E-Mail и т.д.',
                                                default=config.writer.csv.add_comments,
                                                **checkbox_style),
                                ],
                            ], **frame_style, expand_x=True),
                        ],
                        [
                            sg.Frame('Форматирование', layout=[
                                [
                                    sg.Column([
                                        [
                                            sg.Column([
                                                [
                                                    sg.Text('Колонок на сущность', font=get_font(FONT_SIZE_BASE),
                                                            text_color=COLOR_TEXT_PRIMARY),
                                                    sg.Text('Для множественных значений (Телефон_1, Телефон_2...)', 
                                                            font=get_font(FONT_SIZE_SM),
                                                            text_color=COLOR_TEXT_SECONDARY),
                                                ],
                                            ], expand_x=True, pad=0),
                                            sg.Column([
                                                [
                                                    sg.Spin([x for x in range(1, 100)], 
                                                            size=(8, 1), key='-WRITER.CSV.COLUMNS_PER_ENTITY-',
                                                            initial_value=config.writer.csv.columns_per_entity,
                                                            tooltip='Количество колонок для результатов с несколькими значениями',
                                                            **spin_style),
                                                ],
                                            ], element_justification='right', pad=0),
                                        ],
                                    ], expand_x=True, pad=SPACING_MD),
                                ],
                            ], **frame_style, expand_x=True),
                        ],
                    ], font=get_font(FONT_SIZE_BASE), title_color=COLOR_TEXT_PRIMARY,
                    background_color=COLOR_BACKGROUND, selected_title_color=COLOR_ACCENT,
                    selected_background_color=COLOR_BACKGROUND_SECONDARY),
                ],
            ], pad=(SPACING_MD, SPACING_MD), background_color=COLOR_BACKGROUND,
            selected_title_color=COLOR_ACCENT, tab_background_color=COLOR_BACKGROUND_SECONDARY,
            border_width=1, border_color=COLOR_BORDER),
        ],
        
        # Кнопки управления
        [
            sg.Column([
                [
                    sg.Button('💾 Сохранить', size=(14, 1), key='-BTN_SAVE-',
                              button_color=(COLOR_WHITE, COLOR_ACCENT),
                              border_width=0, font=get_font(FONT_SIZE_BASE, 'bold'),
                              pad=((SPACING_MD, SPACING_SM), SPACING_LG)),
                    sg.Button('✕ Отмена', size=(12, 1), key='-BTN_CANCEL-',
                              button_color=(COLOR_TEXT_PRIMARY, COLOR_BACKGROUND_SECONDARY),
                              border_width=0, font=get_font(FONT_SIZE_BASE),
                              pad=((SPACING_SM, SPACING_MD), SPACING_LG)),
                ],
            ], expand_x=True, element_justification='center', background_color=COLOR_BACKGROUND),
        ],
    ]

    window_title = 'Settings' if running_linux() else 'Настройки'
    window = sg.Window(window_title, layout, auto_size_text=True, finalize=True,
                       font=get_font(FONT_SIZE_BASE), modal=True, keep_on_top=True,
                       resizable=True, size=(700, 600), min_size=(600, 500))

    # Основной цикл обработки событий
    while True:
        event, values = window.Read()

        # Закрываем окно по кнопке отмены или закрытию окна
        if event in (None, '-BTN_CANCEL-'):
            break

        # Сохраняем параметры Chrome и других компонентов
        elif event == '-BTN_SAVE-':
            new_parameters_flat = {k.strip('-').lower(): v for k, v in values.items()}
            new_parameters = unwrap_dot_dict(new_parameters_flat)

            try:
                new_configuration = Configuration(**new_parameters)
                config.merge_with(new_configuration)
                config.save_config()
                break
            except pydantic.ValidationError as e:
                errors = []
                errors_report = report_from_validation_error(e, new_parameters)
                for path, description in errors_report.items():
                    arg = description['invalid_value']
                    error_msg = description['error_message']
                    errors.append(f'[*] Поле: {path}, значение: {arg}, ошибка: {error_msg}')

                gui_error_popup('\n\n'.join(errors))
            except Exception as e:
                # Выводим ошибку в консоль и закрываем окно
                logger.error('Ошибка при сохранении параметров:\n%s', e, exc_info=True)
                break

    window.close()
    del window
