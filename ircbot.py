# -*- coding: utf8 -*-
"""
ircbot derived from https://github.com/sambev/ircbot

Edit config.cfg
"""


# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.python import log

# system imports
import time
import sys
import ConfigParser
import json
import traceback
import re


MESSAGES_JSON = 'files/messages.json'
USERINFO_JSON = 'files/user_info.json'


class MessageLogger:
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """
    def __init__(self, file):
        self.file = file


    def log(self, message):
        """Write a message to the file."""
        timestamp = time.strftime("[%H:%M:%S]", time.localtime(time.time()))
        if message.strip() == '': return
        self.file.write('%s %s\n' % (timestamp, message))
        self.file.flush()


    def close(self):
        self.file.close()



class LogBot(irc.IRCClient):
    """A logging IRC bot."""
   
    # the nickname might have problems with uniquness when connecting to freenode.net 
    nickname = "AL"
    stored_messages = {}
    user_info = {}


    def __init__(self, nickname):
        self.stored_messages = self.getMessages()
        self.user_info = self.getUserInfo()
        self.nickname = nickname

    
    def getMessages(self):
        """ Get my persisted messages from the message.json file"""
        with open(MESSAGES_JSON, 'r') as f:
            try:
                messages = json.loads(f.read())
                return messages
            except:
                return {}


    def saveMessages(self):
        """ Presist my stored messages by writing to a file"""
        with open(MESSAGES_JSON, 'w') as f:
            f.write(json.dumps(self.stored_messages))


    def getUserInfo(self):
        """ Get information about my users """
        with open(USERINFO_JSON, 'r') as f:
            try:
                userinfo = json.loads(f.read())
                return userinfo
            except:
                return {}


    def logError(self, channel):
        """ Log an error to STDOUT, the logs, and chat """
        print traceback.format_exc() 
        self.logger.log("Traceback Error:\n%s" % traceback.format_exc())
        # self.msg(channel, 'There was an Error in your request, check the logs')


    def saveUserInfo(self):
        """ Save my user data """
        with open(USERINFO_JSON, 'w') as f:
            f.write(json.dumps(self.user_info))


    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" % 
                        time.asctime(time.localtime(time.time())))
        self.join(self.factory.channel)


    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" % 
                        time.asctime(time.localtime(time.time())))
        self.logger.close()

    # commands

    def remember(self, user, channel):
        try:
            if user not in self.user_info:
                self.user_info[user] = { 'points': 0 }
                self.saveUserInfo()
                self.logger.log("[Add %s to user_info]" % user)
            else:
                self.logger.log("User %s logged in.  Points = %d" %
                        (user, self.user_info[user]['points']))
        except Exception as e:
            self.logError(channel)

    def award(self, user, channel, msg):
        "Input: ipa++ 或 ipa ++ 或 ipa: ++ 或 ipa:++"
        if msg.find('++') == -1:
            return False
        aw = re.compile(r'([^ :+]+)[ :]*[+][+]')
        for awardee in aw.findall(msg):
            if awardee not in self.user_info:
                self.user_info[awardee] = { 'points': 0 }
            self.user_info[awardee]['points'] += 1
            self.saveUserInfo()
            sc = self.user_info[awardee]['points']
            self.logger.log('{0} has {1} point(s)'. format(awardee, sc))
        return True


    def nobody_tw(self, user, channel, msg):
        nb = re.compile(u'承認.+沒有人')
        if nb.search(msg):
            try:
                user = msg.split(':')[0]
            except IndexError:
                return True
        elif msg.find(u'沒有人') == -1:
            return False
        if user == self.nickname:
            self.msg(channel, '你才是沒有人!')
        else:
            self.msg(channel, '%s: 先承認你就是沒有人' % (user.encode('utf-8'),))
        return True


    def nobody_en(self, user, channel, msg):
        if msg.lower().find(u'nobody') == -1:
            return False
        self.msg(channel, '%s is nobody!' % (user,))
        return True


    def cafe(self, cmd, user, channel, msg):
        from scrapers.cafescraper import scrapeCafe
        if cmd != 'cafe':
            return False
        menu = scrapeCafe()
        # make the menu all nice for chat purposes
        for k, v in menu['stations'].items():
            if v:
                station = '{:.<{station_width}}'.format(k.encode('utf-8'), station_width=menu['station_max_width'] + 4)
                item = '{:.>{item_width}}'.format(v['item'].encode('utf-8'), item_width=menu['item_max_width'])
                self.msg(channel, '%s%s   %s' % (station, item, v['price'].encode('utf-8')))
        return True


    def hi(self, cmd, user, channel, msg):
        if cmd not in [u'hi', u'salam', u'selam', u'哈囉', u'你好', u'merhaba']:
            return False
        self.msg(channel, 'Hi! 我是 ' + self.nickname)
        return True


    def quote(self, cmd, user, channel, msg):
        "quote - 從 Reddit 隨機引用一句話"
        from apis.reddit import getQuote
        if cmd != u'quote':
            return False
        randomQuote = getQuote()
        if randomQuote is not None:
            self.msg(channel, randomQuote.encode('utf-8'))
        else:
            self.msg(channel, 'Sorry.  I failed to get a quote.')
        return True


    def weather(self, cmd, user, channel, msg):
        from apis.weatherman import currentWeather
        if cmd != u'weather':
            return False
        parts = msg.split()
        if len(parts) == 3 and  parts[2].isdigit() and len(parts[2]) == 5:
            weather = currentWeather('', '', parts[2])
        elif len(parts) >= 4:
            state = parts.pop()
            city = ' '.join(parts[2:])
            weather = currentWeather(city, state)
        else:
            weather = currentWeather()
            w_msg = 'The weather in {0} is {1}, {2} degrees, {3}% humdity.'.format(
                    weather['place'],
                    weather['status'],
                    weather['temp'],
                    weather['humidity']
                    )
            self.msg(channel, w_msg)
            self.logger.log(w_msg)
        return True


    def tell(self, cmd, user, channel, msg):
        if cmd != u'tell':
            return False
        parts = msg.split()
        target_user = parts[2]
        tell_msg = '{0}, {1} said: {2}'.format(target_user, user, ' '.join(parts[3:]))
        if target_user not in self.stored_messages:
            self.stored_messages[target_user] = []
        self.stored_messages[target_user].append(tell_msg)
        self.saveMessages()
        self.msg(channel, 'I will pass that along when {0} joins'.format(target_user))
        return True


    def movie(self, cmd, user, channel, msg):
        from apis.rottentomatoes import rottentomatoes
        if cmd != u'movie':
            return False
        key = self.factory.rottentomatoes
        if key is None:
            self.logger.log('Please set rottentomatoes key')
            return False
        movie = ' '.join(parts[2:])
        movie_response = rottentomatoes(movie, key)
        if movie_response:
            answer = 'Critics Score: {0}\nAudience Score: {1}\n{2}'.format(
                    movie_response['critics_score'],
                    movie_response['audience_score'],
                    movie_response['link'])
            self.msg(channel, answer)
        else:
            answer = 'I can\'t find that movie'
            self.msg(channel, answer)
        return True


    def reddit(self, cmd, user, channel, msg):
        "reddit <subreddit> [# of article] - 查詢 reddit"
        from apis.reddit import getSubReddit
        if cmd != u'reddit':
            return False
        parts = msg.split()
        subreddit = parts[2]
        try:
            count = int(parts[3])
        except IndexError:
            count = 1

        reddit_response = getSubReddit(subreddit, count)
        if reddit_response:
            answer = '{0}: {1} : {2}'.format(
                    count,
                    reddit_response['title'],
                    reddit_response['url'])
            self.msg(channel, answer.encode('utf-8'))
        else:
            answer = 'I can\'t find that on reddit'
            self.msg(channel, answer)
        return True


    def define(self, cmd, user, channel, msg):
        from apis.urbandic import urbanDict
        if cmd != u'define':
            return False
        question = ' '.join(parts[2:])
        urban_response = urbanDict(question)
        if urban_response:
            answer = '{0}\nFor Example: {1}\n{2}'.format(
                    urban_response['definition'], 
                    urban_response['example'], 
                    urban_response['permalink']) 
            self.msg(channel, answer)
        else:
            answer = 'I don\'t know'
            self.msg(channel, answer)
        return True


    def top10(self, cmd, user, channel, msg):
        "top10 - 按讚排行榜"
        from operator import itemgetter
        if cmd != u'top10':
            return False
        tops = sorted(self.user_info.iteritems(), key=itemgetter(1), reverse = True)
        self.msg(channel, ', '.join(['%s: %d' % (v[0], v[1]['points']) for v in tops[0:10]]).encode('utf-8'))
        return True


    def moedict(self, cmd, user, channel, msg):
        "moe <詞> - 查詢萌典"
        from apis.moedict import quote
        if cmd != u'moe':
            return False
        parts = msg.split()
        self.msg(channel, quote(parts[2]))
        return True


    def song(self, cmd, user, channel, msg):
        from apis.lastfm import getCurrentSong
        if cmd != u'song':
            return False
        parts = msg.split()
        user = parts[2]
        song = getCurrentSong(user)
        if song:
            self.msg(channel, '{0} is listening to {1}'.format(user, song.encode('utf-8')))
        return True


    def funslots(self, cmd, user, channel, msg):
        "funslots - 網友 x 的繽紛樂"
        from apis.funslots import funslots
        if cmd != u'funslots':
            return False
        fun = funslots()
        self.msg(channel, fun)
        return True


    def wolfram(self, user, channel, msg):
        from apis.wolfram import wolfram
        key = self.factory.wolfram
        if key is None:
            return False
        question = ' '.join(msg.split()[1:])
        self.logger.log('Asking wolfram for "%s"' % (question, ))
        w = wolfram(key)
        result = w.search(question)
        if result:
            answer = result.get('Value', 
                    result.get('Result',
                    result.get('Definition',
                    result.get('Statement',
                    result.get('Current result',
                    None)))))
            if answer:
                self.msg(channel, answer.encode('utf-8'))
            else:
                count = 0
                self.msg(channel, 'Not entirely sure, maybe this helps?:')
                for k, v in result.items():
                    if count < 2 and v is not None:
                        self.msg(channel, v.encode('utf-8'))
                    elif v is not None:
                        self.msg(user, v.encode('utf-8'))
                    count += 1
        else:
            self.msg(channel, 'I don\'t know')
        return True


    def unknown_command(self, cmd, user, channel, msg):
        if cmd == 'help':
            return False
        self.msg(channel, 'Affedersiniz.  "%s"\'den anlamadım.' % (cmd.encode('utf-8'),))
        # self.wolfram(user, channel, msg)
        return True


    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)


    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)


    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log("<%s> %s" % (user, msg))
        msg = msg.decode('UTF-8', 'ignore')
        parts = msg.split()
        
        # Check to see if they're sending me a private message
        if channel == self.nickname:
            parts.insert(0, self.nickname+':')
            channel = user
            msg = self.nickname+': '+msg

        #=======================================
        # MESSAGES NOT DIRECTED AT ME
        #=======================================

        indirect_functions = [
                self.award,
                self.nobody_tw,
                self.nobody_en,
                ]
        for f in indirect_functions:
            try:
                if f(user, channel, msg): return
            except Exception as e:
                self.logError(channel)


        #===================================
        # MESSAGES DIRECTED AT ME
        #===================================

        if parts[0] != self.nickname + ':':
            return
        cmd = parts[1].lower()

        direct_functions = [
                #self.cafe,
                self.hi,
                self.funslots,
                self.quote,
                #self.weather,
                #self.tell,
                #self.movie,
                self.reddit,
                self.moedict,
                #self.define,
                self.top10,
                #self.song,
                self.unknown_command,       # Keep this the last func
                ]
        for f in direct_functions:
            try:
                if f(cmd, user, channel, msg): return
            except Exception as e:
                self.logError(channel)
                return

        if cmd == 'help':
            help_msg  = '請使用以下指令:\n'
            for f in direct_functions:
                if f.__doc__ is not None:
                    help_msg += f.__doc__ + '\n'
            help_msg += '或是隨便打，我不一定會去問 Wolfram'
            self.msg(user, help_msg)




    def userJoined(self, user, channel):
        """This will get called when I see a user join a channel"""
        #check to see if I need to tell anyone anything
        self.remember(user, channel)


    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))


    # irc callbacks
    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))


    # For fun, override the method that determines how a nickname is changed on
    # collisions. The default method appends an underscore.
    def alterCollidedNick(self, nickname):
        """
        Generate an altered version of a nickname that caused a collision in an
        effort to create an unused related name for subsequent registration.
        """
        return nickname + '^'



class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, c):
        self.channel  = c.get('irc', 'channel')
        self.filename = c.get('irc', 'logfile')
        self.nickname = c.get('irc', 'nickname')
        if c.has_section('wolfram'):
            self.wolfram = c.get('wolfram', 'key')
        else:
            self.wolfram = None
        if c.has_section('rottentomatoes'):
            self.rottentomatoes = config.get('rottentomatoes', 'key')
        else:
            self.rottentomatoes = None

    def buildProtocol(self, addr):
        p = LogBot(self.nickname)
        p.factory = self
        return p


    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()


    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    # initialize logging
    log.startLogging(sys.stdout)
    config = ConfigParser.RawConfigParser()
    config.read('config.cfg')

    server = config.get('irc', 'server')
    port   = int(config.get('irc', 'port'))
    
    # create factory protocol and application
    f = LogBotFactory(config)

    # connect factory to this host and port
    reactor.connectTCP(server, port, f)

    # run bot
    reactor.run()
