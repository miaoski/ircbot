# -*- coding: utf8 -*-
import requests
import json

def quote(word):
    from random import randint
    import urllib
    if word[0] == "'":  # 台語
        r = requests.get('https://www.moedict.tw/uni/\'' + word[1:])
    else:
        r = requests.get('https://www.moedict.tw/uni/' + word)
    try:
        data = json.loads(r.text)
    except ValueError:
        return 'Cannot look up moedict.  Please try again in a few minutes.'

    quotes = []
    try:
        ds = data['heteronyms'][0]['definitions']
        for d in ds:
            if 'quote' in d:
                quotes += d['quote']
    except:
        pass

    if len(quotes) == 0:
        answer = u'查無資料,'
    else:
        answer = quotes[randint(0, len(quotes)-1)]
    answer += u' 詳見 https://www.moedict.tw/'
    answer += urllib.quote(word.encode('utf-8'))
    return answer.encode('utf-8')


if __name__ == "__main__":
    import sys
    query = sys.argv[1].decode('utf-8')
    print quote(query)
