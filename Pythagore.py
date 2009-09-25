#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Pythagore ("2.0")
# A Python IRC Bot
#
# Pythagore.py : main IRC Bot Classes
#
# Copyright © 2007-2009 Nicolas Dandrimont <Nicolas.Dandrimont@crans.org>
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
import time, os
import pprint

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

from Shared import NoCaseDict, to_unicode

class IRCObserver(object):
    """
    Log observer sending traceback messages to IRC when available
    """

    def __init__(self, pythagore):
        self.bot = pythagore

        try:
            self.logchannel = self.bot.conf['debug_channel']
        except KeyError:
            self.logchannel = '#pythagore-dev'

    def _emit(self, event_dict):
        """Send the message to irc"""
        if 'failure' in event_dict:
            text = event_dict['failure'].getTraceback().splitlines()
        else:
            text = [str(m) for m in event_dict["message"]]

        for line in text:
            self.bot.msg(self.logchannel, line)

    def start(self):
        """Start the logger"""
        log.addObserver(self._emit)

    def stop(self):
        """Stop the logger"""
        log.removeObserver(self._emit)

class PythagoreModules(object):
    """Container class for Pythagore's modules"""
    def __init__(self, pythagore):
        self.pythagore = pythagore
        self.available = NoCaseDict()
        for path in os.listdir('Modules'):
            if path.lower().endswith('.py'):
                # strip ending '.py'
                path = path[:-3]
                # populate dict
                self.available[path.lower()] = path
        self.protected = NoCaseDict(admin = True, logger = True)
        self.instances = NoCaseDict()
        self.dict = NoCaseDict()
        self.keywords = NoCaseDict()

    def __contains__(self, key):
        return key in self.dict

    def __setitem__(self, key, value):
        self.dict[key] = value

    def __getitem__(self, key):
        return self.dict[key]

    def register(self, modname):
        """This registers a module. When it is already loaded, the
        module is first unloaded to refresh its symbols."""
        if modname in self:
            modpath = self.available[modname]
            # Module already there, let's reload it
            self[modname] = reload(self[modname])
            # and clean its symbols
            self.unregister(modname)
        elif modname in self.available:
            modpath = self.available[modname]
            # Module not there, let's import it
            self[modname] = __import__("Modules/%s" % modpath)
        else:
            # this module doesn't exist ...
            return

        # Calls Module.Module(pythagore), to create an instance of the class
        self.instances[modname] = getattr(
            self[modname],
            modpath,
        )(self.pythagore)

        sess = self.pythagore.sessionmaker()
        try:
            # We lookup the module name in the modules table
            module = sess.query(Module).filter(Module.name==modname).one()
        except sa.exceptions.SQLAlchemyError:
            module = Module(modname)
            sess.add(module)
            sess.commit()
        sess.close()

        # We register all the symbols in the lookup table, which looks like :
        # {
        #   'keyword': (Module.Module.keyword_function, 'Module'),
        #   ...
        # }
        for callname, function in self.instances[modname].exports.items():
            self.keywords[callname] = (getattr(
                    self.instances[modname],
                    function
                    ), module)

        # We return the class instance, as a convenience for the Logger class
        return self.instances[modname]

    def unregister(self, modname):
        """This unregisters a module, by removing its symbols from the
        lookup table, and the corresponding Class instance"""
        modname = modname.lower()
        if modname in self.instances and modname not in self.protected:
            for export in self.instances[modname].exports:
                if self.keywords[export][1] == modname:
                    del self.keywords[export]
            del self.instances[modname]
        
