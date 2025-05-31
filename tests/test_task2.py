import pytest
from unittest.mock import Mock, patch

from solution.task2 import get_letter_counts, save_to_csv


# Тест 1: Проверяем, что функция правильно считает животных с одной страницы
@patch('solution.task2.requests.Session')
def test_get_letter_counts(mock_session):
    # Подготовка фейкового HTML — имитируем реальную структуру Википедии
    mock_html = """
    <html>
      <body>
        <div id="mw-pages">
          <div class="mw-category">
            <div class="mw-category-group">
              <ul>
                <li><a href="/wiki/Акула" title="Акула">Акула</a></li>
                <li><a href="/wiki/Бегемот" title="Бегемот">Бегемот</a></li>
                <li><a href="/wiki/Аист" title="Аист">Аист</a></li>
                <li><a href="/wiki/Баран" title="Баран">Баран</a></li>
                <li><a href="/wiki/Волк" title="Волк">Волк</a></li>
              </ul>
            </div>
          </div>
        </div>
        <a href="/wiki/Категория:Животные_по_алфавиту?from=Г">Следующая страница</a>
      </body>
    </html>
    """

    mock_response = Mock()
    mock_response.content = mock_html.encode('utf-8')
    mock_response.raise_for_status.return_value = None

    mock_session.return_value.get.return_value = mock_response

    # Вызываем функцию с ограничением на 1 страницу
    result = get_letter_counts(max_pages=1)

    # Ожидаем подсчёт:
    # А - 2, Б - 2, В - 1
    assert result == {'А': 2, 'Б': 2, 'В': 1}


# Тест 2: Если нет данных — возвращается пустой словарь
@patch('solution.task2.requests.Session')
def test_get_letter_counts_no_data(mock_session):
    mock_html = """
    <html>
      <body>
        <div id="mw-pages"></div>
      </body>
    </html>
    """
    mock_response = Mock()
    mock_response.content = mock_html.encode('utf-8')
    mock_response.raise_for_status.return_value = None

    mock_session.return_value.get.return_value = mock_response

    result = get_letter_counts(max_pages=1)
    assert result == {}


# Тест 3: Обработка сетевой ошибки — возвращает пустой словарь
@patch('solution.task2.requests.Session')
def test_get_letter_counts_network_error(mock_session):
    mock_session.return_value.get.side_effect = Exception("Connection error")

    result = get_letter_counts(max_pages=1)
    assert result == {}


# Тест 4: Сохранение в CSV — проверяет, что файл создаётся и данные записываются
def test_save_to_csv(tmpdir):
    letter_counts = {'А': 2, 'Б': 1}
    file = tmpdir.join("test_beasts.csv")

    save_to_csv(letter_counts, filename=str(file))

    assert file.exists()
    with open(file, 'r', encoding='utf-8-sig') as f:
        content = f.read()
        assert "А,2\n" in content
        assert "Б,1\n" in content