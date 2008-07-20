#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# RSS.py : RSS aggregator for Pythagore bot
#
# Copyright (C) 2008 Nicolas Maître <nox@teepi.net>
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

from PythagoreModule import PythagoreModule
from feedparser import parse

from Mapped import Channel, Feed

import sqlalchemy as sa
import sqlalchemy.orm as sao

from twisted.internet import reactor, protocol, defer
from twisted.web import client
import os, urllib, time


class RSS(PythagoreModule):
    def __init__(self, pythagore):
        PythagoreModule.__init__(self, pythagore)
        self.exports['addrss'] = "addRSS"
        self.exports['delrss'] = "deleteRSS"
        self.exports['enablefeed'] = "enableFeed"
        self.exports['disablefeed'] = "disableFeed"
        self.exports['listrss'] = "listFeeds"
        self.cacheFile = ""


        # SQLAlchemy : description of tables
        self.ftable = sa.Table(self.config["feeds_table"], self.bot.metadata, autoload=True)
        # FIXME : necessary to redescribe in details ?
        #    sa.Column('fid', sa.Integer, primary_key=True),
        #    sa.Column('name', sa.Unicode(60)),
        #    sa.Column('url', sa.Unicode(2000)))
        self.sel_ftable = sa.Table(self.config["selected_feeds_table"], self.bot.metadata, autoload=True)
        
        sao.mapper(Feed, self.ftable, properties={
            'channels' : sao.relation(Channel, secondary=self.sel_ftable, backref='feeds')
        })

        try: self.config['modes2Admin']
        except: self.config['modes2Admin'] = 'qao'
        try: self.cacheDir = self.config['cacheDir']
        except: self.cacheDir = self.config['cacheDir'] = '.'
        if os.path.exists(self.cacheDir) is None:
            os.mkdir(cacheDir)
        try: self.interval = self.config['time_interval']           
        except: self.interval = 10*60

        #Starts the reactor which processes feeds each self.interval seconds
        main(self.cacheDir, self.ftable, self.sel_ftable, self.bot, self.interval)  


    def addRSS(self, channel, nick, msg):
        """A bot admin adds a RSS feed to the database.
        Format : !addrss <name> <url>"""
        if nick not in self.config['admins']:
            return
        if msg is not None and len(msg) >= 2:
            args = msg.split()
            name = args[0]
            url = str("%20".join(args[1:]))
            pref, host, port, path = client._parse(url)
            if pref == "http" and host != "":
                newFeed = Feed(name, url)
                self.bot.session.save(newFeed)
                self.bot.session.commit()
                if newFeed.fid is not None:
                    self.bot.say(channel, "RSS feed number %(fid)s added !" % {'fid' : newFeed.fid})
            else:
                self.bot.error(channel, _("URL malformed."))
        else:
            self.bot.error(channel, _("Too few parameters."))

       
    def deleteRSS(self, channel, nick, msg):
        """A bot admin removes a RSS feed from the database.
        Format : !delrss <fid>"""
        if nick not in self.config['admins']:
            return
        if msg is not None:
            try:
                fid = int(msg[0])
            except ValueError:
                self.bot.error(channel, _("Argument should be a number !"))
                return
            try:
                feed = self.bot.session.query(Feed).filter(Feed.fid==fid).one()
            except sa.exceptions.InvalidRequestError:
                self.bot.say(channel, _("RSS feed number \002%(fid)s\002 doesn't exist !") % {'fid': fid})
            else:
                self.bot.session.delete(feed)
                self.bot.session.commit()
                self.bot.say(channel, _("RSS feed number \002%(fid)s\002 removed.") % {'fid':fid})
        else:
            self.bot.error(channel, _("Too few parameters."))


    def enableFeed(self, channel, nick, msg):
        """A channel operator enables the given feed on channel.
        Format : !rssenable <fid>"""
        if not self.bot.isOp(channel, nick, modes=self.config['modes2Admin']):
            self.bot.say(channel, _("You're not allowed to enable RSS feeds here."))
            return
        if msg is not None:
            try:
                fid = int(msg.split()[0])
            except ValueError:
                self.bot.error(channel, _("Argument should be a number !"))
                return
            try:
                feed = self.bot.session.query(Feed).filter(Feed.fid==fid).one()
            except sa.exceptions.InvalidRequestError:
                self.bot.say(channel, _("RSS feed number \002%(fid)s\002 doesn't exist !") % {'fid': fid})
            else:
                # we check channel is not in the channel list of the feed
                chan = self.bot.session.query(Channel).filter(Channel.name==channel).one()
                if chan.cid not in [feed.channels[i].cid for i in range(len(feed.channels))]:
                    # and we add it to the list if necessary
                    feed.channels.append(chan)
                    self.bot.session.commit()
                    self.bot.say(channel, _("Feed number \002%(fid)s\002 enabled !") % {'fid': fid})
        else:
            self.bot.error(channel, _("Too few parameters."))



    def disableFeed(self, channel, nick, msg):
        """A channel operator disables the given feed on channel.
        Format : "!rssdisable <fid>"""
        if not self.bot.isOp(channel, nick, modes=self.config['modes2Admin']):
            self.bot.say(channel, _("You're not allowed to enable RSS feeds here."))
            return
        if msg is not None:
            try:
                fid = int(msg.split()[0])
            except ValueError:
                self.bot.error(channel, _("Argument should be a number !"))
                return
            try:
                feed = self.bot.session.query(Feed).filter(Feed.fid==fid).one()
            except sa.exceptions.InvalidRequestError:
                self.bot.say(channel, _("RSS feed number \002%(fid)s\002 doesn't exist !") % {'fid': fid})
            else:
                chan = self.bot.session.query(Channel).filter(Channel.name==channel).one()
                if chan.cid in [feed.channels[i].cid for i in range(len(feed.channels))]:
                    feed.channels.remove(chan)
                    self.bot.session.commit()
                    self.bot.say(channel, _("Feed number \002%(fid)s\002 disabled !") % {'fid': fid})
        else:
            self.bot.error(channel, _("Too few parameters."))


    def listFeeds(self, channel, nick, msg):
        """Sends the list of all the available feeds to nick
        !listrss [channel]"""

        if msg is not None and self.bot.isOp(channel, nick, self.config['modes2Admin']):
            # if parameter is the current channel
            if msg.split()[0] == channel:
                chan = self.bot.session.query(Channel).filter(Channel.name==channel).one()
                count = len(chan.feeds)
                self.bot.say(channel, _("There are %(quantity)s enabled feeds on this channel for now :") % {'quantity' : count})
                for row in chan.feeds:
                    self.bot.say(channel, "\002[%s]\002 %s : %s" % (row.fid, row.name, row.url))
        else:
            count = len(self.bot.session.query(Feed).all())
            self.bot.say(channel, _("There's %(quantity)s feeds in the database for now :") % {'quantity' : count})
            s = self.bot.session.query(Feed).all()
            for row in s:
                self.bot.say(channel, _("\002[%(fid)s]\002 %(name)s : %(url)s") % {'fid': row.fid, 'name': row.name, 'url': row.url})


