import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from requests_cache import CachedSession
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import (BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, MAIN_PEP_URL,
                       MESSAGE_STRING)
from outputs import control_output
from exceptions import ParserUlTextException
from utils import find_tag, get_response


def pep(session: CachedSession) -> Optional[List]:
    response = get_response(session, MAIN_PEP_URL)
    if not response:
        return
    pep_count = 0
    diff_statuses: List = []
    statuses: Dict = {}
    soup = BeautifulSoup(response.text, features='lxml')
    section_pep = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    table_tag = section_pep.find('table', attrs={'class': 'pep-zero-table'})
    tbody = find_tag(table_tag, 'tbody')
    tr_tags = tbody.find_all('tr')
    for tr in tqdm(tr_tags, desc='Переход по ссылкам таблицы PEP'):
        first_column_tag = find_tag(tr, 'td')
        preview_status = first_column_tag.text[1:]
        pep_a_tag = find_tag(tr, 'a')
        href = pep_a_tag['href']
        pep_link = urljoin(MAIN_PEP_URL, href)
        response = get_response(session, pep_link)
        if not response:
            continue
        pep_count += 1
        soup = BeautifulSoup(response.text, 'lxml')
        dl_tag = soup.find('dl')
        status_string_tag = [
            tag for tag in dl_tag.find_all('dt') if tag.text == 'Status:'
        ]
        status = status_string_tag[0].find_next_sibling().string
        if (preview_status in EXPECTED_STATUS and
                status not in EXPECTED_STATUS[preview_status]):
            diff_statuses.append(
                MESSAGE_STRING.format(pep_link, status,
                                      EXPECTED_STATUS[preview_status])
            )
        statuses[status] = statuses.get(status, 0) + 1
    results = [('Статус', 'Количество')]
    results.extend(statuses.items())
    results.append(('Total', pep_count))
    if diff_statuses:
        status_message = '\n'.join(diff_statuses)
        logging.info(f'Несовпадающие статусы:\n{status_message}')
    return results


def whats_new(session: CachedSession) -> Optional[List]:
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li',
                                              attrs={'class': 'toctree-l1'})
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = section.a
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session: CachedSession) -> Optional[List]:
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            error_msg = 'Текст "All versions" на странице не найден.'
            logging.error(error_msg, stack_info=True)
            raise ParserUlTextException(error_msg)
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session: CachedSession) -> None:
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    table_tag = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(table_tag, 'a',
                          attrs={'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag.get('href')
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main() -> None:
    configure_logging()
    logging.info('Парсер запущен!')

    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')

    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)


if __name__ == '__main__':
    main()
