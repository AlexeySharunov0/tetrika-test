import pytest
import requests
from unittest.mock import patch, MagicMock, mock_open, call
import csv
import sys
import os

# Добавляем папку solution в sys.path для импорта task2
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../solution')))
import task2 # Импортируем ваш скрипт

# --- Моки HTML-контента ---
MOCK_HTML_PAGE_1 = """
<html><body>
<div id="mw-pages">
  <a href="/wiki/Категория:Животные_по_алфавиту?pagefrom=БАРСУК#mw-pages">Следующая страница</a>
  <div class="mw-category-group"><h3>А</h3><ul><li><a>Аист</a></li><li><a>Акула</a></li></ul></div>
  <div class="mw-category-group"><h3>Б</h3><ul><li><a>Бабочка</a></li></ul></div>
</div>
</body></html>
"""

MOCK_HTML_PAGE_2 = """
<html><body>
<div id="mw-pages">
  <a href="/wiki/Категория:Животные_по_алфавиту?pageuntil=АИСТ#mw-pages">Предыдущая страница</a>
  <div class="mw-category-group"><h3>Б</h3><ul><li><a>Барсук</a></li></ul></div>
  <div class="mw-category-group"><h3>В</h3><ul><li><a>Волк</a></li><li><a>Выдра</a></li></ul></div>
</div>
</body></html>
"""

MOCK_HTML_PAGE_SINGLE_NO_NEXT = """
<html><body>
<div id="mw-pages">
  <div class="mw-category-group"><h3>Я</h3><ul><li><a>Ястреб</a></li></ul></div>
</div>
</body></html>
"""

MOCK_HTML_NO_MW_PAGES = "<html><body><div>No div here</div></body></html>"

MOCK_HTML_NO_ITEMS_NO_NEXT = """
<html><body>
<div id="mw-pages">
</div>
</body></html>
"""

MOCK_HTML_NON_ALPHA_START = """
<html><body>
<div id="mw-pages">
  <div class="mw-category-group"><h3>А</h3><ul><li><a>Аист</a></li><li><a>123Animal</a></li><li><a>(Вид) Собака</a></li></ul></div>
</div>
</body></html>
"""

# --- Хелпер для создания моков ответа ---
def create_mock_response(content, status_code=200, url=""):
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.content = content.encode('utf-8')
    mock_resp.status_code = status_code
    mock_resp.url = url
    mock_resp.raise_for_status = MagicMock()
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.HTTPError(f"Mock HTTP Error {status_code} for {url}")
    return mock_resp

# --- Фикстуры ---
@pytest.fixture
def mock_requests_session():
    with patch('requests.Session') as MockSession:
        mock_session_instance = MockSession.return_value
        yield mock_session_instance

@pytest.fixture
def mock_time_sleep():
    with patch('time.sleep', return_value=None) as mock_sleep:
        yield mock_sleep

# --- Тесты для get_letter_counts ---

def test_get_letter_counts_single_page_success(mock_requests_session, mock_time_sleep):
    """Тестирует успешное получение данных с одной страницы."""
    mock_response = create_mock_response(MOCK_HTML_PAGE_SINGLE_NO_NEXT)
    mock_requests_session.get.return_value = mock_response

    expected_counts = {'Я': 1}
    actual_counts = task2.get_letter_counts()

    assert actual_counts == expected_counts
    mock_requests_session.get.assert_called_once_with(
        task2.BASE_URL,
        headers=task2.HEADERS,
        timeout=10
    )
    mock_time_sleep.assert_not_called()

def test_get_letter_counts_multiple_pages(mock_requests_session, mock_time_sleep):
    """Тестирует обработку нескольких страниц и пагинацию."""
    mock_response_page1 = create_mock_response(MOCK_HTML_PAGE_1)
    mock_response_page2 = create_mock_response(MOCK_HTML_PAGE_2)

    def side_effect_get(url, headers, timeout):
        if url == task2.BASE_URL:
            return mock_response_page1
        elif "pagefrom=БАРСУК" in url: # Ссылка со страницы 1
            return mock_response_page2
        raise ValueError(f"Unexpected URL in test: {url}")

    mock_requests_session.get.side_effect = side_effect_get

    expected_counts = {'А': 2, 'Б': 2, 'В': 2}
    actual_counts = task2.get_letter_counts()

    assert actual_counts == expected_counts
    assert mock_requests_session.get.call_count == 2
    mock_requests_session.get.assert_any_call(task2.BASE_URL, headers=task2.HEADERS, timeout=10)
    mock_requests_session.get.assert_any_call(
        'https://ru.wikipedia.org/wiki/Категория:Животные_по_алфавиту?pagefrom=БАРСУК#mw-pages',
        headers=task2.HEADERS, timeout=10
    )
    mock_time_sleep.assert_called_once_with(1)