class RSS_HTTPConditionnalGet(client.HTTPPageGetter):
    """Protocol which provides a way to avoid parsing the same RSS files twice by not
    fetching unchanged feeds since last parsing"""
    def handleStatus_200(self):
        # Receives normal RSS file, we update the 'last-modified' entry
        if self.headers.has_key('last-modified'):
            self.factory.modified(self.headers['last-modified'])
    
    def handleStatus_304(self):
        # The feed has not been updated since last parsing, exiting connection...
        self.transport.loseConnection()
    
class RSS_HTTPConditionnalFactory(client.HTTPClientFactory):
    """Parent factory for RSS_HTTPConditionnalGet protocol"""

    protocol = RSS_HTTPConditionnalGet

    def __init__(self, cacheDir, url, ftable, sel_ftable, bot, method='GET', postdata=None, headers=None,
        agent="Twisted ConditionalPageGetter", timeout=0, cookies=None, followRedirect=1):

        # FIXME : not sure it's necessary
        self.ftable = ftable
        self.sel_ftable = sel_ftable
        self.bot = bot
        
        self.cacheFile = cacheDir+os.path.sep+self.getName(url)+".cache"

        # if cache file exists, we take the last-modified date to get the page
        # and then HTTPClientFactory makes the work for handleStatus to be called
        # in function of headers 
        if os.path.exists(self.cacheFile):
            last = open(self.cacheFile, 'r').readline().strip()
            if headers is not None:
                headers['last-modified'] = last
            else:
                headers = {'last-modified': last }

        client.HTTPClientFactory.__init__(self, url=url, method=method, postdata=postdata, headers=headers,
            agent=agent, timeout=timeout, cookies=cookies, followRedirect=followRedirect)

    def modified(self, lastmodified):
        file = open(self.cacheFile, 'w')
        file.write(lasmodified)
        file.close()
    
    def getName(self, url):
        return self.bot.session.query(Feed).filter(Feed.url==url).one().fid

