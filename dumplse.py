#!/usr/bin/env python3
"""Dump chat messages for a given www.lse.co.uk user or ticker"""
import argparse
import asyncio
import requests
import sqlite3
import sys
import time
from bs4 import BeautifulSoup
from colorama import Fore
from dataclasses import dataclass
from datetime import datetime
from halo import Halo
from hashlib import sha256
from random import randrange


def get_arguments() -> argparse.Namespace:
    """Parse the command arguments"""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--user", "-u", help="Dump user", type=str)
    group.add_argument("--ticker", "-t", help="Dump ticker", type=str)
    parser.add_argument(
        "--posts_max",
        "-p",
        help="Maximum number of most recent posts to return",
        type=int,
        default=131072,
    )
    parser.add_argument(
        "--page",
        "-P",
        help="The page to start from",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--newlines",
        "-n",
        help="Dont strip newlines from posts",
        action="store_true",
    )
    parser.add_argument(
        "--save",
        "-s",
        help="Save viewed posts to SQLiteDB, dont show posts again",
        action="store_true",
    )
    parser.add_argument(
        "--debug", "-d", help="Print posts with repr", action="store_true"
    )
    _arg = parser.parse_args()
    if len(sys.argv) == 1:
        # pylint: disable=raising-bad-type
        raise parser.error("you must specify either user or ticker")
    if _arg.page and (_arg.page < 1 or _arg.page > 4096):
        # pylint: disable=raising-bad-type
        raise parser.error("page value must be between 1 and 4096")
    if _arg.posts_max and (_arg.posts_max < 1 or _arg.posts_max > 131072):
        # Default 25 posts per page, max pages ~= 4096, ergo ~82k
        # pylint: disable=raising-bad-type
        raise parser.error("posts value must be between 1 and 131072")
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

    def __str__(self) -> str:
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
            f'{("(" + str(self.date) + ")"):20} '
            f"{self.opinion} "
            f"{Fore.CYAN}{self.title}{Fore.RESET}\n"
            f"{self.text}\n"
        )

    def hash(self) -> str:
        hash = sha256()
        hash.update(bytes(self.date + self.username + self.title + self.text, "utf8"))
        return hash.hexdigest()


