#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Quotes.py : Quotes module for Pythagore bot
#
# Copyright (C) 2008 Nicolas Maître <nox@teepi.net>
# Copyright (C) 2008 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
#
# This file is part of Pythagore.
#
# Pythagore is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License, version 2, as 
# published by the Free Software Foundation.
#
# Pythagore is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# of FITNESS FOR ANY PARTICULAR PURPOSE. See the GNU General Public
# License for more details.
#
# You should have received a copy of the GNU General Public License 
# along with Pythagore; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
#

from PythagoreModule import PythagoreModule
from Mapped import Quote, Channel

import random
import sqlalchemy as sa
import sqlalchemy.orm as sao
import datetime

class Quotes(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        # export commands (keywords)
        self.exports['addquote'] = "addQuote"
        self.exports['delquote'] = "removeQuote"
        self.exports['lastquote'] = "lastQuote"
        self.exports['quoteinfo'] = "quoteInfo"
        self.exports['quote'] = "getQuote"
        self.exports['randquote'] = "randomQuote"
        self.exports['findquote'] = "searchQuote"
        
        self.qtable = sa.Table(self.config["qtable"], self.bot.metadata,
            sa.Column('qid', sa.Integer, primary_key=True),
            sa.Column('content', sa.Unicode(400)),
            sa.Column('author', sa.String(60)),
            sa.Column('cid', sa.Integer, sa.ForeignKey('%s.cid' % self.bot.conf["table_names"]["channels"])),
            sa.Column('timestamp', sa.DateTime, default=datetime.datetime.now),
            sa.Column('deleted', sa.Boolean, default=False))

        sao.mapper(Quote, self.qtable)
        
        try:
            self.config['minWordsInQuotes']
        except:
            self.config['minWordsInQuotes'] = 1

    def addQuote(self, channel, nick, msg):
        """!addquote <quote>
        Adds <quote> to the database"""
        if msg:
            words=msg.split()
        else:
            self.bot.error(channel, _("Missing quote contents !"))
            return
        # s'il y a assez de mots dans la quote
        if len(words) >= int(self.config['minWordsInQuotes']):
            newquote = Quote(nick, self.bot.u_(msg, channel), self.bot.channels[channel].cid)
            self.bot.session.save(newquote)
            self.bot.session.commit()
            if newquote.qid is not None:
                self.bot.say(channel, _("Quote number \002%(qid)s\002 added !") % {'qid': newquote.qid})
        else:
            self.bot.error(channel, _("Quote too short !"))

    def removeQuote(self, channel, nick, msg):
        """!delquote <qid>
        Removes quote number <qid> from the database if the user is allowed to"""
        if msg:
            words = msg.split()
            if len(words) == 1:
                try:
                    id = int(words[0])
                except ValueError:
                    self.bot.error(channel, _("Argument should be a number !"))
                    return
                try:
                    quote = self.bot.session.query(Quote).filter(Quote.qid==id).one()
                except sa.exceptions.InvalidRequestError:
                    self.bot.say(channel, _("Quote number \002%(qid)s\002 doesn't exist !") % {'qid': id})
                else:
                    #on vérifie que nick a le droit de l'enlever
                    if nick.lower() == quote.author.lower() or nick in self.config["admins"]:
                        quote.deleted = True
                        self.bot.session.commit()
                        self.bot.say(channel, _("Quote number \002%(qid)s\002 deleted") % {'qid': quote.qid})
                    else:
                        self.bot.say(channel, _("You're not allowed to delete this quote !"))
            else:
                self.bot.error(channel, _("Too many parameters."))
        else:
            self.bot.error(channel, _("Too few parameters."))

    def getQuote(self, channel, nick, msg):
        """!quote <qid> 
        Shows quote number <qid> in the current channel, if allowed"""
        if msg:
            words = msg.split()
            if len(words) == 1:
                try:
                    qid = int(words[0])
                except ValueError:
                    self.bot.error(channel, _("Argument should be a number !"))
                    return
                try:
                    quote = self.bot.session.query(Quote).filter(Quote.deleted==False).filter(Quote.qid==qid).one()
                except sa.exceptions.InvalidRequestError:
                    self.bot.say(channel, _("Quote number \002%(qid)s\002 doesn't exist !") % {'qid': qid})
                    return

                self.printQuoteToChan(channel, quote)
            else:
                self.bot.error(channel, _("Too many parameters."))
        else:
            self.randomQuote(channel, nick, msg)

    def randomQuote(self, channel, nick, msg):
        """!randomquote [--all | --channel=#chan | -c=#chan]
        Shows a random quote from channel #chan, or from all channels, or by default from the current channel."""
      
        all = False
        chan = channel
        if msg is not None:
            words = msg.split()
            if words[0] == "--all":
                all = True
            elif words[0].startswith("-c=") or words[0].startswith("--channel="):
                chan = words[0].split("=", 1)[1]
            else:
                self.bot.error(channel, _("Incorrect parameters !"))
                return
        
        if all:
            try:
                quotes = self.bot.session.query(Quote).join(self.bot.tables["channels"]).\
                    filter(Quote.deleted == False).filter(sa.or_(self.bot.tables["channels"].c.publicquotes == True,
                                                                Quote.cid == self.bot.channels[channel].cid)).all()
            except:
                self.bot.say(channel, _("No quote found !"))
                return
        else:
            if channel != chan and not self.isPublicChannel(chan):
                self.bot.say(channel, _("No quote found !"))
                return
            quotes = self.bot.session.query(Quote).filter(Quote.deleted == False).filter(Quote.cid == self.bot.channels[channel].cid).all()
        
        if quotes:
            self.printQuoteToChan(channel, quotes[random.randint(0,len(quotes)-1)])
        else:
            self.bot.say(channel, _("No quote found !"))

    def searchQuote(self, channel, nick, msg):
        """!findquote [-all | -channel=#chan | -c=#chan] <query> 
        Searches a quote containing <query> from channel #chan, or from all channels, or from the current channel."""
        all = False
        chan = channel
        if msg is not None:
            words = msg.split()
            if words[0] == "--all":
                all = True
                del words[0]
            elif words[0].startswith("-c=") or words[0].startswith("--channel="):
                chan = words[0].split("=", 1)[1]
                del words[0]
            
            toSearch = self.bot.u_("%"+"%".join(words)+"%", channel).encode('UTF-8')

            print repr(toSearch)
        
            if all:
                try:
                    quotes = self.bot.session.query(Quote).\
                        join(self.bot.tables["channels"]).filter(Quote.deleted == False).\
                                                            filter(sa.or_(self.bot.tables["channels"].c.publicquotes == True,
                                                                         Quote.cid == self.bot.channels[channel].cid)).\
                                                            filter(Quote.content.like(toSearch)).all()
                except:
                    self.bot.say(channel, _("No quote found !"))
                    return

            else:
                if channel != chan and not self.isPublicChannel(chan):
                    self.bot.say(channel, _("No quote found !"))
                    return
                 
                try:
                    quotes = self.bot.session.query(Quote).filter(Quote.deleted == False).\
                                                            filter(Quote.cid == self.bot.channels[channel].cid).\
                                                            filter(Quote.content.like(toSearch)).all()
                except:
                    self.bot.say(channel, _("No quote found !"))
                    return
            
            if quotes:
                quotenums = [str(quote.qid) for quote in quotes]
                print ", ".join(quotenums)
                nbFound = len(quotes)
                self.bot.say(channel, nbFound > 1 and _("%(num)s quotes found:") % {'num': nbFound}
                                                  or  _("1 quote found:"))
                i = 0
                while i < 3 and i < nbFound:
                    self.printQuoteToChan(channel, quotes[i])
                    i+=1
                while i < 5 and i < nbFound:
                    self.printQuoteToNick(nick, quotes[i])
                    i+=1
                if i < nbFound:
                    self.bot.say(nick, nbFound-5 > 1 and _("%(num)s other quotes found: %(quotenums)s") % {'num': nbFound-5,
                                                                                                           'quotenums': ", ".join(quotenums[5:])}
                                                     or _("One other quote found: %(quotenum)s") % {'quotenum': quotenums[5]}) 
            else:
                self.bot.say(channel, _("No quote found !"))
        else:
            self.bot.error(channel, _("Define your query !"))

    def lastQuote(self, channel, nick, msg):
        """!lastquote [-all]
        Shows the last quote recorded in the current channel.
        If -all is added, the last quote from the network is printed out."""
        all = False
        row = ()
        if msg is not None:
            words = msg.split()
            if words[0] == "--all":
                all = True
            else:
                self.bot.error(channel, _("Incorrect parameters !"))
                return
        if all:
            try:
                quote = self.bot.session.query(Quote).\
                        join(self.bot.tables["channels"]).\
                        filter(Quote.deleted == False).\
                        filter(sa.or_(self.bot.tables["channels"].c.publicquotes == True,
                                    Quote.cid == self.bot.channels[channel].cid)).\
                        order_by(Quote.qid.desc()).first()
            except sa.exceptions.InvalidRequestError:
                self.bot.say(channel, _("No quote found !"))
                return


        else:
            try:
                quote = self.bot.session.query(Quote).\
                        filter(Quote.deleted == False).\
                        filter(Quote.cid == self.bot.channels[channel].cid).\
                        order_by(Quote.qid.desc()).first()
            except sa.exceptions.InvalidRequestError:
                self.bot.say(channel, _("No quote found !"))
                return

        if quote:
            self.printQuoteToChan(channel, quote)
        else:
            self.bot.say(channel, _("No quote found !"))

    def quoteInfo(self, channel, nick, msg):
        """!quoteinfo <qid> 
        Shows information about quote number <qid>"""
        if msg:
            try:
                id = int(msg)
            except ValueError:
                self.bot.error(channel, _("Argument should be a number !"))
                return
            try:
                quote = self.bot.session.query(Quote).filter(Quote.deleted==False).filter(Quote.qid==id).one()
            except sa.exceptions.InvalidRequestError:
                self.bot.say(channel, _("Quote number \002%(qid)s\002 doesn't exist !") % {'qid': id})
                return

            if quote:
                try:
                    quote_chan = self.bot.session.query(Channel).\
                                    filter(Channel.cid==quote.cid).\
                                    filter(sa.or_(Channel.publicquotes==True,
                                                  Channel.cid==self.bot.channels[channel].cid)).one()
                except sa.exceptions.InvalidRequestError:
                    self.bot.say(channel, _("Quote number \002%(qid)s\002 doesn't exist !") % {'qid': id})
                    return
                # strftime wants a bytesting, not an unicode object. Let's satisfy him.
                timestamp = unicode(quote.timestamp.strftime(_("the %y/%m/%d at %H:%M:%S").encode('UTF-8')), 'UTF-8')
                self.bot.say(channel, _("Quote number \002%(qid)s\002 added by %(author)s on %(date)s, on %(chan)s") %
                        {'qid': quote.qid,'author': quote.author, 'date': timestamp, 'chan': quote_chan.name})
            else:
                self.bot.say(channel, _("No quote found !"))
        else:
            self.bot.error(channel, _("Too few parameters."))

    def printQuoteToChan(self, channel, quote):
        """Shows 'quote' object in the channel, if it exists and the channel is allowed to print the quote"""
        
        if quote:
            if self.bot.channels[channel].cid == quote.cid or self.isPublicChannel(quote.cid):
                self.bot.say(
                    channel,
                    _("[\002%(qid)s\002] %(contents)s") % {'qid': quote.qid, 'contents': self.bot.u_(quote.content, channel)}
                    )
            else:
                self.bot.say(channel, _("No quote found !"))
    
    def printQuoteToNick(self, nick, quote):
        """Prints quote as a private message"""
        if row:
            self.bot.msg(
                nick,
                self.bot.to_encoding(_("[\002%(qid)s\002] %(contents)s") % {'qid': quote.qid, 'contents': quote.content})
                )

    def isPublicChannel(self, channel):
        """Checks if 'channel' is a public channel"""
        if isinstance(channel, basestring):
            try:
                chan = self.bot.channels[channel]
            except KeyError:
                return False
        else:
            try:
                chan = self.bot.session.query(Channel).filter(Channel.cid==channel).one()
            except sa.exceptions.InvalidRequestError:
                return False
        return chan.publicquotes

