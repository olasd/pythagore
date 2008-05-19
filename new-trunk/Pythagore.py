#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Pythagore.py : main IRC Bot Classes
#
# Copyright (C) 2007,2008 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
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

# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, threads
from twisted.python import log

# SQLAlchemy imports
import sqlalchemy as sa
import sqlalchemy.orm as sao

# Gettext import
import gettext
gettext.install('pythagore', './locale', unicode=True)

# yaml import
import yaml

# Mapped objects
from Mapped import Channel, Module

from Shared import *

class PythagoreBot(irc.IRCClient):
    """A Pythagore IRC bot."""
    
    def __init__(self, factory):
        # configuration, loaded at every connection
        configfile = file("Config" + os.sep + "Pythagore" + ".yml", 'r')
        self.conf = yaml.safe_load(configfile)
        configfile.close()

        self.nickname = self.conf["nick"]
        self.tables = {}

        self.factory = factory
        self.SQLInit ()

        self.modules = {}
        self.channels = dict([(channel.name,channel) for channel in self.session.query(Channel).all() if channel.enabled])
        self.moduleinstances = {}
        self.keywords = {}
        self.prefixes = {}
        self.message_rex = re.compile(r"^!(?P<command>[a-zA-Z]+)([ \t]+(?P<args>.*))?$")

    def SQLInit(self):
        """This function sets up the convenience pointers to SQL objects from the factory"""
        self.engine = self.factory.engine
        self.metadata = self.factory.metadata
        self.tables = self.factory.tables
        self.session = self.factory.session

    def connectionMade(self):
        """This function gets called whenever the bot gets connected to the network"""
        self.logger = self.registerModule("Logger") 
        irc.IRCClient.connectionMade(self)
        self.conn_t = time.time()
        self.registerModule("Admin")

    def connectionLost(self, reason):
        """This function gets called whenever the bot gets disconnected from the network"""
        irc.IRCClient.connectionLost(self, reason)
        self.logger.logall(
                _("[disconnected at %s]") %
                time.asctime(time.localtime(time.time())))
        self.logger.close()

    # This function (c) Frédéric Pauget, released under GPLv2.
    def to_encoding(self, txt, enc="ISO8859-15"):
        """Returns the text 'txt', safely encoded to the encoding 'enc', by guessing the source encoding"""
        if isinstance(txt, unicode):
            return txt.encode(enc)
        else:
            try:
                # We suppose the text is UTF-8
                return txt.decode("UTF-8").encode(enc)
            except UnicodeDecodeError:
                # else we assume (hope ?) it is ISO8859-15
                return txt.decode("ISO8859-15").encode(enc)

    def to_unicode_with_channel_enc(self, txt, channel):
        """Tries to decode the string txt into an unicode object, trying channel encoding"""
        try:
            enc = self.channels[channel].encoding
        except KeyError:
            enc = "ISO8859-15"

        return to_unicode(txt, enc)

    u_ = to_unicode_with_channel_enc

    # The following methods handle the user modes dictionnary

    def irc_RPL_NAMREPLY(self, prefix, params):
        """Handles answer to a /names query (for instance while joining a channel)"""
        
        try:
            channel = self.channels[params[2]]
        except KeyError:
            # The channel isn't in the bot's database... WTF ?
            return

        if not hasattr(channel, "usermodes"):
            channel.usermodes = {}

        users = params[3].split()
        for user in users:
            try:
                channel.usermodes[user[1:]] = self.prefixes[user[0]]
            except KeyError:
                # The prefix is unknown, so we presume the user has no special mode.
                channel.usermodes[user] = ''

    def irc_RPL_BOUNCE(self, prefix, params):
        """Handles the server capabilities message"""
        # 005 is doubly assigned.  Piece of crap dirty trash protocol.
        if params[-1].endswith("server"):
            # Server capabilities
            for param in params:
                if param.startswith("PREFIX"):
                    # User mode prefixes has format : "PREFIX=(ohv)@%+"
                    try:
                        mode_index = param.index("(")
                        pref_index = param.index(")")
                    except ValueError:
                        # Format not recognized, let's try some default values
                        if self.prefixes == {}:
                            self.prefixes = {'~': 'a', '@': 'o', '%': 'h', '+': 'v'}
                    else:
                        iter = 1
                        while iter < pref_index - mode_index:
                            self.prefixes[param[pref_index+iter]] = param[mode_index+iter]
                            iter+=1
                        break

    def userJoined(self, user, channel):
        """This gets called when a user joins a channel"""
        # The user has no mode
        self.channels[channel].usermodes[user] = ''
        self.logger.log(channel, _("-!- %(user)s has joined %(channel)s") % {'user': user, 'channel': self.u_(channel, channel)})
    
    def userLeft(self, user, channel):
        """This gets called when a user leaves a channel"""
        # The user is not in the channel anymore
        del self.channels[channel].usermodes[user]

    def userQuit(self, user, quitMessage):
        """This gets called when a user quits the network"""
        # The user is not in the channel anymore
        for channel in self.channels:
            try:
                del self.channels[channel].usermodes[user]
            except KeyError:
                # The user was not in this channel.
                pass
            else:
                self.logger.log(channel, _("-!- %(user)s has quit (%(quitMessage)s)") % {'user': user, 'quitMessage': e_(quitMessage)})

    def userRenamed(self, oldname, newname):
        """This gets called when a user changes name"""
        for channel in self.channels:
            try:
                # We get his old mode
                self.channels[channel].usermodes[newname] = self.channels[channel].usermodes[oldname]
            except KeyError:
                # The user was not there !
                pass
            else:
                # Then we delete it
                del self.channels[channel].usermodes[oldname]
    
    def modeChanged(self, user, channel, set, modes, args):
        """This gets called when a user changes a mode in a channel"""
        # The multiple mode changes is badly handled, so what we do when a mode is changed is
        # a /NAMES query when one of the changed modes is in the handled modes
        for mode in self.prefixes.values():
            if modes.find(mode) != -1:
                self.sendLine("NAMES %s" % channel)
                break

    def isOp(self, channel, user, modes='qaoh'):
        """This function returns True if 'user' has one of the 'modes' in 'channel'"""
        try:
            mode = channel.usermodes[user]
        except AttributeError:
            try:
                mode = self.channels[channel].usermodes[user]
            except IndexError:
                raise
        except:
            mode = ''

        return mode is not '' and mode in modes

    # End modes handling

    def say(self, channel, message, length = None):
        """Sends 'message' to 'channel' limiting line length to 'length'"""
        if not isinstance(message, basestring):
            message = str(message)

        message = self.to_encoding(message, enc=self.channels[channel].encoding)

        irc.IRCClient.say(self, channel, message, length)
    
    def error(self, channel, message=_('Error !')):
        """Sends 'message' to 'channel' appending the URL to the bot's documentation"""
        self.say(
            channel,
            message + _(" See \002%(url)s\002 for more information.") % {'url': 'http://aide.teepi.net/index.php/Pythagore'}
            )

    def words_callback(self, word, channel, nick, msg):
        """This function is called when a message matches the pattern given by 'say'"""
        # We refresh the channel's configuration
        self.session.refresh(self.channels[channel])
        if word in self.keywords and self.keywords[word][1] in self.channels[channel].modules:
            if msg:
                msg = self.u_(msg, channel)
            method = self.keywords[word][0]
            method(channel, nick, msg)
            return True
        return False

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        for channel in self.channels:
            print _("[%(timestamp)s] joining %(channel)s") % {'timestamp': time.time(),'channel': self.u_(channel, channel)}
            self.join(channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log(channel, _("[I have joined %(channel)s]") % {'channel': self.u_(channel, channel)})

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        # 'user' has the form 'nickname!username@host'
        user = user.split('!', 1)[0]
        str = _("(%(user)s) %(msg)s") % {'user': e_(user), 'msg': self.u_(msg, channel)}
        self.logger.log(channel, str)
        # The message may be one of the bot's commands
        if msg.startswith('!'):
            m = self.message_rex.match(msg)
            self.words_callback(m.group('command'), channel, user, m.group('args'))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log(channel, _("* %(user)s %(action)s") % {'user': user, 'action': self.u_(msg, channel)})

    def registerModule(self, modname):
        """This registers a module. When it is already loaded, the module is first unloaded
        to refresh its symbols."""
        if modname in self.modules:
            # Module already there, let's reload it and clean its symbols
            self.modules[modname] = reload(self.modules[modname])
            self.unregisterModule(modname)
        else:
            # Module not there, let's import it
            self.modules[modname] = __import__("Modules/%s" % modname)
        
        # Calls Module.Module(pythagore), to create an instance of the class
        self.moduleinstances[modname] = getattr(
            self.modules[modname],
            modname,
        )(self);
       
        try:
            # We lookup the module name in the modules table
            module = self.session.query(Module).filter(Module.name==modname).one()
        except sa.exceptions.InvalidRequestError:
            # If this exception, zero or two rows have been returned. We hope it's zero...
            module = Module(modname)
            self.session.save(module)
            self.session.commit()

        # We register all the symbols in the lookup table, which looks like :
        # {
        #   'keyword': (Module.Module.keyword_function, 'Module'),
        #   ...
        # }
        for i in self.moduleinstances[modname].exports:
            self.keywords[i] = (getattr(
                    self.moduleinstances[modname],
                    self.moduleinstances[modname].exports[i]
                    ), module)

        # We return the class instance, as a convenience for the Logger class
        return self.moduleinstances[modname]

    def unregisterModule(self, modname):
        """This unregisters a module, by removing its symbols from the lookup table, and the corresponding Class instance"""
        if modname in self.moduleinstances:
            for i in self.moduleinstances[modname].exports:
                if self.keywords[i][1] == modname:
                    del self.keywords[i]
            del self.moduleinstances[modname]

class PythagoreBotConnector(protocol.ClientFactory):
    """A connector for PythagoreBots.

    A new protocol instance will be created each time we connect to the server.
    """

    # the class of the protocol to build when new connection is made
    protocol = PythagoreBot

    def __init__(self, conf):
        self.tables = {}
        self.conf = conf
        self.SQLInit()

    def SQLInit(self):
        """This initializes the class mapping and connection to the database"""
        
        self.engine = sa.create_engine(self.conf["db_uri"], echo=False)
        self.metadata = sa.MetaData()
        self.metadata.bind = self.engine

        Session = sao.sessionmaker(bind=self.engine, autoflush=True, transactional=True)
        self.session = Session()
        self.tables["channels"] = sa.Table(self.conf["table_names"]["channels"], self.metadata, 
            sa.Column('cid', sa.Integer, primary_key=True),
            sa.Column('name', sa.String(60)),
            sa.Column('encoding', sa.String(60)),
            sa.Column('enabled', sa.Boolean),
            sa.Column('publicquotes', sa.Boolean))
        
        self.tables["modules"]  = sa.Table(self.conf["table_names"]["modules"], self.metadata,
            sa.Column('mid', sa.Integer, primary_key=True),
            sa.Column('name', sa.String(60)))

        self.tables["enabled_modules"] = sa.Table(self.conf["table_names"]["enabled_modules"], self.metadata,
            sa.Column('mid', sa.Integer, sa.ForeignKey('%s.mid' % self.conf["table_names"]["modules"])),
            sa.Column('cid', sa.Integer, sa.ForeignKey('%s.cid' % self.conf["table_names"]["channels"])))

        sao.mapper(Module, self.tables["modules"])
        sao.mapper(Channel, self.tables["channels"], properties={
            'modules': sao.relation(Module, secondary=self.tables["enabled_modules"])})
        
        self.metadata.create_all()


    def buildProtocol(self, addr):
        return PythagoreBot (self)

    def clientConnectionLost(self, connector, reason):
        """If we got disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print _("connection failed: "), reason
        connector.connect()

def main():
    # Configuration, which is loaded once here, and reloaded each time the bot connects
    configfile = file("Config" + os.sep + "Pythagore" + ".yml", 'r')
    conf = yaml.safe_load(configfile)
    configfile.close()
    

    # Connection 
    connector = PythagoreBotConnector(conf)
    reactor.connectTCP(conf["host"], conf["port"], connector)
    reactor.run()

if __name__ == "__main__":
    main()

