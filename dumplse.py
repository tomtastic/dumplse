#!/usr/bin/env python3
"""Dump all chat messages for a given www.lse.co.uk user or ticker"""
import argparse
import json
import requests
import sys
import time
from bs4 import BeautifulSoup
from colorama import Fore
from dataclasses import dataclass
from hashlib import sha256
from random import randrange


def get_arguments():
    """Parse the command arguments"""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--user", "-u", help="Dump user", type=str)
    group.add_argument("--ticker", "-t", help="Dump ticker", type=str)
    parser.add_argument(
        "--posts_max",
        "-p",
        help="Maximum number of posts to return",
        type=int,
        default=16384,
    )
    parser.add_argument(
        "--newlines",
        "-n",
        help="Dont strip newlines from posts",
        action="store_true",
    )
    parser.add_argument(
        "--reverse",
        "-r",
        help="Reverse post order",
        action="store_true",
    )
    parser.add_argument("--json", "-j", help="Print posts as JSON", action="store_true")
    parser.add_argument(
        "--debug", "-d", help="Print posts with repr", action="store_true"
    )
    _arg = parser.parse_args()
    if len(sys.argv) == 1:
        # pylint: disable=raising-bad-type
        raise parser.error("you must specify either user or ticker")
    if _arg.posts_max and (_arg.posts_max < 1 or _arg.posts_max > 16384):
        # Default 25 posts per page, max pages ~= 500, ergo 16384
        # pylint: disable=raising-bad-type
        raise parser.error("posts value must be between 1 and 16384")
    if _arg.user:
        _arg.user = _arg.user.lower()
    if _arg.ticker:
        _arg.ticker = _arg.ticker.upper()

    return _arg


@dataclass
class ChatPost:
    """Object describing a chat post"""

    username: str
    ticker: str
    atprice: float
    opinion: str
    date: str
    title: str
    text: str

    def __str__(self):
        """Magic-method to pretty-print our object"""
        if self.opinion == "No Opinion":
            self.opinion = " "
        if self.opinion == "Strong Buy":
            self.opinion = Fore.GREEN + "\u21d1" + Fore.RESET  # ⇑
        if self.opinion == "Weak Buy":
            self.opinion = Fore.GREEN + "\u21e1" + Fore.RESET  # ⇡
        if self.opinion == "Buy":
            self.opinion = Fore.GREEN + "\u2191" + Fore.RESET  # ↑
        if self.opinion == "Hold":
            self.opinion = "\u2192"  # →
        if self.opinion == "Sell":
            self.opinion = Fore.RED + "\u2193" + Fore.RESET  # ↓
        if self.opinion == "Weak Sell":
            self.opinion = Fore.RED + "\u21e3" + Fore.RESET  # ⇣
        if self.opinion == "Strong Sell":
            self.opinion = Fore.RED + "\u21d3" + Fore.RESET  # ⇓

        return (
            f"{(Fore.GREEN + self.username):21}"
            f'{Fore.BLUE + " [" + self.ticker + "]"}'
            f'{(" @" + str(self.atprice) + Fore.RESET)} '
            f'{("(" + self.date + ")"):20} '
            f"{self.opinion} "
            f"{Fore.CYAN}{self.title}{Fore.RESET}\n"
            f"{self.text}\n"
        )

    def hash_post(self) -> str:
        hash = sha256()
        hash.update(bytes(self.date + self.username + self.title + self.text, "utf8"))
        return hash.hexdigest()

    def as_json(self):
        """Method to format our object as JSON"""
        return json.dumps(
            {
                "username": self.username,
                "ticker": self.ticker,
                "atprice": self.atprice,
                "opinion": self.opinion,
                "date": self.date,
                "title": self.title,
                "text": self.text,
                "hash": self.hash_post(),
            },
            indent=4,
        )


