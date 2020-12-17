#!/usr/bin/env python3
"""Dump all chat messages for a given www.lse.co.uk user"""
import sys
import requests
from bs4 import BeautifulSoup
from colorama import Fore

user = sys.argv[1].lower()

if len(sys.argv) > 2:
    POSTS_MAX = int(sys.argv[2])
else:
    POSTS_MAX = None

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

posts_retrieved = 0
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
        if POSTS_MAX is not None or 0:
            if posts_retrieved >= POSTS_MAX:
                sys.exit(0)

        name_elem = post.find(MSG['name']['tag'], class_=MSG['name']['class'])
        share_elem = post.find_all(MSG['share']['tag'], class_=MSG['share']['class'])[1]
        title_elem = post.find(MSG['title']['tag'], class_=MSG['title']['class'])
        date_elem = post.find(MSG['date']['tag'], class_=MSG['date']['class'])
        text_elem = post.find(MSG['text']['tag'], class_=MSG['text']['class'])

        try:
            text_elem.br.replace_with("\n")
        except AttributeError:
            pass

        # Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET
        print(f'{(Fore.GREEN + name_elem.text + Fore.BLUE + " [" + share_elem.text + "]" + Fore.RESET):20} '
              f'{("(" + date_elem.text + ")"):20} '
              f'{Fore.CYAN}{title_elem.text.replace(date_elem.text, "")}{Fore.RESET}')
        print(f'{text_elem.text.strip()}')
        print()

        posts_retrieved += 1

    if last_page_elem is not None:
        break
