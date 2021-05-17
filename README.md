# dumplse.py
## Dump all a users posts from LSE Share Chat forum

    $ poetry install
    $ poetry run python dumplse.py tomtastic
    tomtastic [AFC]      (23 Dec 2019 07:53)  RE: W2T
    Agreed Sharesport, we can only wait and see. I'm not invested in PHE anymore, but still watch their progress with some interest.
    
    tomtastic [AFC]      (23 Dec 2019 07:30)  RE: W2T
    I didn't realise until now that Tim Yeo joined W2T as a director in June 2019! Though offtopic for here, PHEs takeover doesn't seem to have much relevance given W2T didn't seem to actually _do_ anything.
    
    tomtastic [PHE]      (23 Dec 2019 07:24)  RE: Rns
    What did  W2T actually do, they didn't have any actual listed employees, just the White family and Tim Yeo as directors.
    
    tomtastic [BIRD]     (27 Nov 2019 13:43)  Stalled?
    Seems to have stalled around 18p, is there volume to drive this past those profit taking?

* No rate limiting is implemented, and only attempts to get 'up to' 50 pages of posts *


## Generate requirements.txt for github dependancy graphs

    $ poetry export --without-hashes > requirements.txt