def HTTPConditionnalGet(self, cacheDir, url, ftable, sel_ftable, bot, *args, **kwargs):
    #FIXME : i don't understand how to transmit informations obtained
    #by 
    scheme, host, port, path = client._parse(url)
    factory = RSS_HTTPConditionnalFactory(cacheDir, url, ftable, sel_ftable, bot, *args, **kwargs)
    reactor.connectTCP(host, port, factory)


class RSS_FeedProtocol(object):
    def __init__(self):
        self.feeds = {}
        self.bot = self.factory.bot

        self.cacheDir = self.factory.cacheDir

    def start(self, feedsToParse, deferred):
        self.feeds = feedsToParse
        d = defer.succeed(self.succeed())
        
        for feed in self.feeds.items:
            d.addCallback(self.condGet, feed[1])
            d.addErrback(self.error, _("getting page"))

            d.addCallback(self.parseFeed, feed)
            d.addErrback(self.error, _("parsing feed"))
        reactor.callLater(self.factory.interval, deferred.callback)

    def succeed(self):
        print "Starting processing RSS feeds"

    def parseFeed(self, feed):
        f = parse(feed[1])
        fid = feed[0]
        #if the page has been downloaded (in spite of RSS_HTTPConditionnalGet)
        if f is not None:
            for entry in f.entries:
                updated = int(time.mktime(entry['updated_parsed']))
                if self.factory.previous_updated[fid] >= updated:
                    print "All up-to-date in feed number %s" % (fid)
                    break
                # all should be put in a data structure of printed on concerned 
                # channels (debug purpose...)
                #curfeed = self.bot.session.query(Feed).filter(Feed.fid==fid).one():
                #for channel in curfeed.channels:
                #   self.bot.say(channel.name.encode('UTF-8'), "...")
                # FIXME : necessary to display source ?
                print "Source : %s" % ("bouh")
                print "Titre : %s" % (entry['title'])
                print "Lien : %s" % (entry['link'])
                self.factory.previous_updated[feed[0]] = int(time.time())


    def condGet(self, url):
        conditionnalGet(self, self.cacheDir, url, self.factory.ftable, self.factory.sel_ftable, self.bot)

    def error(self, traceback, args):
        print "Error while %(action)s : %(trace)s" % {'action': args, 'trace':traceback}
        print "Going on anyway..."
    

class RSS_FeedFactory(protocol.ClientFactory):
    protocol = RSS_FeedProtocol
    def __init__(self, cacheDir, ftable, sel_ftable, bot, interval):

        # FIXME: is this necessary ?
        self.ftable = ftable
        self.sel_ftable = sel_ftable
        # FIXME: another way to keep those var (instead of passing by args) ?
        self.bot = bot
        self.interval = interval
        self.cacheDir = cacheDir
        
        # FIXME : should be initialized with current time or something...
        # see parseFeed() in RSS_FeedProtocol
        self.previous_updated = {}
        self.mainloop()


    def getFeedsFromDB(self):
        """Returns a dictionnary of feeds urls to parse
        Looks like {(fid,url), (fid, url), ...}"""
        feeds = self.bot.session.query(Feed).all()
        return dict([(feed.fid,feed.url) for feed in feeds if len(feed.channels)>=1])

    def mainloop(self):
        d = defer.Deferred()
        #FIXME : exceptions.TypeError: unbound method start() must be called with RSS_FeedProtocol instance as first argument (got dict instance instead)
        # ????
        self.protocol.start(self.getFeedsFromDB(), d)
        d.addCallback(self.mainloop)

def main(cacheDir, ftable, sel_ftable, bot, interval):
    factory = RSS_FeedFactory(cacheDir, ftable, sel_ftable,  bot, interval)
    # FIXME : not sure at all it works...
    reactor.run()

