###
# Copyright (c) 2002-2004, Jeremiah Fincher
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import re

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.irclib as irclib
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class ChannelStat(irclib.IrcCommandDispatcher):
    def __init__(self, actions=0, chars=0, frowns=0, joins=0, kicks=0, modes=0,
                 msgs=0, parts=0, quits=0, smileys=0, topics=0, words=0):
        self.actions = actions
        self.chars = chars
        self.frowns = frowns
        self.joins = joins
        self.kicks = kicks
        self.modes = modes
        self.msgs = msgs
        self.parts = parts
        self.quits = quits
        self.smileys = smileys
        self.topics = topics
        self.words = words
        self._values = ['actions', 'chars', 'frowns', 'joins', 'kicks','modes',
                       'msgs', 'parts', 'quits', 'smileys', 'topics', 'words']
    def values(self):
        return [getattr(self, s) for s in self._values]

    def addMsg(self, msg):
        self.msgs += 1
        method = self.dispatchCommand(msg.command)
        if method is not None:
            method(msg)

    def doPayload(self, channel, payload):
        channel = plugins.getChannel(channel)
        self.chars += len(payload)
        self.words += len(payload.split())
        fRe = conf.supybot.plugins.ChannelStats.get('frowns').get(channel)()
        sRe =conf.supybot.plugins.ChannelStats.get('smileys').get(channel)()
        self.frowns += len(fRe.findall(payload))
        self.smileys += len(sRe.findall(payload))

    def doPrivmsg(self, msg):
        self.doPayload(*msg.args)
        if ircmsgs.isAction(msg):
            self.actions += 1

    def doTopic(self, msg):
        self.doPayload(*msg.args)
        self.topics += 1

    def doKick(self, msg):
        self.kicks += 1

    def doPart(self, msg):
        if len(msg.args) == 2:
            self.doPayload(*msg.args)
        self.parts += 1

    def doJoin(self, msg):
        if len(msg.args) == 2:
            self.doPayload(*msg.args)
        self.joins += 1

    def doMode(self, msg):
        self.modes += 1

    # doQuit is handled by the plugin.


class UserStat(ChannelStat):
    def __init__(self, kicked=0, *args):
        ChannelStat.__init__(self, *args)
        self.kicked = kicked
        self._values.insert(0, 'kicked')

    def doKick(self, msg):
        self.doPayload(msg.args[0], msg.args[2])
        self.kicks += 1

class StatsDB(plugins.ChannelUserDB):
    def __init__(self, *args, **kwargs):
        plugins.ChannelUserDB.__init__(self, *args, **kwargs)

    def serialize(self, v):
        return v.values()

    def deserialize(self, channel, id, L):
        L = map(int, L)
        if id == 'channelStats':
            return ChannelStat(*L)
        else:
            return UserStat(*L)

    def addMsg(self, msg, id=None):
        if ircutils.isChannel(msg.args[0]):
            channel = plugins.getChannel(msg.args[0])
            if (channel, 'channelStats') not in self:
                self[channel, 'channelStats'] = ChannelStat()
            self[channel, 'channelStats'].addMsg(msg)
            try:
                if id is None:
                    id = ircdb.users.getUserId(msg.prefix)
            except KeyError:
                return
            if (channel, id) not in self:
                self[channel, id] = UserStat()
            self[channel, id].addMsg(msg)

    def getChannelStats(self, channel):
        return self[channel, 'channelStats']

    def getUserStats(self, channel, id):
        return self[channel, id]

