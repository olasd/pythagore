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
from twisted.internet import reactor, protocol
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


class IRCObserver:
    """
    Log observer sending traceback messages to IRC when available
    """

    def __init__(self, pythagore):
        self.bot = pythagore

        try:
            self.logchannel = self.bot.conf['debug_channel']
        except KeyError:
            self.logchannel = '#pythagore-dev'

    def _emit(self, eventDict):
        if 'failure' in eventDict:
            text = eventDict['failure'].getTraceback().splitlines()
        else:
            text = [str(m) for m in eventDict["message"]]

        for line in text:
            self.bot.msg(self.logchannel, line)

    def start(self):
        log.addObserver(self._emit)

    def stop(self):
        log.removeObserver(self._emit)

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
        self.channels = NoCaseDict()
        for channel in self.session.query(Channel).all():
            if channel.enabled:
                self.channels[channel.name.encode('UTF-8')] = channel
        self.moduleinstances = {}
        self.keywords = {}
        self.prefixes = {}

        self.available_modules = {}
        for path in os.listdir('Modules'):
            if path.lower().endswith('.py'):
                # strip ending '.py'
                path = path[:-3]
                # populate dict
                self.available_modules[path.lower()] = path

        self.protected_modules = ('admin', 'logger')

        self.message_rex = re.compile(r"""
                ^ # beginning of line
                ( # formatting
                    \x02                          # bold
                   |\x03[0-9]{0,2}(\,[0-9]{1,2})? # color code (can have 0 to 2 arguments)
                   |\x16                          # invert color
                   |\x1f                          # underline
                   |\x0f                          # reset formatting
                )* # or lack thereof
                !  # the magic bang
                (?P<command>\S+)    # the command can be of any non-space characters
                (\s+(?P<args>.*))?  # arguments should be separated from command with one or more space characters
                $ # end of line
                """, re.UNICODE | re.VERBOSE)

        self.formatting_rex = re.compile(r"""(
                 \x02                          # bold
                |\x03[0-9]{0,2}(\,[0-9]{1,2})? # color code (can have 0 to 2 arguments)
                |\x16                          # invert color
                |\x1f                          # underline
                |\x0f                          # reset formatting
               )""", re.UNICODE | re.VERBOSE)

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
        self.observer = IRCObserver(self)
        self.observer.start()

        if self.conf["oper_pwd"]:
            # oper up
            if "oper_nick" in self.conf:
                self.oper(self.conf["oper_pwd"], nick=self.conf["oper_nick"])
            else:
                self.oper(self.conf["oper_pwd"])

        if "nickserv_pwd" in self.conf:
            # Identify against nickserv
            self.msg('NickServ', 'IDENTIFY %(pwd)s' % {'pwd': self.conf["nickserv_pwd"]})

    def connectionLost(self, reason):
        """This function gets called whenever the bot gets disconnected from the network"""
        irc.IRCClient.connectionLost(self, reason)
        self.logger.logall(
                _("[disconnected at %s]") %
                time.asctime(time.localtime(time.time())))
        self.logger.close()
        self.observer.stop()

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

    def strip_formatting(self, msg, repl=u''):
        """Strips all formatting from message 'msg', replacing it with 'repl'.
        Formatting is defined in self.formatting_rex.
        'repl' should be whatever re.sub's second argument accepts"""
        return self.formatting_rex.sub(repl, msg)

    # The following methods handle the user modes dictionnary

    def irc_RPL_NAMREPLY(self, prefix, params):
        """Handles answer to a /names query (for instance while joining a channel)"""

        try:
            channel = self.channels[params[2]]
        except KeyError:
            # The channel isn't in the bot's database... WTF ?
            return

        if not hasattr(channel, "usermodes"):
            channel.usermodes = NoCaseDict()

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

    def irc_PART(self, prefix, params):
        nick = prefix.split('!')[0]
        channel = params[0]
        if nick == self.nickname:
            self.left(channel)
        else:
            self.myUserLeft(nick, channel, ' '.join(params[1:]))

    def myUserLeft(self, user, channel, reason):
        """This gets called when a user leaves a channel"""
        # The user is not in the channel anymore
        del self.channels[channel].usermodes[user]
        self.logger.log(channel, _("-!- %(user)s has left %(channel)s (%(reason)s)") %  {'user': user, 'channel': self.u_(channel, channel), 'reason': reason})

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
        if oldname.lower() != newname.lower():
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

        irc.IRCClient.msg(self, channel, message, length)

    def msg(self, dest, message, length = None):
        """Sends 'message' to 'dest' limiting line length to 'length'"""
        if not isinstance(message, basestring):
            message = str(message)

        message = self.to_encoding(message)

        irc.IRCClient.msg(self, dest, message, length)

    def error(self, channel, message=_('Error !')):
        """Sends 'message' to 'channel' appending the URL to the bot's documentation"""
        self.say(
            channel,
            message + _(" See \002%(url)s\002 for more information.") % {'url': self.conf["helpurl"]}
            )

    def words_callback(self, word, channel, nick, msg):
        """This function is called when a message matches the pattern given by 'say'"""
        # We refresh the channel's configuration
        self.session.refresh(self.channels[channel])
        word = self.strip_formatting(word)
        if word in self.keywords and (self.keywords[word][1] in self.protected_modules or self.keywords[word][1] in self.channels[channel].modules):
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

    def join(self, channel):
        """This is called when the bot wants to join a channel. It loads all required modules if applicable"""

        try:
            module_names = [module.name for module in self.channels[channel].modules]
        except KeyError:
            # Channel not found, we don't load any modules
            pass
        else:
            for module in module_names:
                if module.lower() not in self.modules:
                    self.registerModule(module)

        irc.IRCClient.join(self, self.to_encoding(channel, enc='UTF-8'))

    def oper(self, password, nick=None):
        """This is called for the bot to OPER up, using 'password' as password, and 'nick' as a nick if given."""
        if not nick:
            nick = self.conf["nick"]

        self.sendLine('OPER %(nick)s %(password)s' % {'nick': nick, 'password': password})
        time.sleep(2)
        self.sendLine('MODE %s +Bp' % self.conf["nick"])
        self.sendLine('MODE %s -h' % self.conf["nick"])

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log(channel, _("[I have joined %(channel)s]") % {'channel': self.u_(channel, channel)})

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        # 'user' has the form 'nickname!username@host'
        user = user.split('!', 1)[0]
        str = _("(%(user)s) %(msg)s") % {'user': e_(user), 'msg': self.u_(msg, channel)}
        self.logger.log(channel, str)
        # The message may be one of the bot's commands if it contains ! as one of its characters
        if '!' in msg:
            m = self.message_rex.match(msg)
            if m:
                self.words_callback(m.group('command'), channel, user, m.group('args'))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log(channel, _("* %(user)s %(action)s") % {'user': user, 'action': self.u_(msg, channel)})

    def kickedFrom(self, channel, kicker, message):
        """This gets called when the bot is kicked from a channel."""
        # try to rejoin channel
        self.join(channel)

    def registerModule(self, modname):
        """This registers a module. When it is already loaded, the module is first unloaded
        to refresh its symbols."""
        modname = modname.lower()
        if modname in self.modules:
            modpath = self.available_modules[modname]
            # Module already there, let's reload it
            self.modules[modname] = reload(self.modules[modname])
            # and clean its symbols
            self.unregisterModule(modname)
        elif modname in self.available_modules:
            modpath = self.available_modules[modname]
            # Module not there, let's import it
            self.modules[modname] = __import__("Modules/%s" % modpath)
        else:
            # this module doesn't exist ...
            return

        # Calls Module.Module(pythagore), to create an instance of the class
        self.moduleinstances[modname] = getattr(
            self.modules[modname],
            modpath,
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
        modname = modname.lower()
        if modname in self.moduleinstances and modname not in self.protected_modules:
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

        self.engine = sa.create_engine(self.conf["db_uri"], echo=False, connect_args = {'use_unicode': True, 'charset': "utf8"})
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

