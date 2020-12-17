#!/usr/bin/env python3
"""Dump all chat messages for a given www.lse.co.uk user"""
import sys
import requests
from bs4 import BeautifulSoup

user = sys.argv[1].lower()
URL = 'https://www.lse.co.uk/profiles/' + user

# Maximum chat pages to dump
GET_MAX = 50

LAST_PAGE = {
    'tag': 'a',
    'class': 'pager__link pager__link--next pager__link--disabled'
    }

MSG = {
    'class': 'share-chat-message__message-content',
    'name': {
            'tag': 'p',
            'class': 'share-chat-message__details--username'
        },
    'share': {
            'tag': 'a',
            'class': 'share-chat-message__link'
        },
    'title': {
            'tag': 'div',
            'class': 'share-chat-message__status-bar'
        },
    'date': {
            'tag': 'span',
            'class': 'share-chat-message__status-bar-time'
        },
    'text': {
            'tag': 'p',
            'class': 'share-chat-message__message-text'
        },
    }

for page_num in range(1, GET_MAX):
    try:
        page = requests.get(URL + '/?page=' + str(page_num))
    except requests.exceptions.RequestException as get_error:
        print(f"[!] Error: {get_error}")
        sys.exit(1)

    soup = BeautifulSoup(page.content, 'html.parser')
    post_elems = soup.find_all(class_=MSG['class'])
    last_page_elem = soup.find(LAST_PAGE['tag'], class_=LAST_PAGE['class'])

    if len(post_elems) == 0:
        print("[!] Nothing found")
        sys.exit(1)

    for post in post_elems:
        name_elem = post.find(MSG['name']['tag'], class_=MSG['name']['class'])
        share_elem = post.find_all(MSG['share']['tag'], class_=MSG['share']['class'])[1]
        title_elem = post.find(MSG['title']['tag'], class_=MSG['title']['class'])
        date_elem = post.find(MSG['date']['tag'], class_=MSG['date']['class'])
        text_elem = post.find(MSG['text']['tag'], class_=MSG['text']['class'])

        try:
            text_elem.br.replace_with("\n")
        except AttributeError:
            pass

        print(f'{(name_elem.text + " [" + share_elem.text + "]"):20} '
              f'{("(" + date_elem.text + ")"):20} '
              f'{title_elem.text.replace(date_elem.text, "")}')
        print(f'{text_elem.text.strip()}')
        print()

    if last_page_elem is not None:
        break
