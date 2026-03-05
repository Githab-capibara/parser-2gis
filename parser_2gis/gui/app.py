from __future__ import annotations

import queue
import threading
import webbrowser
from functools import partial
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from ..common import GUI_ENABLED, running_linux, running_windows
from ..logger import logger, setup_cli_logger, setup_gui_logger
from ..paths import image_data, image_path
from ..runner import GUIRunner
from ..version import version
from .city_selector import gui_city_selector
from .error_popup import gui_error_popup
from .settings import gui_settings
from .theme import (COLOR_ACCENT, COLOR_ACCENT_HOVER, COLOR_BACKGROUND,
                    COLOR_BACKGROUND_SECONDARY, COLOR_BORDER, COLOR_ERROR,
                    COLOR_LOG_CRITICAL, COLOR_LOG_ERROR, COLOR_LOG_WARNING,
                    COLOR_LOG_INFO, COLOR_LOG_SUCCESS, COLOR_TEXT_PRIMARY,
                    COLOR_TEXT_SECONDARY, COLOR_WHITE, ELEMENT_HEIGHT_LG,
                    ELEMENT_HEIGHT_MD, FONT_SIZE_BASE, FONT_SIZE_LG, FONT_SIZE_MD,
                    FONT_SIZE_SM, FONT_SIZE_XL, RADIUS_LG, RADIUS_MD, SPACING_LG,
                    SPACING_MD, SPACING_SM, SPACING_XS, apply_theme, get_font)
from .utils import (ensure_gui_enabled, generate_event_handler,
                    setup_text_widget)

if TYPE_CHECKING:
    from ..config import Configuration

if GUI_ENABLED:
    import tkinter as tk

    import PySimpleGUI as sg


