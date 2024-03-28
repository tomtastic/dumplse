# dumplse.py

## Dump chat posts from the LSE Share Chat forums

### Install dependancies

```shell
    $ poetry install
```

### View command syntax

```shell
    $ poetry run python dumplse.py -h
    usage: dumplse.py [-h] [--user USER | --ticker TICKER] [--posts_max POSTS_MAX] [--newlines] [--reverse] [--json] [--debug]

    options:
      -h, --help            show this help message and exit
      --user USER, -u USER  Dump user
      --ticker TICKER, -t TICKER
                            Dump ticker
      --posts_max POSTS_MAX, -p POSTS_MAX
                            Maximum number of posts to return
      --newlines, -n        Dont strip newlines from posts
      --reverse, -r         Reverse post order
      --json, -j            Print posts as JSON
      --debug, -d           Print posts with repr
```

### Dump latest posts for a user (limited to 1 posts)

```shell
    $ poetry run python dumplse.py -u tomtastic -p 1
    tomtastic        [AFC] @14.00 (23 Dec 2019 07:39)    RE: W2T
    Of course, for the White family and Tim Yeo, they get to exchange their presumed worthless shares in W2T for a decent chunk of PHE. Quite a nice move from their perspective, but I look forward be being told what PHE will materially gain from the arrangements.  (I simply cant take anything on AIM at face value).
```

### Dump latest posts for a user (limited to 1 post, with unstripped-newlines)

```shell
    $ poetry run python dumplse.py -u tomtastic -p 1 -n
    tomtastic        [AFC] @14.00 (23 Dec 2019 07:39)    RE: W2T
    Of course, for the White family and Tim Yeo, they get to exchange their presumed worthless shares in W2T for a decent chunk of PHE. Quite a nice move from their perspective, but I look forward be being told what PHE will materially gain from the arrangements.
```

### Dump latest posts for a user (limited to 2 posts, formatted as JSON)

```json
    $ poetry run python dumplse.py -u tomtastic -p 2 -j
    [{
        "username": "tomtastic",
        "ticker": "AFC",
        "atprice": "58.50",
        "opinion": "Strong Buy",
        "date": "26 Aug 2021 13:56",
        "title": "RE: Mace Podcast & AFC",
        "text": "Iain is listening to his twitter :)"
    },
    {
        "username": "tomtastic",
        "ticker": "AFC",
        "atprice": "14.00",
        "opinion": "No Opinion",
        "date": "23 Dec 2019 07:53",
        "title": "RE: W2T",
        "text": "Agreed Sharesport, we can only wait and see. I'm not invested in PHE anymore, but still watch their progress with some interest."
    }]
```

### Dump latest posts for a ticker symbol (limited to 2 posts, with unstripped-newlines)

```shell
    $ poetry run python dumplse.py -t RDSB -p 2 -n
    bald_eagle       [RDSB] @1,686.60 (Today 11:27)          RE: Blue hydrogen
    "When the truth comes out it will make fossil fuel extraction look green by comparison."
    =============================================================================
    Getagrip, to some extent you have a point. Not enough research has gone into the environmental impact of 'going green'. The same could 'probably' be said about nuclear, it isn't a perfect solution but it will 'probably' be needed for energy security...i.e. when the sun don't shine & the wind don't blow.

    getafgrip        [RDSB] @1,692.40 (Today 10:36)          RE: Blue hydrogen
    It was an interesting take on the direction Japan is taking, also showing environmentalists concerned at Japan building its latest coal-fired power station & stating that the Japanese are importing 200 million tons of coal each year, largely from Australia. Then as BE says
```
