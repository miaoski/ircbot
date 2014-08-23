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
#from scrapers.cafescraper import scrapeCafe
from apis.weatherman import currentWeather
from apis.wolfram import wolfram
#from apis.urbandic import urbanDict
#from apis.lastfm import getCurrentSong
#from apis.rottentomatoes import rottentomatoes
from apis.reddit import getSubReddit, getQuote
#from random import randint
import ConfigParser
import json
import traceback


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
                messages = json.loads(f.read())
                return messages
            except:
                return {}


    def logError(self, channel):
        """ Log an error to STDOUT, the logs, and chat """
        print traceback.format_exc() 
        self.logger.log("Traceback Error:\n%s" % traceback.format_exc())
        self.msg(channel, 'There was an Error in your request, check the logs')


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
        parts = msg.split()
        
        # Check to see if they're sending me a private message
        if channel == self.nickname:
            parts.insert(0, self.nickname+':')
            channel = user

        # if someone is trying to give points
        if parts[0][-2:] == '++':
            awardee = parts[0][:-2]

            # create a new user if AL doesn't know who they are
            if awardee not in self.user_info:
                self.user_info[awardee] = {
                    'points': 0
                }

            self.user_info[awardee]['points'] += 1
            total_points = self.user_info[awardee]['points']
            self.saveUserInfo()
            if total_points == 1:
                self.msg(channel, '{0} has {1} point'. format(awardee, total_points))
            else:
                self.msg(channel, '{0} has {1} points'. format(awardee, total_points))


        #==========================================================================================
        # ---------- MESSAGES DIRECTED AT ME
        #==========================================================================================
        if parts[0] == self.nickname + ':':

            if parts[1] == 'help':
                """Tell them the commands I have available"""
                try:
                    help_msg = 'I currently support the following commands:\
                    \nquote\
                    \nweather [<city> <state> | <zip>]\
                    \ndefine <something>\
                    \nshow users\
                    \nremember <name>\
                    \nreddit <subreddit> <# of article optional>\
                    \nor just ask me a question, I will ask Wolfram'
                    self.msg(user, help_msg)
                except Exception as e:
                    self.logError(channel)


#            elif parts[1] == 'cafe':
#                try:
#                    menu = scrapeCafe()
#                    # make the menu all nice for chat purposes
#                    for k, v in menu['stations'].items():
#                        if v:
#                            station = '{:.<{station_width}}'.format(k.encode('utf-8'), station_width=menu['station_max_width'] + 4)
#                            item = '{:.>{item_width}}'.format(v['item'].encode('utf-8'), item_width=menu['item_max_width'])
#                            self.msg(channel, '%s%s   %s' % (station, item, v['price'].encode('utf-8')))
#                except Exception as e:
#                    self.logError(channel)


            elif parts[1] == 'hi':
                    self.msg(channel, 'Hello, I am ' + self.nickname)

            elif parts[1] == 'quote':
                try:
                    randomQuote = getQuote()
                    self.msg(channel, randomQuote.encode('utf-8'))
                except Exception, e:
                    self.logError(channel)
                    

            elif parts[1] == 'weather':
                try:
                    # get the weather and tell the channel
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
                except Exception as e:
                    self.logError(channel)


            elif parts[1] == 'tell':
                """Tell a user a given message when they join"""
                try:
                    # form the message
                    target_user = parts[2]
                    tell_msg = '{0}, {1} said: {2}'.format(target_user, user, ' '.join(parts[3:]))
                    if target_user not in self.stored_messages:
                        self.stored_messages[target_user] = []
                    self.stored_messages[target_user].append(tell_msg)
                    self.saveMessages()
                    self.msg(channel, 'I will pass that along when {0} joins'.format(target_user))
                except Exception as e:
                    self.logError(channel)


