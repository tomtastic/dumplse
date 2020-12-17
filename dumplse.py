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
    'class': 'share-chat-message__content-message',
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

for page in range(1, GET_MAX):
    page = requests.get(URL + '/?page=' + str(page))
    soup = BeautifulSoup(page.content, 'html.parser')
    msg_elems = soup.find_all(class_=MSG['class'])
    last_page_elem = soup.find(LAST_PAGE['tag'], class_=LAST_PAGE['class'])
    for msg in msg_elems:
        title_elem = msg.find(MSG['title']['tag'], class_=MSG['title']['class'])
        date_elem = msg.find(MSG['date']['tag'], class_=MSG['date']['class'])
        text_elem = msg.find(MSG['text']['tag'], class_=MSG['text']['class'])
        print(f'{user} : {title_elem.text.replace(date_elem.text, "")}  -  {date_elem.text}')
        print(f'{text_elem.text}')
        print()
    if last_page_elem is not None:
        break