def get_posts_from_page(soup, ticker_symbol, with_newlines):
    """
    Returns a list of chat message objects from a beautiful soup page object
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
        if arg.debug:
            print(
                f"DEBUG: Can't find any tags of class : {msg['class']}",
                file=sys.stderr,
            )
            print(
                f"DEBUG: Soup: {soup}",
                file=sys.stderr,
            )
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
            elem["opinion"] = elem["details"][2]
        else:
            _ticker = elem["details"][1].text.replace("Posted in: ", "")
            elem["price"] = elem["details"][3]
            elem["opinion"] = elem["details"][4]

        elem["title"] = post.find(msg["title"]["tag"], class_=msg["title"]["class"])
        elem["date"] = post.find(
            msg["date"]["tag"], class_=msg["date"]["class"]
        ).getText()
        elem["text"] = post.find(msg["text"]["tag"], class_=msg["text"]["class"])
        if with_newlines:
            for br_tag in elem["text"].find_all("br"):
                br_tag.replace_with("\n" + br_tag.text)
        else:
            for br_tag in elem["text"].find_all("br"):
                br_tag.replace_with(" " + br_tag.text)

        # Trim the elements, and assign to an object
        price = elem["price"].text.replace("Price: ", "").lstrip()
        opinion = elem["opinion"].getText()
        title = elem["title"].text.replace(elem["date"], "")

        chat_post = ChatPost(
            elem["name"],
            _ticker,
            price,
            opinion,
            elem["date"],
            title,
            elem["text"].getText(),
        )
        page_posts.append(chat_post)

    return page_posts


def detect_alerts(soup):
    """Detect alert errors in soup object which may cause failure to parse"""
    got_alert = False
    alert_tags = {
        "errors": {"tag": "li", "class": "alert alert--error"},
        "warnings": {"tag": "li", "class": "alert__list-item"},
    }
    alert_errs = soup.find(class_=alert_tags["errors"]["class"])
    alert_warns = soup.find(class_=alert_tags["warnings"]["class"])

    if alert_errs is not None:
        for item in alert_errs.find_all(alert_tags["errors"]["tag"]):
            if item.getText() == "Login failed":
                # Ignore login error alerts
                if arg.debug:
                    print(
                        f"DEBUG: Ignoring (alert_errs) for : {item.getText()}{Fore.RESET}",
                        file=sys.stderr,
                    )
            else:
                got_alert = True
                print(
                    f"{Fore.RED}[!] Alert(error) : {item.getText()}{Fore.RESET}",
                    file=sys.stderr,
                )

    if alert_warns is not None:
        if "refresh the page" in alert_warns.getText():
            if arg.debug:
                print(f"DEBUG: (alert_warns): {alert_warns}", file=sys.stderr)
        else:
            if arg.debug:
                print(f"DEBUG: (alert_warns): {alert_warns}", file=sys.stderr)

    return got_alert


if __name__ == "__main__":
    # Define how to detect additional pages of chat messages
    NEXT_PAGE = {"tag": "a", "class": "pager__link pager__link--next"}
    LAST_PAGE = {
        "tag": "a",
        "class": "pager__link pager__link--next pager__link--disabled",
    }

    # Be nice to the LSE server
    PAGE_PAUSE = randrange(7)
    PAGES_MAX = 500

    # Keep the chat post objects in this list
    ALL_POSTS = []
    SEEN_POSTS: dict[str, bool] = dict()  # [hash_of_post => True]

    # Parse the command arguments
    arg = get_arguments()

    if arg.user:
        url = "https://www.lse.co.uk/profiles/" + arg.user + "/?page="
    if arg.ticker:
        url = "https://www.lse.co.uk/ShareChat.asp?ShareTicker=" + arg.ticker + "&page="

    for page_num in range(1, PAGES_MAX):
        try:
            # firefox on MacOS
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15"
            }
            if arg.debug:
                print(f"[+] Getting {url}")
            page = requests.get(url + str(page_num), headers=headers)
        except requests.exceptions.RequestException as get_error:
            print(f"{Fore.RED}[!] Error: {get_error}{Fore.RESET}", file=sys.stderr)
            sys.exit(1)

        page_soup = BeautifulSoup(page.content, "html.parser")

        # On occasion, LSE will enforce logins before chat can be viewed :<
        if detect_alerts(page_soup):
            break

        soup_posts = get_posts_from_page(page_soup, arg.ticker, arg.newlines)
        if len(soup_posts) == 0:
            break
        for chatpost in soup_posts:
            ALL_POSTS.append(chatpost)
            SEEN_POSTS[chatpost.hash_post()] = True

        if page_soup.find(NEXT_PAGE["tag"], class_=NEXT_PAGE["class"]) is None:
            if arg.debug:
                print(
                    f"DEBUG: Page {page_num}, and no next page found?", file=sys.stderr
                )
            break
        if page_soup.find(LAST_PAGE["tag"], class_=LAST_PAGE["class"]) is not None:
            if arg.debug:
                print("DEBUG: Last chat page parsed", file=sys.stderr)
            break
        if len(ALL_POSTS) >= arg.posts_max:
            # We don't want any more chat posts than we have now
            if arg.debug:
                print(f"DEBUG: ALL_POSTS is >= {arg.posts_max}", file=sys.stderr)
            break

        if arg.debug:
            print(f"DEBUG: Got {len(ALL_POSTS)} posts, sleeping...", file=sys.stderr)
        time.sleep(PAGE_PAUSE)

    if arg.json:
        print("[", end="")
        if arg.reverse:
            for index, chatpost in enumerate(reversed(ALL_POSTS[: arg.posts_max])):
                print(chatpost.as_json(), end="")
                if index < len(ALL_POSTS[: arg.posts_max]) - 1:
                    print(",")
        else:
            for index, chatpost in enumerate(ALL_POSTS[: arg.posts_max]):
                print(chatpost.as_json(), end="")
                if index < len(ALL_POSTS[: arg.posts_max]) - 1:
                    print(",")
        print("]")
    elif arg.debug:
        for chatpost in ALL_POSTS[: arg.posts_max]:
            if chatpost.hash_post() in SEEN_POSTS:
                print("[+] We have seen the hash of this post")
            print(chatpost.hash_post(), end="\n")
            print(repr(chatpost), end="\n\n")
    elif arg.reverse:
        for chatpost in reversed(ALL_POSTS[: arg.posts_max]):
            print(chatpost)
    else:
        for chatpost in ALL_POSTS[: arg.posts_max]:
            print(chatpost)
