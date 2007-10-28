###
# Copyright (c) 2004, Daniel DiPaolo
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

import os
import time
import random

import supybot.dbi as dbi
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class QuoteGrabsRecord(dbi.Record):
    __fields__ = [
        'by',
        'text',
        'grabber',
        'at',
        'hostmask',
        ]

    def __str__(self):
        at = time.strftime(conf.supybot.reply.format.time(),
                           time.localtime(float(self.at)))
        grabber = plugins.getUserName(self.grabber)
        return '%s (Said by: %s; grabbed by %s at %s)' % \
                  (self.text, self.hostmask, grabber, at)

class SqliteQuoteGrabsDB(object):
    def __init__(self, filename):
        self.dbs = ircutils.IrcDict()
        self.filename = filename

    def close(self):
        for db in self.dbs.itervalues():
            db.close()

    def _getDb(self, channel):
        try:
            import sqlite
        except ImportError:
            raise callbacks.Error, 'You need to have PySQLite installed to ' \
                                   'use QuoteGrabs.  Download it at ' \
                                   '<http://pysqlite.org/>'
        filename = plugins.makeChannelFilename(self.filename, channel)
        def p(s1, s2):
            return int(ircutils.nickEqual(s1, s2))
        if filename in self.dbs:
            return self.dbs[filename]
        if os.path.exists(filename):
            self.dbs[filename] = sqlite.connect(filename,
                                                converters={'bool': bool})
            self.dbs[filename].create_function('nickeq', 2, p)
            return self.dbs[filename]
        db = sqlite.connect(filename, converters={'bool': bool})
        self.dbs[filename] = db
        self.dbs[filename].create_function('nickeq', 2, p)
        cursor = db.cursor()
        cursor.execute("""CREATE TABLE quotegrabs (
                          id INTEGER PRIMARY KEY,
                          nick TEXT,
                          hostmask TEXT,
                          added_by TEXT,
                          added_at TIMESTAMP,
                          quote TEXT
                          );""")
        db.commit()
        return db

    def get(self, channel, id):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, nick, quote, hostmask, added_at, added_by
                          FROM quotegrabs WHERE id = %s""", id)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        (id, by, quote, hostmask, at, grabber) = cursor.fetchone()
        return QuoteGrabsRecord(id, by=by, text=quote, hostmask=hostmask,
                                at=at, grabber=grabber)

    def random(self, channel, nick):
        db = self._getDb(channel)
        cursor = db.cursor()
        if nick:
            cursor.execute("""SELECT quote FROM quotegrabs
                              WHERE nickeq(nick, %s)
                              ORDER BY random() LIMIT 1""",
                              nick)
        else:
            cursor.execute("""SELECT quote FROM quotegrabs
                              ORDER BY random() LIMIT 1""")
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        return cursor.fetchone()[0]

    def list(self, channel, nick):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT id, quote FROM quotegrabs
                          WHERE nickeq(nick, %s)
                          ORDER BY id DESC""", nick)
        return [QuoteGrabsRecord(id, text=quote)
                for (id, quote) in cursor.fetchall()]

    def getQuote(self, channel, nick):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT quote FROM quotegrabs
                          WHERE nickeq(nick, %s)
                          ORDER BY id DESC LIMIT 1""", nick)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        return cursor.fetchone()[0]

    def select(self, channel, nick):
        db = self._getDb(channel)
        cursor = db.cursor()
        cursor.execute("""SELECT added_at FROM quotegrabs
                          WHERE nickeq(nick, %s)
                          ORDER BY id DESC LIMIT 1""", nick)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        return cursor.fetchone()[0]

    def add(self, msg, by):
        channel = msg.args[0]
        db = self._getDb(channel)
        cursor = db.cursor()
        text = ircmsgs.prettyPrint(msg)
        # Check to see if the latest quotegrab is identical
        cursor.execute("""SELECT quote FROM quotegrabs
                          WHERE nick=%s
                          ORDER BY id DESC LIMIT 1""", msg.nick)
        if cursor.rowcount != 0:
            if text == cursor.fetchone()[0]:
                return
        cursor.execute("""INSERT INTO quotegrabs
                          VALUES (NULL, %s, %s, %s, %s, %s)""",
                       msg.nick, msg.prefix, by, int(time.time()), text)
        db.commit()

    def search(self, channel, text):
        db = self._getDb(channel)
        cursor = db.cursor()
        text = '%' + text + '%'
        cursor.execute("""SELECT id, nick, quote FROM quotegrabs
                          WHERE quote LIKE %s
                          ORDER BY id DESC""", text)
        if cursor.rowcount == 0:
            raise dbi.NoRecordError
        return [QuoteGrabsRecord(id, text=quote, by=nick)
                for (id, nick, quote) in cursor.fetchall()]

QuoteGrabsDB = plugins.DB('QuoteGrabs', {'sqlite': SqliteQuoteGrabsDB})

class QuoteGrabs(callbacks.Plugin):
    """Add the help for "@help QuoteGrabs" here."""
    def __init__(self, irc):
        self.__parent = super(QuoteGrabs, self)
        self.__parent.__init__(irc)
        self.db = QuoteGrabsDB()

    def doPrivmsg(self, irc, msg):
        irc = callbacks.SimpleProxy(irc, msg)
        if irc.isChannel(msg.args[0]):
            (channel, payload) = msg.args
            words = self.registryValue('randomGrabber.minimumWords',
                                       channel)
            length = self.registryValue('randomGrabber.minimumCharacters',
                                        channel)
            grabTime = \
            self.registryValue('randomGrabber.averageTimeBetweenGrabs',
                               channel)
            if self.registryValue('randomGrabber', channel):
                if len(payload) > length and len(payload.split()) > words:
                    try:
                        last = int(self.db.select(channel, msg.nick))
                    except dbi.NoRecordError:
                        self._grab(irc, msg, irc.prefix)
                        self._sendGrabMsg(irc, msg)
                    else:
                        elapsed = int(time.time()) - last
                        if random.random()*elapsed > grabTime/2:
                            self._grab(irc, msg, irc.prefix)
                            self._sendGrabMsg(irc, msg)

    def _grab(self, irc, msg, addedBy):
        self.db.add(msg, addedBy)

    def _sendGrabMsg(self, irc, msg):
        s = 'jots down a new quote for %s' % msg.nick
        irc.reply(s, action=True, prefixNick=False)

    def grab(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        Grabs a quote from <channel> by <nick> for the quotegrabs table.
        <channel> is only necessary if the message isn't sent in the channel
        itself.
        """
        # chan is used to make sure we know where to grab the quote from, as
        # opposed to channel which is used to determine which db to store the
        # quote in
        chan = msg.args[0]
        if chan is None:
            raise callbacks.ArgumentError
        if ircutils.nickEqual(nick, msg.nick):
            irc.error('You can\'t quote grab yourself.', Raise=True)
        for m in reversed(irc.state.history):
            if m.command == 'PRIVMSG' and ircutils.nickEqual(m.nick, nick) \
                    and ircutils.strEqual(m.args[0], chan):
                self._grab(irc, m, msg.prefix)
                irc.replySuccess()
                return
        irc.error('I couldn\'t find a proper message to grab.')
    grab = wrap(grab, ['channeldb', 'nick'])

    def quote(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        Returns <nick>'s latest quote grab in <channel>.  <channel> is only
        necessary if the message isn't sent in the channel itself.
        """
        try:
            irc.reply(self.db.getQuote(channel, nick))
        except dbi.NoRecordError:
            irc.error('I couldn\'t find a matching quotegrab for %s.' % nick,
                      Raise=True)
    quote = wrap(quote, ['channeldb', 'nick'])

    def list(self, irc, msg, args, channel, nick):
        """[<channel>] <nick>

        Returns a list of shortened quotes that have been grabbed for <nick>
        as well as the id of each quote.  These ids can be used to get the
        full quote.  <channel> is only necessary if the message isn't sent in
        the channel itself.
        """
        try:
            records = self.db.list(channel, nick)
            L = []
            for record in records:
                # strip the nick from the quote
                quote = record.text.replace('<%s> ' % nick, '', 1)
                item = utils.str.ellipsisify('#%s: %s' % (record.id, quote),50)
                L.append(item)
            irc.reply(utils.str.commaAndify(L))
        except dbi.NoRecordError:
            irc.error('I couldn\'t find any quotegrabs for %s.' % nick,
                      Raise=True)
    list = wrap(list, ['channeldb', 'nick'])

    def random(self, irc, msg, args, channel, nick):
        """[<channel>] [<nick>]

        Returns a randomly grabbed quote, optionally choosing only from those
        quotes grabbed for <nick>.  <channel> is only necessary if the message
        isn't sent in the channel itself.
        """
        try:
            irc.reply(self.db.random(channel, nick))
        except dbi.NoRecordError:
            if nick:
                irc.error('Couldn\'t get a random quote for that nick.')
            else:
                irc.error('Couldn\'t get a random quote.  Are there any '
                          'grabbed quotes in the database?')
    random = wrap(random, ['channeldb', additional('nick')])

    def get(self, irc, msg, args, channel, id):
        """[<channel>] <id>

        Return the quotegrab with the given <id>.  <channel> is only necessary
        if the message isn't sent in the channel itself.
        """
        try:
            irc.reply(self.db.get(channel, id))
        except dbi.NoRecordError:
            irc.error('No quotegrab for id %s' % utils.str.quoted(id),
                      Raise=True)
    get = wrap(get, ['channeldb', 'id'])

    def search(self, irc, msg, args, channel, text):
        """[<channel>] <text>

        Searches for <text> in a quote.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        try:
            records = self.db.search(channel, text)
            L = []
            for record in records:
                # strip the nick from the quote
                quote = record.text.replace('<%s> ' % record.by, '', 1)
                item = utils.str.ellipsisify('#%s: %s' % (record.id, quote),50)
                L.append(item)
            irc.reply(utils.str.commaAndify(L))
        except dbi.NoRecordError:
            irc.error('No quotegrabs matching %s' % utils.str.quoted(text),
                       Raise=True)
    search = wrap(search, ['channeldb', 'text'])

Class = QuoteGrabs

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
