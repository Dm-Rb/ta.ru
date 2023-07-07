import requests
from bs4 import BeautifulSoup
import json
import os
import time
import re


#  ------------------------------------------------------------
HOST = 'https://tachka.ru/'
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Connection": 'keep-alive',
    "Host":	"tachka.ru",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"
}
#  ------------------------------------------------------------
session = requests.Session()

def get_html(url):
    global session

    time.sleep(0.1)

    r = session.get(url, headers=headers)
    if r.status_code == 200:
        html = r.text
        return html


def strip_custom(string):
    for _ in range(len(string)):
        string = string.strip('\n')
        string = string.strip('\t')
        string = string.strip(' ')

    return string


def get_links_category(url):
    html = get_html(url)
    categories = []
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find("ul", class_='side-menu')
        li_list = container.find_all('li', class_='side-menu__item')
        for elem in li_list:
            a = elem.find('a')
            if a.get('href', '') != '':
                link = a['href']
                div = a.find('div', class_='side-menu__content')
                if div:
                    if type(div.find('span')) != type(None):
                        div.span.decompose()
                        text = strip_custom(div.text)

                        if text != 'Запчасти':
                            categories.append({'name': text, 'link': HOST + link})

                else:
                    if a['href'] and a.text and a.text != 'Запчасти':
                        categories.append({'name': a.text, 'link': HOST + link})
    return categories


def get_product_links(url):
    page_num = 1
    end = f'?page={page_num}'
    result = []
    while True:
        print(f'Собираю ссылки с {url + end}')
        html = get_html(url + end)
        if html:
            soup = BeautifulSoup(html, 'html.parser')
            container = soup.find("div", class_='catalog-list')
            links = container.findAll('a')
            links = [HOST + i.get('href') for i in links if i.get('itemprop', '') == 'url']
            result.extend(links)
            right_button = soup.find('a', class_='paging__right')

            if not right_button:
                return result
            page_num += 1
            end = f'?page={page_num}'
        else:
            return result


def parse_description(soup):

    result = {}
    try:
        h = [i.text for i in soup.find_all('h2')]
    except:
        h = None
    descr_1 = soup.find('extautoopisan')
    if h:
        for i in range(len(soup.find_all('ul'))):
            ul = soup.find_all('ul')
            if h == 'Кросс коды':
                cross_codes = [[strip_custom(j) for j in i.text.split(' - ')] for i in ul[i].find_all('li')]
                cross_codes_dict = {}
                for elem in cross_codes:
                    if not cross_codes_dict.get(elem[0], False):
                        cross_codes_dict[elem[0]] = [elem[1]]
                    else:
                        cross_codes_dict[elem[0]].append(elem[1])

                result['analogs'] = [{i[0]: i[1]} for i in cross_codes_dict.items()]


            elif h == 'Подходит для следующих модификаций:':
                mod = [[strip_custom(j) for j in i.text.split(' - ')] for i in ul[i].find_all('li')]
                modification = []
                for elem in mod:
                    a = elem[0].split('\n')
                    a = [strip_custom(i) for i in a]

                    modification.append(a)
                result['modifications'] = modification

    return result


def parse_image(soup):
    links = []

    sources = soup.find('div', class_='product-short__image').findAll('source')
    for source in sources:
        if source.get('srcset', False):
                s = source['srcset']
                if (s.endswith('.jpg') or s.endswith('.jpeg') or s.endswith('.png')) and (not s.endswith('placeholder.png')):
                    links.append(source['srcset'])
        elif source.get('data-srcset', False):
                s = source['data-srcset']
                if (s.endswith('.jpg') or s.endswith('.jpeg') or s.endswith('.png')) and (not s.endswith('placeholder.png')):
                    links.append(source['data-srcset'])
    return links


def files_pdf(soup):
    container = soup.find('div', class_='product__files')
    if container:
        files = [{"name": strip_custom(i.text), "link": i['href']} for i in container.find_all('a')]
        return files


def get_categories(soup):
    container = soup.find('div', class_='dh')
    if container:
        categories = [strip_custom(i.text) for i in container.find_all('a') if strip_custom(i.text) != '']
        return categories




def parse_page(url):
    html = get_html(url)
    print(url)
    if html:
        soup = BeautifulSoup(html, "lxml")
        container_header = soup.find("div", class_='product-summary')
        container_description = soup.find("div", class_='product-description')


        content = {
            "url": url,
            'title': container_header.find('h1', class_='product__head').text,
            'brand': [i.find('meta') for i in container_header.find_all('td') if "Бренд" in i.text][0]['content'],
            'params': [{"name": strip_custom(j.find_all('td')[0].text), "value": strip_custom(j.find_all('td')[1].text)} for j in [i for i in container_header.find('table', class_='attribute_table_off').find_all('tr')]]
            }


        categ = get_categories(soup)
        if categ:
            content['sub_categories'] = categ

        images = parse_image(soup)
        if images:
            content['images'] = images

        pdf = files_pdf(soup)
        if pdf:
            content['pdf_files'] = pdf

        if container_description:
            for key, value in parse_description(container_description).items():
                content[key] = value


        return content





if __name__ == '__main__':
    session = requests.Session()

    categories = get_links_category(HOST)

    for category in categories:
        content_list = []
        print(f"Текущая категория: {category['name']}")
        product_links = get_product_links(category['link'])
        for propuct_link in product_links:
            try:
                content = parse_page(propuct_link)
                content_list.append(content)

            except Exception:
                continue

        ####
        with open(f'{category["name"]}.json', 'w', encoding='utf-8') as f:
            f.write(json.dumps(content_list, ensure_ascii=False, indent=2))

