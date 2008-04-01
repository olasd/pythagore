#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Pythagore.py : main IRC Bot Classes
#
# Copyright (C) 2007 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
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

# regex module import
import re

# system imports
import time, sys, os

sys.path.append('lib')

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, threads
from twisted.python import log

# yaml import
import yaml

class PythagoreBot(irc.IRCClient):
    """A Pythagore IRC bot."""
    
    nickname = "Pyth"

    def __init__(self):
        self.modules = {}
        self.moduleinstances = {}
        self.keywords = {}
        self.message_rex = re.compile(r"^!(?P<command>[a-zA-Z]+)([ \t]+(?P<args>.*))?$")

    def connectionMade(self):
        self.logger = self.registerModule("Logger") 
        irc.IRCClient.connectionMade(self)
        self.conn_t = time.time()
        self.registerModule("Admin")

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.logall(
                "[disconnected at %s]" % 
                time.asctime(time.localtime(time.time())))
        self.logger.close()

    # This function (c) Frédéric Pauget, released under GPLv2.
    def to_encoding(self, txt, enc="iso-8859-15"):
        if type(txt) == unicode:
            return txt.encode(enc)
        else:
            # On suppose d'abord que le texte est en UTF-8
            try:
                return txt.decode("UTF-8").encode(enc)
            except:
                # Sinon c'est surement de l'iso
                return txt.decode("ISO8859-15").encode(enc)

    def say(self, channel, message, length = None):
        if channel in self.factory.conf["encodings"]:
            encoding = self.factory.conf["encodings"][channel]
        else:
            encoding = "iso-8859-15"
        
        message = self.to_encoding(message, enc=encoding)

        irc.IRCClient.say(self, channel, message, length)


    # words callbacks
    def words_callback(self, word, channel, nick, msg):
        if word in self.keywords:
            if msg:
                msg = self.to_encoding(msg, enc="UTF-8")
            method = self.keywords[word]
            method(channel, nick, msg)
            return True
        return False

    # callbacks for events
    def userJoined(self, user, channel):
        reactor.callFromThread(
                self.logger.log,
                channel, 
                "-!- %s has joined %s" % (user, channel)
        )
        self.mode(channel, True, "o", None, user)
        pass

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        for channel in self.factory.conf["channels"]:
            print "[%s] joining %s" % (time.time() , channel)
            self.join(channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log(channel, "[I have joined %s]" % channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]
        self.logger.log(channel, "(%s) %s" % (user, msg))
        if msg.startswith('!'):
            m = self.message_rex.match(msg)
            self.words_callback(m.group('command'), channel, user, m.group('args'))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log(channel, "* %s %s" % (user, msg))

    def registerModule(self, modname):
        """This registers a module"""
        if modname in self.modules:
            self.modules[modname] = reload(self.modules[modname])
            self.unregisterModule(modname)
        else:
            self.modules[modname] = __import__("Modules/%s" % modname)
        
        self.moduleinstances[modname] = getattr(
            self.modules[modname],
            modname,
        )(self);
        
        for i in self.moduleinstances[modname].exports:
            self.keywords[i] = getattr(
                    self.moduleinstances[modname],
                    self.moduleinstances[modname].exports[i]
                    )
        
        return self.moduleinstances[modname]

    def unregisterModule(self, modname):
        """This unregisters a module"""
        if modname in self.moduleinstances:
            for i in self.moduleinstances[modname].exports:
                del self.keywords[i]
            del self.moduleinstances[modname]

    def error(self, channel, message='Erreur !'):
        self.say(
            channel,
            message + " Voir \002http://aide.teepi.net/index.php/Pythagore\002 pour plus d'informations."
            )

class PythagoreBotFactory(protocol.ClientFactory):
    """A factory for PythagoreBots.

    A new protocol instance will be created each time we connect to the server.
    """

    # the class of the protocol to build when new connection is made
    protocol = PythagoreBot

    def __init__(self, conf):
        self.conf = conf

    def clientConnectionLost(self, connector, reason):
        """If we got disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed: ", reason
        connector.connect()

def main():
    # configuration
    configfile = file("Config" + os.sep + "Pythagore" + ".yml", 'r')
    conf = yaml.safe_load(configfile)
    configfile.close()
    f = PythagoreBotFactory(conf)
    reactor.connectTCP(conf["host"], conf["port"], f)
    reactor.run()

if __name__ == "__main__":
    main()

