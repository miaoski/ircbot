Forked From
===========

Forked from https://github.com/sambev/ircbot, but intended to reduce its functions.

Please use its original version if you want fancy functions.


Installation
============

1. `pip install -r requirements.txt`
2. Edit `config.cfg`
3. Touch `files/messages.json` and `files/user_info.json`
4. create a log directory for the log files

You will probably need the libxml2-dev and libxslt-dev packages (for BeautifulSoup, used for scrapers). 

`apt-get install libxml2-dev libxslt-dev`


Usage
=====

1. Better use an empty channel (e.g. #test_ircbot) to get familiar with it
2. Send `/msg AL^ help` for commands