class PythagoreBot(irc.IRCClient):
    """A Pythagore IRC bot."""

    def __init__(self, factory):
        # configuration, loaded at every connection
        configfile = file(os.path.join("Config", "Pythagore.yml"), 'r')
        self.conf = yaml.safe_load(configfile)
        configfile.close()

        self.nickname = self.conf["nick"]
        self.tables = {}

        self.factory = factory
        self.SQLInit ()

        self.modules = PythagoreModules(self)
        self.usermodes = NoCaseDict()
        self.prefixes = {}

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

    def channels(self, channel_name = None, session = False):
        """Query the database for a channel with the given name, or
        all channels. Returns the channel(s), or a (channel(s),
        session) tuple if asked"""

        sess = self.sessionmaker()
        if channel_name is not None:
            try:
                channel = sess.query(Channel).filter(Channel.name == channel_name).one()
            except sa.exceptions.SQLAlchemyError:
                sess.rollback()
                sess.close()
                if session:
                    return None, None
                else:
                    return None
            else:
                if session:
                    return channel, sess
                else:
                    sess.close()
                    return channel
        else:
            try:
                channels = sess.query(Channel).all()
            except sa.exceptions.SQLAlchemyError:
                sess.rollback()
                sess.close()
                if session:
                    return None, None
                else:
                    return None
            else:
                if session:
                    return channels, sess
                else:
                    sess.close()
                    return channels

    def SQLInit(self):
        """This function sets up the convenience pointers to SQL objects from the factory"""
        self.engine = self.factory.engine
        self.metadata = self.factory.metadata
        self.tables = self.factory.tables
        self.sessionmaker = self.factory.sessionmaker

    def connectionMade(self):
        """This function gets called whenever the bot gets connected to the network"""
        self.logger = self.modules.register("Logger")
        irc.IRCClient.connectionMade(self)
        self.modules.register("Admin")
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

    def to_encoding(self, txt, enc="ISO8859-15"):
        """Returns the text 'txt', safely encoded to the encoding 'enc', by guessing the source encoding"""
        return to_unicode(txt).encode(enc)

    def to_unicode_with_channel_enc(self, txt, channel):
        """Tries to decode the string txt into an unicode object, trying channel encoding"""
        enc = getattr(self.channels(channel), 'encoding', 'ISO-8859-15')

        return to_unicode(txt, 'UTF-8', (enc, 'ISO-8859-15'))

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
            channelmodes = self.usermodes[params[2]]
        except KeyError:
            channelmodes = NoCaseDict()
            self.usermodes[params[2]] = channelmodes

        users = params[3].split()
        for user in users:
            try:
                channelmodes[user[1:]] = self.prefixes[user[0]]
            except KeyError:
                # The prefix is unknown, so we presume the user has no special mode.
                channelmodes[user] = ''

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
        self.usermodes[channel][user] = ''
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
        del self.usermodes[channel][user]
        self.logger.log(channel, _("-!- %(user)s has left %(channel)s (%(reason)s)") %  {'user': user, 'channel': self.u_(channel, channel), 'reason': reason})

    def userQuit(self, user, quitMessage):
        """This gets called when a user quits the network"""
        # The user is not in the channel anymore
        for channel in self.channels():
            channel = str(channel)
            try:
                del self.usermodes[channel][user]
            except KeyError:
                # The user was not in this channel.
                pass
            else:
                self.logger.log(channel, _("-!- %(user)s has quit (%(quitMessage)s)") % {'user': user, 'quitMessage': to_unicode(quitMessage)})

    def userRenamed(self, oldname, newname):
        """This gets called when a user changes name"""
        if oldname.lower() != newname.lower():
            for channel in self.channels():
                channel = str(channel)
                try:
                    # We get his old mode
                    self.usermodes[channel][newname] = self.usermodes[channel][oldname]
                except KeyError:
                    # The user was not there !
                    pass
                else:
                    # Then we delete it
                    del self.usermodes[channel][oldname]

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
            mode = self.usermodes[channel][user]
        except IndexError:
            mode = ''

        return mode is not '' and mode in modes

    # End modes handling

    def say(self, channel, message, length = None):
        """Sends 'message' to 'channel' limiting line length to 'length'"""
        if not isinstance(message, basestring):
            message = str(message)

        encoding = "ISO-8859-15"
        chobj = self.channels(channel)
        if chobj:
            encoding = chobj.encoding

        message = self.to_encoding(message, enc=encoding)

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
        chanobj, sess = self.channels(channel, True)
        if not sess:
            self.error(channel, _("Database error!"))
            return False
        word = self.strip_formatting(word)
        if word in self.modules.keywords:
            method, module = self.modules.keywords[word]
            sess.add(module)
            if module.name in self.modules.protected or module in chanobj.modules:
                if msg:
                    msg = self.u_(msg, channel)
                method(channel, nick, msg)
                sess.close()
                return True
        sess.close()
        return False

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        for channel in self.channels():
            if channel.enabled:
                print _("[%(timestamp)s] joining %(channel)s") % {'timestamp': time.time(),'channel': self.u_(channel, channel)}
                self.join(channel)

    def join(self, channel):
        """This is called when the bot wants to join a channel. It loads all required modules if applicable"""

        sess = self.sessionmaker()
        try:
            sess.add(channel)
            module_names = [module.name for module in channel.modules]
            sess.close()
        except KeyError:
            # Channel not found, we don't load any modules
            sess.close()
        else:
            for module in module_names:
                if module not in self.modules:
                    self.modules.register(module)

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
        str = _("(%(user)s) %(msg)s") % {'user': to_unicode(user), 'msg': self.u_(msg, channel)}
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

        self.sessionmaker = sao.sessionmaker(bind=self.engine)
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
        return PythagoreBot(self)

    def clientConnectionLost(self, connector, reason):
        """If we got disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print _("connection failed: "), reason
        connector.connect()

def main():
    # Configuration, which is loaded once here, and reloaded each time the bot connects
    configfile = file(os.path.join("Config", "Pythagore" + ".yml"), 'r')
    conf = yaml.safe_load(configfile)
    configfile.close()


    # Connection
    connector = PythagoreBotConnector(conf)
    reactor.connectTCP(conf["host"], conf["port"], connector)
    reactor.run()

if __name__ == "__main__":
    main()

