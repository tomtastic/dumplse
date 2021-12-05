#!/usr/bin/env python3
"""Dump all chat messages for a given www.lse.co.uk user or ticker"""
import argparse

# import json
import sys
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from colorama import Fore


def get_arguments():
    """Get the command line arguments, and check if they're files"""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--user", help="Dump user")
    group.add_argument("--ticker", help="Dump ticker")
    parser.add_argument("--posts", help="Max posts to return", type=int)
    args = parser.parse_args()
    if args.user:
        args.user = args.user.lower()
    if args.ticker:
        args.ticker = args.ticker.upper()
    return (args.user, args.ticker, args.posts)


@dataclass
class UserPost:
    """Objects describing users posts"""

    username: str
    ticker: str
    currprice: float
    date: str
    title: str
    text: str


# Maximum chat pages to dump
GET_MAX = 500

ALERT = {"class": "alert__list-item"}
NEXT_PAGE = {"tag": "a", "class": "pager__link pager__link--next"}
LAST_PAGE = {"tag": "a", "class": "pager__link pager__link--next pager__link--disabled"}

MSG = {
    "class": "share-chat-message__message-content",
    "name": {"tag": "p", "class": "share-chat-message__details--username"},
    "details": {"tag": "p", "class": "share-chat-message__details"},
    "title": {"tag": "div", "class": "share-chat-message__status-bar"},
    "date": {"tag": "span", "class": "share-chat-message__status-bar-time"},
    "text": {"tag": "p", "class": "share-chat-message__message-text"},
}


def dump_user(username):
    """Attempt to print all user posts"""
    user_url = "https://www.lse.co.uk/profiles/" + username
    posts_retrieved = 0
    all_posts = []
    for page_num in range(1, GET_MAX):
        try:
            page = requests.get(user_url + "/?page=" + str(page_num))
        except requests.exceptions.RequestException as get_error:
            print(f"{Fore.RED}[!] Error: {get_error}{Fore.RESET}")
            sys.exit(1)

        soup = BeautifulSoup(page.content, "html.parser")
        alerts = soup.find(class_=ALERT["class"])
        post_elems = soup.find_all(class_=MSG["class"])
        next_page_elem = soup.find(NEXT_PAGE["tag"], class_=NEXT_PAGE["class"])
        last_page_elem = soup.find(LAST_PAGE["tag"], class_=LAST_PAGE["class"])

        if len(post_elems) == 0:
            print(f"{Fore.RED}[!] Nothing found{Fore.RESET}")
            if alerts is not None:
                print(f"{Fore.RED}[!] {(alerts.text).split('.')[0]}{Fore.RESET}")
            sys.exit(1)

        for post in post_elems:
            if POSTS_MAX is not None:
                if posts_retrieved >= POSTS_MAX:
                    sys.exit(0)

            name_elem = post.find(MSG["name"]["tag"], class_=MSG["name"]["class"])
            # No good class to find this with, but usually found at index 1 :
            share_elem = post.find_all(
                MSG["details"]["tag"], class_=MSG["details"]["class"]
            )[1]
            price_elem = post.find_all(
                MSG["details"]["tag"], class_=MSG["details"]["class"]
            )[3]
            title_elem = post.find(MSG["title"]["tag"], class_=MSG["title"]["class"])
            date_elem = post.find(MSG["date"]["tag"], class_=MSG["date"]["class"])
            text_elem = post.find(MSG["text"]["tag"], class_=MSG["text"]["class"])

            # Trim the elements, and assign to an object
            share = share_elem.text.replace("Posted in: ", "")
            price = price_elem.text.replace("Price: ", "").lstrip()
            title = title_elem.text.replace(date_elem.text, "")
            text = text_elem.text.strip()

            try:
                text_elem.br.replace_with("\n")
            except AttributeError:
                pass

            user_post = UserPost(
                name_elem.text, share, price, date_elem.text, title, text
            )
            all_posts.append(user_post)

            # Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET
            print(
                f"{(Fore.GREEN + user_post.username)}"
                f'{Fore.BLUE + " [" + user_post.ticker + "]"}'
                f'{(" @" + user_post.currprice + Fore.RESET)} '
                f'{("(" + user_post.date + ")"):20} '
                f"{Fore.CYAN}{user_post.title}{Fore.RESET}"
            )
            print(f"{user_post.text}")
            print()

            posts_retrieved += 1

        if last_page_elem is not None:
            sys.exit(1)

        if next_page_elem is None:
            print(f"{Fore.RED}[!] No more pages found?{Fore.RESET}")
            sys.exit(1)

    print(f"{Fore.RED}[!] Exceeded GET_MAX({GET_MAX}) pages.{Fore.RESET}")