def create_db(db_name: str) -> sqlite3.Connection:
    """Creates an SQLite3 database file containing hashes of posts we've seen"""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS posts
            (hash TEXT PRIMARY KEY,
            username TEXT,
            ticker TEXT,
            atprice TEXT,
            opinion TEXT,
            date TEXT,
            title TEXT,
            text TEXT)
        """
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"\rError creating posts table in database : {e}")
    finally:
        cursor.close()
    return conn


def exists_in_db(conn: sqlite3.Connection, hash: str) -> bool:
    """Check if a post hash exists in the database"""
    cursor = conn.cursor()
    try:
        rows = cursor.execute(f'SELECT * FROM posts WHERE hash = "{hash}"').fetchall()
        if len(rows) >= 1:
            return True
    except sqlite3.Error as e:
        print(f"\rError checking hash of post in database : {e}")
    finally:
        cursor.close()
    return False


def add_to_db(conn: sqlite3.Connection, hash: str, p: ChatPost) -> None:
    """Add a hash of a seen post to the database"""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO posts (hash, username, ticker, atprice, opinion, date, title, text) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (hash, p.username, p.ticker, p.atprice, p.opinion, p.date, p.title, p.text),
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"\r[!] Error adding hash of post {repr(p)} to database : {e}")
        conn.rollback()
    finally:
        cursor.close()


def get_posts_from_page(soup: BeautifulSoup, arg: argparse.Namespace) -> list:
    """
    Returns a list of chat message objects from a beautiful soup page object
    (optional) ticker_symbol argument, hints we're parsing all posts for a given share
    """

    def string_to_datetime(post_time: str) -> str:
        # Convert the date string to a datetime object
        if "Today" in str(post_time):
            # "Today 15.32"
            time = str(post_time)[6:]
            todays_date = datetime.today().strftime("%d %b %Y")
            post_time = str(todays_date) + " " + str(time)

        try:
            # "29 Mar 2024 15:32"
            post_time = datetime.strptime(post_time, "%d %b %Y %H:%M")
        except:
            print(f"\r[!] Something went wrong parsing {post_time}")
            pass

        return str(post_time)

    page_posts: list[ChatPost] = []

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
                f"\rDEBUG: Can't find any tags of class : {msg['class']}",
                file=sys.stderr,
            )
            print(
                f"\rDEBUG: Soup: {soup}",
                file=sys.stderr,
            )
        return page_posts

    for post in post_elems:
        elem = {}
        elem["name"] = post.find(
            name=msg["name"]["tag"], attrs=msg["name"]["class"]
        ).getText()
        # details element contains {share name, opinion, share price at date of posting}
        elem["details"] = post.find_all(
            msg["details"]["tag"], attrs=msg["details"]["class"]
        )
        if arg.ticker:
            _ticker = arg.ticker
            elem["price"] = elem["details"][2]
            elem["opinion"] = elem["details"][3]
        else:
            _ticker = elem["details"][1].text.replace("Posted in: ", "")
            elem["price"] = elem["details"][3]
            elem["opinion"] = elem["details"][4]

        elem["title"] = post.find(msg["title"]["tag"], attrs=msg["title"]["class"])
        elem["date"] = post.find(
            msg["date"]["tag"], attrs=msg["date"]["class"]
        ).getText()
        elem["text"] = post.find(msg["text"]["tag"], attrs=msg["text"]["class"])
        if arg.newlines:
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
            string_to_datetime(elem["date"]),
            title,
            elem["text"].getText(),
        )
        page_posts.append(chat_post)

    return page_posts


def detect_alerts(soup: BeautifulSoup, arg: argparse.Namespace) -> bool:
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
                        f"\rDEBUG: Ignoring (alert_errs) for : {item.getText()}{Fore.RESET}",
                        file=sys.stderr,
                    )
            else:
                got_alert = True
                print(
                    f"\r{Fore.RED}[!] Alert(error) : {item.getText()}{Fore.RESET}",
                    file=sys.stderr,
                )

    if alert_warns is not None:
        if "refresh the page" in alert_warns.getText():
            if arg.debug:
                print(f"\rDEBUG: (alert_warns): {alert_warns}", file=sys.stderr)
        else:
            if arg.debug:
                print(f"\rDEBUG: (alert_warns): {alert_warns}", file=sys.stderr)

    return got_alert


@Halo(text="Dumping", spinner="dots")
def dump_pages(
    url: str,
    arg: argparse.Namespace,
    conn: sqlite3.Connection | None,
    PAGE_START: int,
    PAGES_MAX: int,
) -> None:
    # Define how to detect additional pages of chat messages
    NEXT_PAGE = {"tag": "a", "class": "pager__link pager__link--next"}
    # FIXME, last page detection is broken.
    # This is the next button...can we extract the page number from it to check?
    # Because when it's at the last page, it references the current page number
    # <a href="https://www.lse.co.uk/ShareChat.html?ShareTicker=AFC&amp;share=AFC-Energy&amp;page=3" class="pager__link pager__link--next">
    LAST_PAGE = {
        "tag": "a",
        "class": "pager__link pager__link--next pager__link--disabled",
    }
    PAGE_PAUSE_MAX = 5
    posts_printed: int = 0

    for page_num in range(PAGE_START, PAGES_MAX):
        try:
            # firefox on MacOS
            # FIXME, cookies = {"chat_page_size":"50"}
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                " AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.2 Safari/605.1.15"
            }
            if arg.debug:
                print(f"[+] Getting {url}{page_num}")
            page = requests.get(url + str(page_num), headers=headers)
        except requests.exceptions.RequestException as get_error:
            print(f"{Fore.RED}[!] Error: {get_error}{Fore.RESET}", file=sys.stderr)
            sys.exit(1)

        page_soup = BeautifulSoup(page.content, "html.parser")

        # On occasion, LSE will enforce logins before chat can be viewed :<
        if page_num == 1:
            if detect_alerts(page_soup, arg):
                break

        soup_posts = get_posts_from_page(page_soup, arg)
        if len(soup_posts) == 0:
            break

        # Print the posts from the page we just retrieved
        posts_printed = print_post(arg, soup_posts, posts_printed, conn)

        if posts_printed >= arg.posts_max:
            # We don't want any more chat posts than we have now
            if arg.debug:
                print(
                    f"\rDEBUG: posts_printed is >= {arg.posts_max}, exiting",
                    file=sys.stderr,
                )
            break

        if page_soup.find(NEXT_PAGE["tag"], class_=NEXT_PAGE["class"]) is None:
            if arg.debug:
                print(
                    f"\rDEBUG: Page {page_num}, and no next page found?",
                    file=sys.stderr,
                )
            break
        if page_soup.find(LAST_PAGE["tag"], class_=LAST_PAGE["class"]) is not None:
            # This is broken now, no last page tag in the source
            if arg.debug:
                print("\rDEBUG: Last chat page parsed", file=sys.stderr)
            break

        random_pause = randrange(PAGE_PAUSE_MAX)

        if arg.debug:
            print(f"\rDEBUG: Got {posts_printed} posts,"
                  f"sleeping for {random_pause} secs...", file=sys.stderr)

        time.sleep(random_pause)

def print_post(
    arg: argparse.Namespace,
    soup_posts: list,
    posts_printed: int = 0,
    conn: None | sqlite3.Connection = None,
) -> int:
    """
    Print an entire page of soup_posts, up to the args.posts_max limit
    Optionally also saving the post to the provided SQLite DB connection
    If saving the post, dont print posts which already exist in the DB
    """

    SEEN_SOME = False
    if arg.debug:
        for chatpost in soup_posts:
            if posts_printed < arg.posts_max:
                print("\r" + repr(chatpost), end="\n\n")
                posts_printed += 1
            else:
                break

    else:
        for chatpost in soup_posts:
            if posts_printed < arg.posts_max:
                if arg.save:
                    if isinstance(conn, sqlite3.Connection):
                        # Insert a hash of the post into the database
                        if exists_in_db(conn, chatpost.hash()):
                            if not SEEN_SOME:
                                print(
                                    f"\r{Fore.LIGHTBLACK_EX}[!] Not showing some posts already saved{Fore.RESET}",
                                    file=sys.stderr,
                                )
                            posts_printed += 1
                            SEEN_SOME = True
                        else:
                            add_to_db(conn, chatpost.hash(), chatpost)
                            print("\r" + str(chatpost))
                            posts_printed += 1
                            SEEN_SOME = False
                else:
                    print("\r" + str(chatpost))
                    posts_printed += 1
            else:
                break

    # We like to keep track of how many posts we've printed so far,
    # in order we dont show more than the user supplied posts_max arg
    return posts_printed


def main() -> None:
    # Be nice to the LSE server
    PAGES_MAX: int = 4096
    PAGE_START: int = 1
    # Parse the command arguments
    arg = get_arguments()
    url: str = ""
    if arg.user:
        url = "https://www.lse.co.uk/profiles/" + arg.user + "/?page="
    if arg.ticker:
        url = "https://www.lse.co.uk/ShareChat.asp?ShareTicker=" + arg.ticker + "&page="
    if arg.page:
        PAGE_START = arg.page
    if arg.save:
        # Create and/or open the seen posts database
        conn = create_db("posts.sqlite3")
        dump_pages(url, arg, conn, PAGE_START, PAGES_MAX)
        conn.close()
    else:
        dump_pages(url, arg, None, PAGE_START, PAGES_MAX)


if __name__ == "__main__":
    main()
