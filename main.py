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

def get_html(url):
    global session
    time.sleep(0.1)

    r = session.get(url, headers=headers)
    if r.status_code == 200:
        html = r.text
        return html


def get_link_category_spares(url):
    html = get_html(url)
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find("div", {"id": "content"})
        if container:
            links_categories = container.find_all('a')
            links_categories = [(i.text, i.get('href')) for i in links_categories]
            return links_categories


def get_link_category(url):
    html = get_html(url)
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        container = soup.find("div", class_='models')
        if container:
            links_categories = container.find_all('a')
            links_categories = [(i.text, i.get('href')) for i in links_categories]
            return links_categories


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
            links = [i.get('href') for i in links if i.get('itemprop', '') == 'url']
            result.extend(links)
            right_button = soup.find('a', class_='paging__right')

            if not right_button:
                return result
            page_num += 1
            end = f'?page={page_num}'
        else:
            return result


def strip_custom(string):
    for _ in range(len(string)):
        string = string.strip('\n')
        string = string.strip('\t')
        string = string.strip(' ')

    return string


def parse_description(soup):

    result = {}
    ul = soup.find_all('ul')
    h = soup.find_all('h2')
    for i in range(len(soup.find_all('ul'))):

        if h[i].text == 'Кросс коды':
            cross_codes = [[strip_custom(j) for j in i.text.split(' - ')] for i in ul[i].find_all('li')]
            cross_codes_dict = {}
            for elem in cross_codes:
                if not cross_codes_dict.get(elem[0], False):
                    cross_codes_dict[elem[0]] = [elem[1]]
                else:
                    cross_codes_dict[elem[0]].append(elem[1])


            result['analogs'] = [{i[0]:i[1]} for i in cross_codes_dict.items()]


        elif h[i].text == 'Подходит для следующих модификаций:':
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
    sources = []

    sources = soup.find('div', class_='product-short__image').findAll('source')
    for source in sources:
        if source.get('srcset', False):
                s = source['srcset']
                if (s.endswith('.jpg') or s.endswith('.jpeg') or s.endswith('.png')) and (not s.endswith('placeholder.png')):
                    print(source['srcset'])
        elif source.get('data-srcset', False):
                s = source['data-srcset']
                if (s.endswith('.jpg') or s.endswith('.jpeg') or s.endswith('.png')) and (not s.endswith('placeholder.png')):
                    print(source['data-srcset'])


    # sources.extend([p.find_all('source') for p in pictures])
    # for source in sources:
    #     if source.get('srcset', False):
    #         s = source['srcset']
    #         if s.endswith('.jpg') or s.endswith('.jpeg') or s.endswith('.png'):
    #             print(source['srcset'])

    # sources = [p.find_all('source') for p in pictures]
    # # отфильтровывает теги source без аттрибута 'data-srcset'
    # sources_ = []
    #
    # for source in sources:
    #     for source_ in source:
    #         if source_.get('srcset', False):
    #             if source_['srcset'].endswith('.jpg'):
    #                 print(source_['srcset'])





    # img_links = [l['data-srcset'] for l in sources if l.get('data-srcset', False) and l['data-srcset'].endswith('.jpg')]
    # print(img_links)
    # for picture in pictures:
    #     sources = picture.find_all('source')
    #     img_links = [l['data-srcset'] for l in sources if l.get('data-srcset', False) and l['data-srcset'].endswith('.jpg')]
    #     print(img_links)
        # for s in sources:
        #     try:
        #         print(s['data-srcset'])
        #     except:
        #         continue

        # meta = img.find('meta')
        #
        # if meta:
        #     sting_tag = str(meta)  # стрингуем объект bs4
        #     link_re = re.search(r'https\S+', sting_tag)
        #     link = link_re.group(0)
        #     link = link[:len(link) - 1]
        #     links.append(link)
        # else:
        #     link = img['src']
        #     links.append(link)

    return links



def parse_page(url):
    html = get_html(url)
    if html:
        soup = BeautifulSoup(html, "lxml")
        container_header = soup.find("div", class_='product-summary')
        container_description = soup.find("div", class_='product-description')
        images = parse_image(soup)
        content = {
            'title': container_header.find('h1', class_='product__head').text,
            'brand': [i.find('meta') for i in container_header.find_all('td') if "Бренд" in i.text][0]['content'],
            'params': [{"name": strip_custom(j.find_all('td')[0].text), "value": strip_custom(j.find_all('td')[1].text)} for j in [i for i in container_header.find('table', class_='attribute_table_off').find_all('tr')]]
            }
        if images:
            content['images'] = images
        if container_description:
            for key, value in parse_description(container_description).items():
                content[key] = value


        return content


def main():
    content_list = []

    HOST = 'https://tachka.ru'
    categories = get_link_category_spares(HOST + '/zapchasti')

    for category in categories:
        if not category:
            continue
        link = category[1]
        spare = category[0]
        links_manufacturers = get_link_category(HOST + link)
        print("Запчасть: " + spare)


        for elem_1 in links_manufacturers:

            if not elem_1:
                continue
            link = elem_1[1]
            manufacturer = elem_1[0]
            print("Марка авто: " + manufacturer)
            links_models = get_link_category(HOST + link)
            for elem_2 in links_models:

                if not elem_2:
                    continue
                link = elem_2[1]
                model = elem_2[0]
                print('Модель авто: ' + model)

                link_range = get_link_category(HOST + link)
                for elem_3 in link_range:
                    if not elem_3:
                        continue
                    link = elem_3[1]
                    range_model = elem_3[0]
                    print(range_model)
                    links = get_product_links(HOST + link)
                print(f"Собрано {len(links)} ссылок. Парсинг...")
                for link in links:
                    print(f"Парсинг: {HOST + link}")
                    try:
                        content_page = parse_page(HOST + link)
                        content_page['group'] = spare
                        content_page['applicab_model'] = [
                            {
                                "manufacturer": manufacturer,
                                "name": model,
                                "range": range_model
                            }
                        ]
                        content_list.append(content_page)
                    except Exception:
                        continue


    ####
    with open('result.json', 'w', encoding='utf-8') as f:
        f.write(json.dumps(content_list, ensure_ascii=False))


if __name__ == '__main__':
    session = requests.Session()
    main()