def dump_ticker(ticker_symbol):
    """Attempt to print all ticker posts"""
    ticker_url = "https://www.lse.co.uk/ShareChat.asp?ShareTicker=" + ticker_symbol
    posts_retrieved = 0
    all_posts = []
    for page_num in range(1, GET_MAX):
        try:
            page = requests.get(ticker_url + "&page=" + str(page_num))
        except requests.exceptions.RequestException as get_error:
            print(f"{Fore.RED}[!] Error: {get_error}{Fore.RESET}")
            sys.exit(1)

        soup = BeautifulSoup(page.content, "html.parser")
        alerts = soup.find(class_=ALERT["class"])
        post_elems = soup.find_all(class_=MSG["class"])
        next_page_elem = soup.find(NEXT_PAGE["tag"], class_=NEXT_PAGE["class"])
        last_page_elem = soup.find(LAST_PAGE["tag"], class_=LAST_PAGE["class"])

        if len(post_elems) == 0:
            print(f"{Fore.RED}[!] Nothing found{Fore.RESET}")
            if alerts is not None:
                print(f"{Fore.RED}[!] {(alerts.text).split('.')[0]}{Fore.RESET}")
            sys.exit(1)

        for post in post_elems:
            if POSTS_MAX is not None:
                if posts_retrieved >= POSTS_MAX:
                    sys.exit(0)

            name_elem = post.find(MSG["name"]["tag"], class_=MSG["name"]["class"])
            # No good class to find this with, but usually found at index 1 :
            price_elem = post.find_all(
                MSG["details"]["tag"], class_=MSG["details"]["class"]
            )[1]
            title_elem = post.find(MSG["title"]["tag"], class_=MSG["title"]["class"])
            date_elem = post.find(MSG["date"]["tag"], class_=MSG["date"]["class"])
            text_elem = post.find(MSG["text"]["tag"], class_=MSG["text"]["class"])

            # Trim the elements, and assign to an object
            price = price_elem.text.replace("Price: ", "").lstrip()
            title = title_elem.text.replace(date_elem.text, "")
            text = text_elem.text.strip()

            try:
                text_elem.br.replace_with("\n")
            except AttributeError:
                pass

            user_post = UserPost(
                name_elem.text, ticker_symbol, price, date_elem.text, title, text
            )
            all_posts.append(user_post)

            # Fore: BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, RESET
            print(
                f"{(Fore.GREEN + user_post.username)}"
                f'{Fore.BLUE + " [" + user_post.ticker + "]"}'
                f'{(" @" + user_post.currprice + Fore.RESET)} '
                f'{("(" + user_post.date + ")"):20} '
                f"{Fore.CYAN}{user_post.title}{Fore.RESET}"
            )
            print(f"{user_post.text}")
            print()

            posts_retrieved += 1

        if last_page_elem is not None:
            sys.exit(1)

        if next_page_elem is None:
            print(f"{Fore.RED}[!] No more pages found?{Fore.RESET}")
            sys.exit(1)

    print(f"{Fore.RED}[!] Exceeded GET_MAX({GET_MAX}) pages.{Fore.RESET}")


(user, ticker, POSTS_MAX) = get_arguments()

if user:
    dump_user(user)
if ticker:
    dump_ticker(ticker)