#            elif parts[1] == 'movie':
#                try:
#                    config = ConfigParser.RawConfigParser()
#                    config.read('config.cfg')
#                    key = config.get('rottentomatoes', 'key')
#                    movie = ' '.join(parts[2:])
#                    movie_response = rottentomatoes(movie, key)
#                    if movie_response:
#                        answer = 'Critics Score: {0}\nAudience Score: {1}\n{2}'.format(
#                            movie_response['critics_score'],
#                            movie_response['audience_score'],
#                            movie_response['link'])
#                        self.msg(channel, answer)
#                    else:
#                        answer = 'I can\'t find that movie'
#                        self.msg(channel, answer)
#                except Exception, e:
#                    self.logError(channel)

            elif parts[1] == 'reddit':
                try:
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
                except Exception, e:
                    self.logError(channel)        


            elif parts[1] == 'define':
                try:
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
                except Exception as e:
                    self.logError(channel)

            elif ' '.join(parts[1:3]) == 'show users':
                try:
                    self.msg(channel, ', '.join([user for user in self.user_info]).encode('utf-8'))
                except Exception as e:
                    self.logError(channel)


            elif parts[1] == 'remember':
                try:
                    user = parts[2]
                    if user not in self.user_info:
                        self.user_info[user] = {
                            'points': 0
                        }
                        self.saveUserInfo()
                        self.msg(channel, "I'll remember that info")
                    else:
                        self.msg(channel, 'I already know that user')
                except Exception as e:
                    self.logError(channel)


#            elif ' '.join(parts[1:3]) == 'update email':
#                try:
#                    user = parts[3]
#                    if user in self.user_info:
#                        try:
#                            self.user_info[user]['email'] = parts[4]
#                            self.saveUserInfo()
#                            self.msg(channel, 'Updated email for %s' % user)
#                        except IndexError:
#                            self.msg(channel, 'Please supply an email')
#                    else:
#                        self.msg(channel, "I don't know that user")
#                except Exception as e:
#                    self.logError(channel)


#            elif parts[1] == 'song':
#                try:
#                    user = parts[2]
#                    song = getCurrentSong(user)
#                    if song:
#                        self.msg(channel, '{0} is listening to {1}'.format(user, song.encode('utf-8')))
#                except Exception as e:
#                    self.logError(channel)

#            elif parts[1] in ['Will', 'will']:
#                try:
#                    possible_ansers = [
#                        'Yes.',
#                        'No.',
#                        'Probably.',
#                        'There is a 50/50 chance.',
#                        'Maybe. Impossible to know for sure',
#                        'Probably not.'
#                    ]
#                    self.msg(channel, possible_ansers[randint(0, 5)].encode('utf-8'))
#                except:
#                    self.logError(channel)


        #==========================================================================================
        # ---------- IF NOT ONE OF THE SPECIAL COMMANDS ABOVE ASK WOLFRAM
        #==========================================================================================
            else:
                try:
                    config = ConfigParser.RawConfigParser()
                    config.read('config.cfg')
                    key = config.get('wolfram', 'key')
                    question = ' '.join(parts[1:])
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

                except Exception as e:
                    self.logError(channel)


    def userJoined(self, user, channel):
        """This will get called when I see a user join a channel"""
        #check to see if I need to tell anyone anything
        try:
            if user in self.stored_messages:
                for message in self.stored_messages[user]:
                    self.msg(channel, str(message))
                #remove the messages
                del self.stored_messages[user]
                self.saveMessages()
        except Exception as e:
            self.logError(channel)


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

    def __init__(self, conf):
        self.channel = conf['channel']
        self.filename = conf['logfile']
        self.nickname = conf['nickname']

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
    c = {'server': '', 'port': 0, 'channel': '', 'logfile': '', 'nickname': ''}
    for k,v in c.items():
        c[k] = config.get('irc', k)
        if type(v) == type(0):
            c[k] = int(c[k])
    
    # create factory protocol and application
    f = LogBotFactory(c)

    # connect factory to this host and port
    reactor.connectTCP(c['server'], c['port'], f)

    # run bot
    reactor.run()
