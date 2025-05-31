import requests
from bs4 import BeautifulSoup
import csv
import time


BASE_URL = 'https://ru.wikipedia.org/wiki/Категория:Животные_по_алфавиту'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}

def get_letter_counts(max_pages=None):
    letter_counts = {}
    session = requests.Session()
    url = BASE_URL
    pages_processed = 0

    while True:
        try:
            response = session.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Ошибка при запросе страницы: {e}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')

        category_div = soup.find('div', {'id': 'mw-pages'})
        if not category_div:
            print("Не удалось найти раздел с категориями на странице.")
            break

        for ul in category_div.find_all('ul'):
            for li in ul.find_all('li'):
                title = li.get_text()
                if title:
                    first_letter = title[0].upper()
                    if first_letter.isalpha():
                        letter_counts[first_letter] = letter_counts.get(first_letter, 0) + 1
                        pages_processed += 1

                        if pages_processed % 100 == 0:
                            print(f"Обработано записей: {pages_processed}")

                        if max_pages and pages_processed >= max_pages:
                            print("Достигнут лимит обработанных страниц.")
                            return letter_counts

        next_link = soup.find('a', string='Следующая страница')
        if next_link and 'href' in next_link.attrs:
            next_href = next_link['href']
            url = 'https://ru.wikipedia.org' + next_href
            time.sleep(1) 
        else:
            break

    return letter_counts

def save_to_csv(letter_counts, filename='beasts.csv'):
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        for letter in sorted(letter_counts):
            writer.writerow([letter, letter_counts[letter]])
    print(f"Результаты сохранены в файл: {filename}")

if __name__ == '__main__':
    counts = get_letter_counts(max_pages=2000)  # Если нужно обработать все страницы - поставьте значение None
    if counts:
        for letter, count in sorted(counts.items()):
            print(f"{letter}: {count}")
        save_to_csv(counts)
    else:
        print("Не удалось получить данные.")