def test_get_letter_counts_max_items_limit(mock_requests_session, mock_time_sleep, capsys):
    """Тестирует параметр max_pages (фактически max_items)."""
    mock_response = create_mock_response(MOCK_HTML_PAGE_1) # 3 элемента: Аист, Акула, Бабочка
    mock_requests_session.get.return_value = mock_response

    limit = 2
    expected_counts = {'А': 2} # Только Аист, Акула
    actual_counts = task2.get_letter_counts(max_pages=limit)

    assert actual_counts == expected_counts
    captured = capsys.readouterr()
    assert "Достигнут лимит обработанных страниц." in captured.out
    mock_time_sleep.assert_not_called() # Лимит достигнут на первой странице

def test_get_letter_counts_request_exception(mock_requests_session, mock_time_sleep, capsys):
    """Тестирует обработку исключения при запросе страницы."""
    mock_requests_session.get.side_effect = requests.RequestException("Test network error")

    expected_counts = {}
    actual_counts = task2.get_letter_counts()

    assert actual_counts == expected_counts
    captured = capsys.readouterr()
    assert "Ошибка при запросе страницы: Test network error" in captured.out
    mock_time_sleep.assert_not_called()

def test_get_letter_counts_no_category_div(mock_requests_session, mock_time_sleep, capsys):
    """Тестирует случай, когда на странице нет основного div с категориями."""
    mock_response = create_mock_response(MOCK_HTML_NO_MW_PAGES)
    mock_requests_session.get.return_value = mock_response

    expected_counts = {}
    actual_counts = task2.get_letter_counts()

    assert actual_counts == expected_counts
    captured = capsys.readouterr()
    assert "Не удалось найти раздел с категориями на странице." in captured.out
    mock_time_sleep.assert_not_called()

def test_get_letter_counts_no_items_on_page(mock_requests_session, mock_time_sleep):
    """Тестирует страницу, где есть div категорий, но нет элементов списка (и нет след. страницы)."""
    mock_response = create_mock_response(MOCK_HTML_NO_ITEMS_NO_NEXT)
    mock_requests_session.get.return_value = mock_response

    expected_counts = {}
    actual_counts = task2.get_letter_counts()

    assert actual_counts == expected_counts
    mock_requests_session.get.assert_called_once()
    mock_time_sleep.assert_not_called()

def test_get_letter_counts_ignore_non_alpha_start(mock_requests_session, mock_time_sleep):
    """Тестирует игнорирование записей, начинающихся не с буквы."""
    mock_response = create_mock_response(MOCK_HTML_NON_ALPHA_START)
    mock_requests_session.get.return_value = mock_response

    # Ожидаем только 'А' из "Аист".
    # "(Вид) Собака" начинается с '(', "123Animal" начинается с '1'.
    # Оба будут пропущены проверкой first_letter.isalpha().
    expected_counts = {'А': 1}
    actual_counts = task2.get_letter_counts()

    assert actual_counts == expected_counts
    mock_time_sleep.assert_not_called()

def test_get_letter_counts_item_processing_print(mock_requests_session, mock_time_sleep, capsys):
    """Тестирует вывод информации об обработанных записях (pages_processed % 100 == 0)."""
    items_html_parts = []
    # Генерируем 100 элементов, чтобы вызвать print
    for i in range(100):
        # Используем разные первые буквы, чтобы избежать перезаписи в словаре,
        # хотя для этого теста это не критично, но более реалистично.
        # Для простоты оставим одну букву, т.к. проверяем только print.
        items_html_parts.append(f"<li><a>Животное{i}</a></li>")
    items_html = "".join(items_html_parts)

    mock_html_100_items = f"""
    <html><body>
    <div id="mw-pages">
      <div class="mw-category-group"><h3>Ж</h3><ul>{items_html}</ul></div>
    </div>
    </body></html>
    """
    mock_response = create_mock_response(mock_html_100_items)
    mock_requests_session.get.return_value = mock_response

    # Вызываем функцию, результат не так важен, как вывод
    task2.get_letter_counts(max_pages=100) # Установим max_pages, чтобы он точно обработал 100

    captured = capsys.readouterr()
    assert "Обработано записей: 100" in captured.out
    assert "Достигнут лимит обработанных страниц." in captured.out # т.к. max_pages=100
    mock_time_sleep.assert_not_called() # Все на одной странице