@ensure_gui_enabled
def gui_app(urls: Optional[List[str]], output_path: str, format: str, config: Configuration) -> None:
    """Запуск GUI.

    Args:
        urls: URL-адреса 2GIS с результатами для сбора.
        output_path: Путь к файлу результата.
        format: Формат `csv`, `xlsx` или `json`.
        config: Пользовательская конфигурация.
        
    Примечание:
        Функция включает улучшенную обработку ошибок и потоков.
    """
    try:
        # Применяем современную тему
        apply_theme('modern')

        # Устанавливаем иконку (если функция доступна в версии PySimpleGUI)
        if hasattr(sg, 'set_global_icon'):
            sg.set_global_icon(image_data('icon', 'png'))

        # Настраиваем основной GUI logger (очередь для потокобезопасного логгирования)
        log_queue: queue.Queue[Tuple[str, str]] = queue.Queue()  # Очередь сообщений лога (уровень, сообщение)
        setup_gui_logger(log_queue, config.log)

        # Настраиваем CLI logger после создания очереди GUI logger
        setup_cli_logger(config.log)

        # Формат результата
        default_result_format = format if format else 'csv'
        result_filetype: Dict[str, List[Tuple[str, str]]] = {
            'csv': [('CSV Table', '*.csv')],
            'xlsx': [('Microsoft Excel Spreadsheet', '*.xlsx')],
            'json': [('JSON', '*.json')]
        }

        # Если URL не передан, создаём пустой список
        if urls is None:
            urls = []
            
    except Exception as e:
        logger.error('Ошибка при инициализации GUI: %s', e, exc_info=True)
        gui_error_popup(f'Критическая ошибка при инициализации GUI:\n{str(e)}')
        return

    # Современные стили для элементов
    button_style = {'button_color': (COLOR_WHITE, COLOR_ACCENT),
                    'pad': (SPACING_SM, SPACING_SM)}

    input_style = {'background_color': COLOR_WHITE,
                   'text_color': COLOR_TEXT_PRIMARY,
                   'font': get_font(FONT_SIZE_BASE)}

    frame_style = {'background_color': COLOR_BACKGROUND,
                   'title_color': COLOR_TEXT_PRIMARY,
                   'font': get_font(FONT_SIZE_MD, 'bold'),
                   'pad': (SPACING_MD, SPACING_MD)}

    # Макет окна - современный дизайн с боковой панелью
    layout = [
        # Верхняя панель с заголовком и настройками
        [
            sg.Column([
                [
                    sg.Text('Парсер 2GIS', font=get_font(FONT_SIZE_XL, 'bold'),
                            text_color=COLOR_TEXT_PRIMARY, pad=(SPACING_LG, SPACING_MD)),
                    sg.Text(f'v{version}', font=get_font(FONT_SIZE_SM),
                            text_color=COLOR_TEXT_SECONDARY, pad=(0, SPACING_MD)),
                ],
            ], background_color=COLOR_BACKGROUND, pad=0),
            sg.Column([
                [
                    sg.Button('', image_data=image_data('settings'), key='-BTN_SETTINGS-',
                              tooltip=f'Настройки: {config.path}',
                              button_color=(COLOR_TEXT_SECONDARY, COLOR_BACKGROUND),
                              border_width=0, pad=(SPACING_SM, SPACING_MD)),
                ],
            ], element_justification='right', background_color=COLOR_BACKGROUND, pad=0),
        ],

        # Основная рабочая область
        [
            sg.Frame('Параметры парсинга', expand_x=True, layout=[
                [
                    sg.Column([
                        [
                            sg.Text('URL для парсинга', font=get_font(FONT_SIZE_MD),
                                    text_color=COLOR_TEXT_SECONDARY, pad=(0, SPACING_XS)),
                        ],
                        [
                            sg.Input(key='-IN_URL-', use_readonly_for_disable=True, expand_x=True,
                                     font=get_font(FONT_SIZE_BASE), background_color=COLOR_WHITE),
                            sg.Column([
                                [
                                    sg.Button('Города', key='-BTN_CITIES-', size=(10, 1),
                                              button_color=(COLOR_WHITE, COLOR_ACCENT), border_width=0),
                                    sg.Button('Категории', key='-BTN_CATEGORIES_MODE-', size=(14, 1),
                                              button_color=(COLOR_WHITE, COLOR_ACCENT), border_width=0),
                                    sg.Button('Редактор', key='-BTN_URLS-', size=(10, 1),
                                              button_color=(COLOR_WHITE, COLOR_ACCENT), border_width=0),
                                ],
                            ], element_justification='right', pad=((SPACING_SM, 0), 0)),
                        ],
                    ], expand_x=True, pad=SPACING_LG),
                ],
            ], **frame_style, relief='flat'),
        ],
        
        # Настройки результата
        [
            sg.Frame('Результат', expand_x=True, layout=[
                [
                    sg.Column([
                        [
                            sg.Text('Формат файла', font=get_font(FONT_SIZE_MD), 
                                    text_color=COLOR_TEXT_SECONDARY, pad=(0, SPACING_XS)),
                        ],
                        [
                            sg.Combo(key='-FILE_FORMAT-', default_value=default_result_format,
                                     values=['csv', 'xlsx', 'json'], readonly=True, enable_events=True,
                                     font=get_font(FONT_SIZE_BASE), background_color=COLOR_WHITE,
                                     size=(10, 1)),
                            sg.Text('Путь к файлу', font=get_font(FONT_SIZE_MD), 
                                    text_color=COLOR_TEXT_SECONDARY, pad=((SPACING_LG, SPACING_XS), 0)),
                        ],
                        [
                            sg.Input(key='-OUTPUT_PATH-', expand_x=True,
                                     default_text='' if output_path is None else output_path,
                                     font=get_font(FONT_SIZE_BASE), background_color=COLOR_WHITE),
                            sg.FileSaveAs(key='-OUTPUT_PATH_BROWSE-', button_text='Обзор',
                                          size=(8, 1), button_color=(COLOR_WHITE, COLOR_ACCENT),
                                          default_extension=f'.{default_result_format}',
                                          file_types=result_filetype[default_result_format]),
                        ],
                    ], expand_x=True, pad=SPACING_LG),
                ],
            ], **frame_style, relief='flat'),
        ],

        # Лог выполнения
        [
            sg.Frame('Лог выполнения', expand_x=True, expand_y=True, layout=[
                [
                    sg.Multiline(key='-LOG-', size=(80, 15), expand_x=True, expand_y=True,
                                 autoscroll=True, reroute_stdout=True, reroute_stderr=True,
                                 echo_stdout_stderr=True, font=get_font(FONT_SIZE_BASE, 'normal'),
                                 background_color=COLOR_BACKGROUND_SECONDARY,
                                 text_color=COLOR_TEXT_PRIMARY,
                                 no_scrollbar=False),
                ],
            ], **frame_style, relief='flat'),
        ],

        # Нижняя панель с логотипом и кнопками управления
        [
            sg.Column([
                [
                    sg.Image(data=image_data('logo'), key='-IMG_LOGO-',
                             enable_events=True, background_color=COLOR_BACKGROUND,
                             tooltip='Открыть GitHub репозиторий'),
                ],
            ], size=(80, 80), pad=(SPACING_LG, SPACING_MD)),

            sg.Column([
                [
                    sg.Image(key='-IMG_LOADING-', visible=False,
                             background_color=COLOR_BACKGROUND),
                ],
            ], expand_x=True, element_justification='center', pad=SPACING_LG),

            sg.Column([
                [
                    sg.Button('▶ Запуск', key='-BTN_START-', size=(12, 1),
                              button_color=(COLOR_WHITE, COLOR_ACCENT),
                              border_width=0, font=get_font(FONT_SIZE_MD, 'bold'),
                              pad=((SPACING_MD, SPACING_SM), SPACING_MD)),
                    sg.Button('⏹ Стоп', key='-BTN_STOP-', size=(10, 1),
                              button_color=(COLOR_WHITE, '#FF9500'),
                              border_width=0, font=get_font(FONT_SIZE_MD, 'bold'),
                              visible=False, pad=((SPACING_SM, SPACING_SM), SPACING_MD)),
                    sg.Button('✕ Выход', size=(10, 1),
                              button_color=(COLOR_WHITE, COLOR_ERROR),
                              border_width=0, font=get_font(FONT_SIZE_MD),
                              key='-BTN_EXIT-', pad=((SPACING_SM, SPACING_LG), SPACING_MD)),
                ],
            ], element_justification='right', pad=0),
        ],
    ]

    # tkinter может иметь проблемы с кодировкой кириллицы на Linux (панель инструментов, заголовок),
    # поэтому заголовок окна будет на английском. Это не критично.
    window_title = 'Parser 2GIS' if running_linux() else 'Парсер 2GIS'

    # Главное окно с современными параметрами
    window = sg.Window(
        window_title,
        layout,
        auto_size_text=True,
        finalize=True,
        font=get_font(FONT_SIZE_BASE),
        margins=(0, 0),
        use_custom_titlebar=False,
        keep_on_top=False,
        resizable=True,
        size=(1000, 700),
    )

    # Настраиваем текстовые виджеты
    setup_text_widget(window['-IN_URL-'].widget, window.TKroot, menu_clear=False, set_focus=True)
    setup_text_widget(window['-OUTPUT_PATH-'].widget, window.TKroot, menu_clear=False)
    setup_text_widget(window['-LOG-'].widget, window.TKroot, menu_paste=False, menu_cut=False)

    # Запрещаем пользователю редактировать консоль лога,
    # блокируем все клавиши кроме Ctrl+C, ←, ↑, →, ↓
    def log_key_handler(e: tk.Event) -> str | None:
        if e.char == '\x03' or e.keysym in ('Left', 'Up', 'Right', 'Down'):
            return None

        return 'break'

    window['-LOG-'].widget.bind('<Key>', log_key_handler)
    window['-LOG-'].widget.bind('<<Paste>>', lambda e: 'break')
    window['-LOG-'].widget.bind('<<Cut>>', lambda e: 'break')

    # Включаем очередь логирования для обработки в главном цикле
    # log_queue уже создан выше для setup_gui_logger

    # Курсор-рука для логотипа
    window['-IMG_LOGO-'].widget.config(cursor='hand2')

    # Устанавливаем изображение кнопки настроек при наведении/нажатии
    def change_settings_image(image_name: str) -> None:
        window['-BTN_SETTINGS-'].update(image_data=image_data(image_name))

    window['-BTN_SETTINGS-'].TKButton.bind(
        '<Button>' if running_windows() else '<Enter>',
        generate_event_handler(partial(change_settings_image, 'settings_inverted')))

    window['-BTN_SETTINGS-'].TKButton.bind(
        '<ButtonRelease>' if running_windows() else '<Leave>',
        generate_event_handler(partial(change_settings_image, 'settings')))

    # Перемещаем курсор в конец поля URL
    window['-IN_URL-'].widget.icursor('end')

    # Поток парсинга с блокировкой для потокобезопасности
    parsing_thread: GUIRunner | None = None
    parsing_thread_lock = threading.Lock()  # Блокировка для доступа к parsing_thread

    def parsing_thread_running() -> bool:
        """Проверка состояния потока с блокировкой."""
        with parsing_thread_lock:
            return parsing_thread is not None and parsing_thread.is_alive()

    # Обновление элемента URL в соответствии со списком `urls`
    def update_urls_input() -> None:
        urls_length = len(urls) if isinstance(urls, list) else 0
        if urls_length == 0:
            window['-IN_URL-'].update('', disabled=False)
        elif urls_length == 1:
            window['-IN_URL-'].update(urls[0], disabled=False)
        else:
            def get_plural() -> str:
                last_1d = urls_length % 10
                last_2d = urls_length % 100
                if 11 <= last_2d <= 19:
                    return 'ссылок'
                if last_1d == 1:
                    return 'ссылка'
                elif 2 <= last_1d <= 4:
                    return 'ссылки'
                return 'ссылок'

            window['-IN_URL-'].update(f'<{len(urls)} {get_plural()}>', disabled=True)

    update_urls_input()

    # Установка цветов фона логирования по уровням - современные цвета
    log_colors = {
        'CRITICAL': COLOR_LOG_CRITICAL,
        'ERROR': COLOR_LOG_ERROR,
        'WARNING': COLOR_LOG_WARNING,
        'INFO': COLOR_LOG_INFO,
        'SUCCESS': COLOR_LOG_SUCCESS,
    }

    # Предварительное определение тегов логирования с современными цветами
    for level, color in log_colors.items():
        tag = f'Multiline(None,{color},None)'
        # Проверяем наличие атрибута tags для совместимости со старыми версиями PySimpleGUI
        if hasattr(window['-LOG-'], 'tags') and hasattr(window['-LOG-'].tags, 'add'):
            window['-LOG-'].tags.add(tag)
        window['-LOG-'].widget.tag_configure(tag, background=color)

    # Сохраняем приоритет тега выделения наверху
    window['-LOG-'].widget.tag_raise('sel')

    # Главный цикл обработки событий
    while True:
        try:
            event, values = window.Read(timeout=50)
        except Exception as e:
            logger.error('Ошибка при чтении событий окна: %s', e)
            break

        # Выход из приложения
        if event in (None, '-BTN_EXIT-'):
            # Корректное завершение потока с timeout для предотвращения утечки ресурсов
            try:
                if parsing_thread_running():
                    with parsing_thread_lock:
                        if parsing_thread is not None:
                            logger.info('Завершение потока парсинга...')
                            parsing_thread.stop()
                            # Ждем завершения потока с timeout (5 секунд)
                            parsing_thread.join(timeout=5.0)
                            # Проверяем, завершился ли поток
                            if parsing_thread.is_alive():
                                logger.warning('Поток парсинга не завершился корректно в течение 5 секунд')
                            else:
                                logger.debug('Поток парсинга успешно завершён')
            except Exception as e:
                logger.error('Ошибка при завершении потока парсинга: %s', e)
            finally:
                break

        # Запуск настроек
        elif event == '-BTN_SETTINGS-':
            gui_settings(config)

        # Запуск редактора URL
        elif event == '-BTN_URLS-':
            # Синхронизация URL с элементом ввода
            if not window['-IN_URL-'].Disabled:
                urls = [values['-IN_URL-']]

            ret_urls = gui_urls_editor(urls)
            # Проверка возвращаемого значения на None
            if ret_urls is not None and isinstance(ret_urls, list):
                urls = ret_urls
                update_urls_input()

        # Запуск селектора городов
        elif event == '-BTN_CITIES-':
            # Синхронизация URL с элементом ввода
            if not window['-IN_URL-'].Disabled:
                urls = [values['-IN_URL-']]

            # Запускаем селектор городов
            selected_cities = gui_city_selector(config)
            if selected_cities:
                # Запрашиваем поисковый запрос у пользователя
                query = sg.popup_get_text('Введите поисковый запрос:', title='Генерация URL по городам',
                                          default_text='Организации', font=get_font(FONT_SIZE_BASE))
                if query:
                    # Запрашиваем рубрику (опционально)
                    if sg.popup_yes_no('Выбрать рубрику?', title='Генерация URL по городам') == 'Yes':
                        from .rubric_selector import gui_rubric_selector
                        rubric_dict = gui_rubric_selector()
                        rubric = rubric_dict if rubric_dict and rubric_dict.get('code') else None
                    else:
                        rubric = None

                    # Генерируем URL по выбранным городам
                    from ..common import generate_city_urls
                    generated_urls = generate_city_urls(selected_cities, query, rubric)
                    urls.extend(generated_urls)
                    update_urls_input()
                    logger.info('Добавлено %d URL для городов: %s', len(generated_urls),
                               ', '.join([city['name'] for city in selected_cities]))

        # Запуск парсинга по категориям
        elif event == '-BTN_CATEGORIES_MODE-':
            # Синхронизация URL с элементом ввода
            if not window['-IN_URL-'].Disabled:
                urls = [values['-IN_URL-']]

            # Запускаем селектор городов
            selected_cities = gui_city_selector(config)
            if selected_cities:
                # Запускаем селектор категорий
                from .category_selector import gui_category_selector
                selected_categories = gui_category_selector()
                
                if selected_categories:
                    # Запрашиваем папку для сохранения
                    import tkinter as tk
                    from pathlib import Path
                    
                    # Создаём диалог выбора папки с обработкой ошибок
                    root = None
                    try:
                        root = tk.Tk()
                        root.withdraw()
                        output_dir = tk.filedialog.askdirectory(
                            title='Выберите папку для сохранения результатов',
                            initialdir=Path.cwd()
                        )
                    finally:
                        if root:
                            root.destroy()
                    
                    if output_dir:
                        # Запускаем параллельный парсинг
                        from ..parallel_parser import ParallelCityParser
                        
                        logger.info('Запуск параллельного парсинга по %d категориям', len(selected_categories))
                        logger.info('Города: %s', [c['name'] for c in selected_cities])
                        
                        # Создаём парсер
                        parser = ParallelCityParser(
                            cities=selected_cities,
                            categories=selected_categories,
                            output_dir=output_dir,
                            config=config,
                            max_workers=3,
                        )
                        
                        def on_progress(success: int, failed: int, filename: str) -> None:
                            logger.info('Прогресс: успешно=%d, ошибок=%d, файл=%s', success, failed, filename)
                        
                        # Запускаем в отдельном потоке с обработкой ошибок
                        def run_parser():
                            try:
                                output_file = str(Path(output_dir) / 'merged_result.csv')
                                result = parser.run(output_file=output_file, progress_callback=on_progress)
                                if result:
                                    logger.info('Параллельный парсинг завершён успешно!')
                                else:
                                    logger.error('Параллельный парсинг завершён с ошибками')
                            except Exception as e:
                                logger.error('Ошибка при параллельном парсинге: %s', e, exc_info=True)
                        
                        threading.Thread(target=run_parser, daemon=True).start()
                        
                        sg.popup_info(
                            f'Запущен параллельный парсинг!\n\nГорода: {len(selected_cities)}\nКатегории: {len(selected_categories)}\n\nРезультаты будут сохранены в: {output_dir}',
                            title='Парсинг запущен',
                            font=get_font(FONT_SIZE_BASE),
                            background_color=COLOR_BACKGROUND,
                            text_color=COLOR_TEXT_PRIMARY,
                            button_color=(COLOR_WHITE, COLOR_ACCENT)
                        )

        # Выбор формата выходного файла
        elif event == '-FILE_FORMAT-':
            file_format = values['-FILE_FORMAT-']
            if file_format in result_filetype:
                window['-OUTPUT_PATH_BROWSE-'].FileTypes = result_filetype[file_format]
                window['-OUTPUT_PATH_BROWSE-'].DefaultExtension = f'.{file_format}'

        # Клик по логотипу
        elif event == '-IMG_LOGO-':
            webbrowser.open('https://github.com/interlark/parser-2gis')

        # Нажатие кнопки остановки
        elif event == '-BTN_STOP-':
            # Потокобезопасная остановка через флаг и polling
            if parsing_thread_running():
                logger.warning('Парсинг остановлен пользователем.')
                with parsing_thread_lock:
                    if parsing_thread is not None:
                        parsing_thread.stop()

                # Отключаем кнопку до полной остановки потока (polling)
                window['-BTN_STOP-'].update(disabled=True)

        # Нажатие кнопки запуска
        elif event == '-BTN_START-':
            try:
                # Проверка пути к выходному файлу
                if not values['-OUTPUT_PATH-']:
                    gui_error_popup('Отсутствует путь результирующего файла!\n\nУкажите файл для сохранения результатов парсинга.')
                    continue

                # Проверка URL
                if not values['-IN_URL-']:
                    gui_error_popup('Отсутствует URL!\n\nВведите URL для парсинга или используйте редактор ссылок.')
                    continue

                # Проверка формата результата
                if values['-FILE_FORMAT-'] not in ('csv', 'xlsx', 'json'):
                    gui_error_popup('Формат результирующего файла должен быть csv, xlsx или json!')
                    continue

                # Проверка соответствия формата результата расширению файла
                output_extension = values['-OUTPUT_PATH-'].split('.')[-1].lower()
                if output_extension != values['-FILE_FORMAT-']:
                    gui_error_popup(f'Расширение результирующего файла должно быть *.{values["-FILE_FORMAT-"]}!')
                    continue

                # Синхронизация URL с элементом ввода
                if not window['-IN_URL-'].Disabled:
                    urls = [values['-IN_URL-']]

                # Запуск парсера с блокировкой для потокобезопасности
                if not parsing_thread_running():
                    try:
                        with parsing_thread_lock:
                            parsing_thread = GUIRunner(
                                urls, 
                                values['-OUTPUT_PATH-'], 
                                values['-FILE_FORMAT-'], 
                                config
                            )
                            parsing_thread.start()
                        logger.info('Поток парсинга запущен')
                    except Exception as runner_error:
                        logger.error('Ошибка при запуске парсера: %s', runner_error, exc_info=True)
                        gui_error_popup(f'Ошибка при запуске парсинга:\n{str(runner_error)}')

                    # Активируем кнопку остановки, если она была отключена
                    window['-BTN_STOP-'].update(disabled=False)
                    
            except Exception as e:
                logger.error('Непредвиденная ошибка при запуске парсинга: %s', e, exc_info=True)
                gui_error_popup(f'Критическая ошибка при запуске:\n{str(e)}')

        # Опрос очереди логирования
        while True:
            try:
                log_level, log_msg = log_queue.get(block=False)
            except queue.Empty:
                break
            else:
                # Вывод сообщения в лог
                window['-LOG-'].update(log_msg, append=True,
                                       background_color_for_value=log_colors.get(log_level, None))

        # Переключение кнопок запуска/остановки
        if parsing_thread_running():
            if window['-BTN_START-'].visible:
                window['-BTN_START-'].update(visible=False)

            if not window['-BTN_STOP-'].visible:
                window['-BTN_STOP-'].update(visible=True)

            if not window['-IMG_LOADING-'].visible:
                window['-IMG_LOADING-'].update(visible=True)

            # Запускаем анимацию загрузки
            try:
                window['-IMG_LOADING-'].update_animation(image_path('loading'), time_between_frames=50)
            except Exception as anim_error:
                logger.debug('Ошибка анимации загрузки: %s', anim_error)
        else:
            if not window['-BTN_START-'].visible:
                window['-BTN_START-'].update(visible=True)

            if window['-BTN_STOP-'].visible:
                window['-BTN_STOP-'].update(visible=False)

            if window['-IMG_LOADING-'].visible:
                window['-IMG_LOADING-'].update(visible=False)

    # Закрытие окна с обработкой ошибок
    try:
        window.close()
        del window
        logger.debug('GUI окно закрыто')
    except Exception as close_error:
        logger.error('Ошибка при закрытии GUI окна: %s', close_error)