filename = conf.supybot.directories.data.dirize('ChannelStats.db')
class ChannelStats(callbacks.Plugin):
    noIgnore = True
    def __init__(self, irc):
        self.__parent = super(ChannelStats, self)
        self.__parent.__init__(irc)
        self.lastmsg = None
        self.laststate = None
        self.outFiltering = False
        self.db = StatsDB(filename)
        self._flush = self.db.flush
        world.flushers.append(self._flush)

    def die(self):
        world.flushers.remove(self._flush)
        self.db.close()
        self.__parent.die()

    def __call__(self, irc, msg):
        try:
            if self.lastmsg:
                self.laststate.addMsg(irc, self.lastmsg)
            else:
                self.laststate = irc.state.copy()
        finally:
            self.lastmsg = msg
        self.db.addMsg(msg)
        super(ChannelStats, self).__call__(irc, msg)

    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG':
            if ircutils.isChannel(msg.args[0]):
                if self.registryValue('selfStats', msg.args[0]):
                    try:
                        self.outFiltering = True
                        self.db.addMsg(msg, 0)
                    finally:
                        self.outFiltering = False
        return msg

    def doQuit(self, irc, msg):
        try:
            id = ircdb.users.getUserId(msg.prefix)
        except KeyError:
            id = None
        for (channel, c) in self.laststate.channels.iteritems():
            if msg.nick in c.users:
                if (channel, 'channelStats') not in self.db:
                    self.db[channel, 'channelStats'] = ChannelStat()
                self.db[channel, 'channelStats'].quits += 1
                if id is not None:
                    if (channel, id) not in self.db:
                        self.db[channel, id] = UserStat()
                    self.db[channel, id].quits += 1

    def doKick(self, irc, msg):
        (channel, nick, _) = msg.args
        hostmask = irc.state.nickToHostmask(nick)
        try:
            id = ircdb.users.getUserId(hostmask)
        except KeyError:
            return
        if channel not in self.db.channels:
            self.db.channels[channel] = {}
        if id not in self.db.channels[channel]:
            self.db.channels[channel][id] = UserStat()
        self.db.channels[channel][id].kicked += 1

    def stats(self, irc, msg, args, channel, name):
        """[<channel>] [<name>]

        Returns the statistics for <name> on <channel>.  <channel> is only
        necessary if the message isn't sent on the channel itself.  If <name>
        isn't given, it defaults to the user sending the command.
        """
        if name and ircutils.strEqual(name, irc.nick):
            id = 0
        elif not name:
            try:
                id = ircdb.users.getUserId(msg.prefix)
                name = ircdb.users.getUser(id).name
            except KeyError:
                irc.error('I couldn\'t find you in my user database.')
                return
        elif not ircdb.users.hasUser(name):
            try:
                hostmask = irc.state.nickToHostmask(name)
                id = ircdb.users.getUserId(hostmask)
            except KeyError:
                irc.errorNoUser()
                return
        else:
            id = ircdb.users.getUserId(name)
        try:
            stats = self.db.getUserStats(channel, id)
            s = format('%s has sent %n; a total of %n, %n, '
                       '%n, and %n; %s of those messages %s'
                       '%s has joined %n, parted %n, quit %n, '
                       'kicked someone %n, been kicked %n, '
                       'changed the topic %n, and changed the '
                       'mode %n.',
                       name, (stats.msgs, 'message'),
                       (stats.chars, 'character'),
                       (stats.words, 'word'),
                       (stats.smileys, 'smiley'),
                       (stats.frowns, 'frown'),
                       stats.actions,
                       stats.actions == 1 and 'was an ACTION.  '
                                           or 'were ACTIONs.  ',
                       name,
                       (stats.joins, 'time'),
                       (stats.parts, 'time'),
                       (stats.quits, 'time'),
                       (stats.kicks, 'time'),
                       (stats.kicked, 'time'),
                       (stats.topics, 'time'),
                       (stats.modes, 'time'))
            irc.reply(s)
        except KeyError:
            irc.error(format('I have no stats for that %s in %s.',
                             name, channel))
    stats = wrap(stats, ['channeldb', additional('something')])

    def channelstats(self, irc, msg, args, channel):
        """[<channel>]

        Returns the statistics for <channel>.  <channel> is only necessary if
        the message isn't sent on the channel itself.
        """
        try:
            stats = self.db.getChannelStats(channel)
            s = format('On %s there have been %i messages, containing %i '
                       'characters, %n, %n, and %n; '
                       '%i of those messages %s.  There have been '
                       '%n, %n, %n, %n, %n, and %n.',
                       channel, stats.msgs, stats.chars,
                       (stats.words, 'word'),
                       (stats.smileys, 'smiley'),
                       (stats.frowns, 'frown'),
                       stats.actions, stats.actions == 1 and 'was an ACTION'
                                                          or 'were ACTIONs',
                       (stats.joins, 'join'),
                       (stats.parts, 'part'),
                       (stats.quits, 'quit'),
                       (stats.kicks, 'kick'),
                       (stats.modes, 'mode', 'change'),
                       (stats.topics, 'topic', 'change'))
            irc.reply(s)
        except KeyError:
            irc.error(format('I\'ve never been on %s.', channel))
    channelstats = wrap(channelstats, ['channeldb'])


Class = ChannelStats

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