# --- Тесты для save_to_csv ---

@patch('builtins.open', new_callable=mock_open)
@patch('csv.writer')
def test_save_to_csv_success(mock_csv_writer_module, m_open, capsys):
    """Тестирует успешное сохранение данных в CSV."""
    letter_counts = {'Б': 5, 'А': 10, 'В': 2}
    # Используем имя файла по умолчанию из функции save_to_csv
    expected_filename = 'beasts.csv'

    mock_writer_instance = mock_csv_writer_module.return_value
    task2.save_to_csv(letter_counts) # Используем имя файла по умолчанию

    m_open.assert_called_once_with(expected_filename, 'w', encoding='utf-8-sig', newline='')
    mock_csv_writer_module.assert_called_once_with(m_open.return_value)

    expected_calls = [
        call(['А', 10]),
        call(['Б', 5]),
        call(['В', 2])
    ]
    mock_writer_instance.writerow.assert_has_calls(expected_calls)

    captured = capsys.readouterr()
    assert f"Результаты сохранены в файл: {expected_filename}" in captured.out

@patch('builtins.open', new_callable=mock_open)
@patch('csv.writer')
def test_save_to_csv_empty_counts(mock_csv_writer_module, m_open, capsys):
    """Тестирует сохранение пустого набора данных."""
    letter_counts = {}
    expected_filename = 'empty_beasts.csv' # Передаем другое имя для теста
    mock_writer_instance = mock_csv_writer_module.return_value

    task2.save_to_csv(letter_counts, filename=expected_filename)

    m_open.assert_called_once_with(expected_filename, 'w', encoding='utf-8-sig', newline='')
    mock_csv_writer_module.assert_called_once_with(m_open.return_value)
    mock_writer_instance.writerow.assert_not_called()

    captured = capsys.readouterr()
    assert f"Результаты сохранены в файл: {expected_filename}" in captured.out

# --- Тесты для логики в if __name__ == '__main__': ---

@patch('task2.get_letter_counts')
@patch('task2.save_to_csv')
@patch('builtins.print')
def test_main_flow_success(mock_print, mock_save_csv, mock_get_counts):
    """Тестирует основной успешный сценарий выполнения скрипта."""
    sample_counts_value = {'А': 10, 'Б': 5}
    mock_get_counts.return_value = sample_counts_value

    # Эмуляция кода из if __name__ == '__main__':
    # Шаг 1: Вызов get_letter_counts (мокированной)
    counts_from_script = task2.get_letter_counts(max_pages=2000) # Значение из вашего main

    # Шаг 2: Логика обработки результата
    if counts_from_script:
        for letter, count in sorted(counts_from_script.items()):
            mock_print(f"{letter}: {count}") # Это print из цикла в main
        task2.save_to_csv(counts_from_script) # Это вызов мокированной save_to_csv
    else:
        mock_print("Не удалось получить данные.")

    mock_get_counts.assert_called_once_with(max_pages=2000)
    mock_save_csv.assert_called_once_with(sample_counts_value)

    # Проверяем специфичные print вызовы из цикла
    mock_print.assert_any_call("А: 10")
    mock_print.assert_any_call("Б: 5")

    # Убедимся, что сообщение "Не удалось получить данные." НЕ было напечатано
    no_data_message_called = any(
        c == call("Не удалось получить данные.") for c in mock_print.call_args_list
    )
    assert not no_data_message_called, "Сообщение 'Не удалось получить данные.' было вызвано ошибочно."


@patch('task2.get_letter_counts')
@patch('task2.save_to_csv')
@patch('builtins.print')
def test_main_flow_no_data_returned(mock_print, mock_save_csv, mock_get_counts):
    """Тестирует сценарий, когда get_letter_counts не возвращает данных."""
    mock_get_counts.return_value = {} # или None, ваш скрипт обрабатывает {} как "нет данных"

    # Эмуляция кода из if __name__ == '__main__':
    counts_from_script = task2.get_letter_counts(max_pages=2000)

    if counts_from_script: # Это условие будет False
        for letter, count in sorted(counts_from_script.items()):
            mock_print(f"{letter}: {count}")
        task2.save_to_csv(counts_from_script)
    else:
        mock_print("Не удалось получить данные.")

    mock_get_counts.assert_called_once_with(max_pages=2000)
    mock_save_csv.assert_not_called()
    # Проверяем, что было напечатано только сообщение об отсутствии данных
    mock_print.assert_called_once_with("Не удалось получить данные.")