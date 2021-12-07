#!/usr/bin/env python3
"""Dump all chat messages for a given www.lse.co.uk user or ticker"""
import argparse
import json
import sys
import time
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from colorama import Fore


def get_arguments():
    """Parse the command arguments"""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--user", "-u", help="Dump user")
    group.add_argument("--ticker", "-t", help="Dump ticker")
    parser.add_argument("--posts", "-p", help="Max posts to return", type=int)
    parser.add_argument("--json", "-j", help="Print posts as JSON", action="store_true")
    args = parser.parse_args()
    if args.posts < 1 or args.posts > 2 ** 14:
        # Default 25 posts per page, max pages ~= 500, ergo 2^14 (16384)
        # pylint: disable=raising-bad-type
        raise parser.error("posts value must be between 1 and 16384")
    if args.user:
        args.user = args.user.lower()
    if args.ticker:
        args.ticker = args.ticker.upper()
    return (args.user, args.ticker, args.posts, args.json)


@dataclass
class ChatPost:
    """Object describing a chat post"""

    username: str
    ticker: str
    atprice: float
    date: str
    title: str
    text: str

    def __str__(self):
        """Magic-method to pretty-print our object"""
        return (
            f"{(Fore.GREEN + self.username):20}"
            f'{Fore.BLUE + " [" + self.ticker + "]"}'
            f'{(" @" + self.atprice + Fore.RESET)} '
            f'{("(" + self.date + ")"):20} '
            f"{Fore.CYAN}{self.title}{Fore.RESET}\n"
            f"{self.text}\n"
        )

    def as_json(self):
        """Method to format our object as JSON"""
        return json.dumps(
            {
                "username": self.username,
                "ticker": self.ticker,
                "atprice": self.atprice,
                "date": self.date,
                "title": self.title,
                "text": self.text,
            },
            indent=4,
        )


def get_posts_from_page(soup, ticker_symbol):
    """
    Attempt to extract all chat messages from a beautiful soup page object
    (optional) ticker_symbol argument, hints we're parsing all posts for a given share
    """
    page_posts = []

    msg = {
        "class": "share-chat-message__message-content",
        "name": {"tag": "p", "class": "share-chat-message__details--username"},
        "details": {"tag": "p", "class": "share-chat-message__details"},
        "title": {"tag": "div", "class": "share-chat-message__status-bar"},
        "date": {"tag": "span", "class": "share-chat-message__status-bar-time"},
        "text": {"tag": "p", "class": "share-chat-message__message-text"},
    }

    post_elems = soup.find_all(class_=msg["class"])

    if len(post_elems) == 0:
        print(f"{Fore.RED}[!] Nothing found{Fore.RESET}", file=sys.stderr)
        return page_posts

    for post in post_elems:
        elem = {}
        elem["name"] = post.find(
            msg["name"]["tag"], class_=msg["name"]["class"]
        ).getText()
        # details element contains {share name, opinion, share price at date of posting}
        elem["details"] = post.find_all(
            msg["details"]["tag"], class_=msg["details"]["class"]
        )
        if ticker_symbol:
            _ticker = ticker_symbol
            elem["price"] = elem["details"][1]
        else:
            _ticker = elem["details"][1].text.replace("Posted in: ", "")
            elem["price"] = elem["details"][3]

        elem["title"] = post.find(msg["title"]["tag"], class_=msg["title"]["class"])
        elem["date"] = post.find(
            msg["date"]["tag"], class_=msg["date"]["class"]
        ).getText()
        elem["text"] = post.find(
            msg["text"]["tag"], class_=msg["text"]["class"]
        ).getText()

        # Trim the elements, and assign to an object
        price = elem["price"].text.replace("Price: ", "").lstrip()
        title = elem["title"].text.replace(elem["date"], "")

        chat_post = ChatPost(
            elem["name"], _ticker, price, elem["date"], title, elem["text"]
        )
        page_posts.append(chat_post)

    return page_posts


def detect_alerts(soup):
    """Detect login alert errors in soup object"""
    alert_tags = {"tag": "li", "class": "alert alert--error"}
    # alert_tags = {"tag": "li", "class": "alert__list-item"}
    alerts = soup.find(class_=alert_tags["class"])
    if alerts is not None:
        # print(f"{Fore.RED}[!] Alert detected: {(alert_msg).split('.')[0]}{Fore.RESET}")
        for alert in alerts.find_all(alert_tags["tag"]):
            if alert.getText() == "Login failed":
                # false positive
                return False
            else:
                print(
                    f"{Fore.RED}[!] Alert detected: {alert.getText()}{Fore.RESET}",
                    file=sys.stderr,
                )
        return True
    return False


if __name__ == "__main__":
    # Define how to detect additional pages of chat messages
    NEXT_PAGE = {"tag": "a", "class": "pager__link pager__link--next"}
    LAST_PAGE = {
        "tag": "a",
        "class": "pager__link pager__link--next pager__link--disabled",
    }

    # Be nice to the LSE server
    PAGE_PAUSE = 3
    PAGES_MAX = 500

    # Keep the chat post objects in this list
    ALL_POSTS = []

    # Parse the command arguments
    (user, ticker, POSTS_MAX, as_json) = get_arguments()

    if user:
        url = "https://www.lse.co.uk/profiles/" + user + "/?page="
    if ticker:
        url = "https://www.lse.co.uk/ShareChat.asp?ShareTicker=" + ticker + "&page="

    for page_num in range(1, PAGES_MAX):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15"
            }
            page = requests.get(url + str(page_num), headers=headers)
        except requests.exceptions.RequestException as get_error:
            print(f"{Fore.RED}[!] Error: {get_error}{Fore.RESET}", file=sys.stderr)
            sys.exit(1)

        page_soup = BeautifulSoup(page.content, "html.parser")

        # On occasion, LSE will enforce logins before chat can be viewed :<
        if detect_alerts(page_soup):
            break

        for posts in get_posts_from_page(page_soup, ticker):
            ALL_POSTS.append(posts)

        if page_soup.find(NEXT_PAGE["tag"], class_=NEXT_PAGE["class"]) is None:
            print(f"{Fore.RED}[!] No more pages found?{Fore.RESET}", file=sys.stderr)
            break
        if page_soup.find(LAST_PAGE["tag"], class_=LAST_PAGE["class"]) is not None:
            print(f"{Fore.GREEN}[+] Last chat page parsed{Fore.RESET}", file=sys.stderr)
            break
        if POSTS_MAX is not None:
            if len(ALL_POSTS) >= POSTS_MAX:
                # We don't want any more chat posts than we have now
                break

        time.sleep(PAGE_PAUSE)


    if as_json:
        print("[", end="")
        for index, chatpost in enumerate(ALL_POSTS[:POSTS_MAX]):
            print(chatpost.as_json(), end="")
            if index < len(ALL_POSTS[:POSTS_MAX]) - 1:
                print(",")
        print("]")
    else:
        for chatpost in ALL_POSTS[:POSTS_MAX]:
            print(chatpost)
